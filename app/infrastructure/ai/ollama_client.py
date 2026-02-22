import os
import json
import openai

# Убедись, что OPENAI_API_KEY задан в окружении
openai.api_key = os.getenv("OPENAI_API_KEY")

client = openai.OpenAI()

MODEL = "gpt-4"  # или gpt-3.5-turbo

VALID_TYPES = {
    'Жалоба', 'Смена данных', 'Консультация', 'Претензия',
    'Неработоспособность приложения', 'Мошеннические действия', 'Спам'
}
VALID_TONES = {'Позитивный', 'Нейтральный', 'Негативный'}
VALID_LANGS = {'RU', 'KZ', 'ENG'}


def analyze_ticket(desc: str, segment: str, country: str, region: str) -> dict:
    """Анализирует тикет через OpenAI GPT API и возвращает словарь с полями анализа."""

    prompt = (
        "Ты классификатор обращений службы поддержки Freedom Broker.\n"
        "Верни ТОЛЬКО JSON, без пояснений.\n\n"

        f"Сегмент: {segment}\n"
        f"Страна/Регион: {country}, {region}\n"
        f"Обращение: {desc}\n\n"

        "Типы (выбери один):\n"
        "- Жалоба: недовольство сервисом или сотрудником\n"
        "- Претензия: потеря денег, неверное списание\n"
        "- Смена данных: изменить телефон, email, адрес\n"
        "- Консультация: вопрос как что-то сделать\n"
        "- Неработоспособность приложения: баг, ошибка, не грузится\n"
        "- Мошеннические действия: взлом, чужой вход, подозрительная операция\n"
        "- Спам: реклама, не связана с Freedom Broker\n\n"

        "Тональность: Позитивный / Нейтральный / Негативный\n\n"

        "Приоритет 1-10:\n"
        "9-10: мошенничество, пропажа денег, взлом\n"
        "7-8: не работает приложение, нельзя провести операцию\n"
        "5-6: жалоба без потерь\n"
        "3-4: консультация, смена данных\n"
        "1-2: спам\n\n"

        "Язык — определяй ТОЛЬКО по тексту обращения, не по стране:\n"
        "RU — если текст на русском\n"
        "KZ — если текст на казахском\n"
        "ENG — если текст на английском\n\n"

        "Примеры:\n"
        'Обращение: "Купить акции Apple со скидкой!" -> тип: Спам, язык: RU\n'
        'Обращение: "Кто-то зашёл в мой аккаунт и вывел деньги" -> тип: Мошеннические действия, язык: RU\n'
        'Обращение: "Менің телефон нөмірімді өзгерту керек" -> тип: Смена данных, язык: KZ\n'
        'Обращение: "How do I buy ETF?" -> тип: Консультация, язык: ENG\n\n'

        "Верни JSON:\n"
        "{\n"
        '  "тип": "...",\n'
        '  "тональность": "...",\n'
        '  "приоритет": 5,\n'
        '  "язык": "RU",\n'
        '  "резюме": "1-2 предложения",\n'
        '  "рекомендация": "действие менеджера"\n'
        "}"
    )

    try:
        response = client.responses.create(
            model=MODEL,
            input=[{"role": "user", "content": prompt}],
            temperature=0
        )
        raw_text = response.output_text.strip()
        data = json.loads(raw_text)
    except Exception as e:
        print(f"Error processing LLM response: {e}")
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