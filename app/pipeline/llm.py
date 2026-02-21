import os, json, requests

OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434/api/generate')
MODEL = 'llama3.2'

VALID_TYPES = {
    'Жалоба', 'Смена данных', 'Консультация', 'Претензия',
    'Неработоспособность приложения', 'Мошеннические действия', 'Спам'
}
VALID_TONES = {'Позитивный', 'Нейтральный', 'Негативный'}
VALID_LANGS = {'RU', 'KZ', 'ENG'}


def analyze_ticket(desc: str, segment: str, country: str, region: str) -> dict:
    """Анализирует тикет через LLM. Возвращает dict с полями анализа."""

    prompt = (
        'Ты ассистент службы поддержки Freedom Broker.\n'
        'Проанализируй обращение клиента и верни ТОЛЬКО JSON без пояснений.\n\n'
        f'Сегмент: {segment}\n'
        f'Страна/Регион: {country}, {region}\n'
        f'Обращение: {desc}\n\n'
        'Допустимые значения:\n'
        '  тип: "Жалоба"|"Смена данных"|"Консультация"|"Претензия"|'
        '"Неработоспособность приложения"|"Мошеннические действия"|"Спам"\n'
        '  тональность: "Позитивный"|"Нейтральный"|"Негативный"\n'
        '  приоритет: целое число от 1 до 10\n'
        '  язык: "RU"|"KZ"|"ENG" — язык текста обращения\n\n'
        'Верни JSON:\n'
        '{\n'
        '  "тип": "...",\n'
        '  "тональность": "...",\n'
        '  "приоритет": 5,\n'
        '  "язык": "...",\n'
        '  "резюме": "1-2 предложения о сути проблемы",\n'
        '  "рекомендация": "что конкретно должен сделать менеджер"\n'
        '}'
    )

    try:
        resp = requests.post(OLLAMA_URL, json={
            'model': MODEL,
            'prompt': prompt,
            'stream': False,
            'format': 'json',
        }, timeout=30)
        resp.raise_for_status()
        data = json.loads(resp.json()['response'].strip())
    except Exception:
        return _fallback(desc)

    # Валидация и нормализация полей
    ticket_type = data.get('тип', '')
    if ticket_type not in VALID_TYPES:
        ticket_type = 'Консультация'

    tone = data.get('тональность', '')
    if tone not in VALID_TONES:
        tone = 'Нейтральный'

    try:
        priority = int(data.get('приоритет', 5))
        priority = max(1, min(10, priority))
    except (TypeError, ValueError):
        priority = 5

    language = str(data.get('язык', 'RU')).upper().strip()
    if language not in VALID_LANGS:
        language = 'RU'

    return {
        'ticket_type':    ticket_type,
        'tone':           tone,
        'priority':       priority,
        'language':       language,
        'summary':        str(data.get('резюме', '')),
        'recommendation': str(data.get('рекомендация', '')),
    }


def _fallback(desc: str) -> dict:
    return {
        'ticket_type':    'Консультация',
        'tone':           'Нейтральный',
        'priority':       5,
        'language':       'RU',
        'summary':        desc[:150] if desc else '',
        'recommendation': 'Связаться с клиентом для уточнения деталей',
    }