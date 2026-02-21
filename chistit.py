import pandas as pd
import os
import re

def universal_data_cleaner(file_path, output_format='xlsx'):
    """
    Универсальная функция для очистки тикетов. 
    Поддерживает CSV и XLSX.
    """
    print(f"--- Начинаю обработку файла: {file_path} ---")
    
    # 1. Загрузка данных
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == '.csv':
        # Читаем с запасом, так как битые кавычки могут мешать
        df = pd.read_csv(file_path, on_bad_lines='warn', encoding='utf-8')
    elif ext == '.xlsx':
        df = pd.read_excel(file_path)
    else:
        return "Неподдерживаемый формат"

    # 2. Функция "умной" очистки текста (LLM-подход)
    def clean_text_logic(text):
        if pd.isna(text):
            return ""
        
        # Убираем лишние кавычки в начале и конце, которые дублируются
        text = str(text).strip()
        text = re.sub(r'^"+|"+$', '"', text) # Оставляем по одной кавычке если нужно, или убираем вовсе
        
        # Убираем внутренние переносы строк, которые ломают CSV
        text = text.replace('\n', ' ').replace('\r', ' ')
        
        # Убираем двойные пробелы
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip('"') # Финальный стрип

    # 3. Применяем очистку ко всем текстовым колонкам
    # Особенно к колонке 'Описание ', где больше всего мусора
    text_columns = df.select_dtypes(include=['object']).columns
    for col in text_columns:
        df[col] = df[col].apply(clean_text_logic)

    # 4. Исправление дат (убираем 0:00:00)
    if 'Дата рождения' in df.columns:
        df['Дата рождения'] = pd.to_datetime(df['Дата рождения'], errors='coerce').dt.date

    # 5. Сохранение
    output_file = f"final_version.{output_format}"
    if output_format == 'xlsx':
        df.to_excel(output_file, index=False)
    else:
        df.to_csv(output_file, index=False, quoting=1) # quoting=1 добавляет кавычки правильно
    
    print(f"--- Готово! Файл сохранен как: {output_file} ---")
    return df

# ПРИМЕР ЗАПУСКА:
# universal_data_cleaner('tickets.csv', output_format='xlsx')

universal_data_cleaner('tickets.csv', output_format='csv')