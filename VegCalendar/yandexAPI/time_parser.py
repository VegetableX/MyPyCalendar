import re
from config import WORK_DAY_MINUTES

# Нормализация времени для преобразования недель дней часов в минуты
def iso_duration_to_minutes(duration_str):
    """
    Принимает строку типа 'P1DT1H' или 'PT90M'
    Возвращает общее количество минут (int)
    """
    if not duration_str:
        return 0
    
    # Ищем числа перед D (дни), H (часы) и M (минуты)
    days = re.search(r'(\d+)D', duration_str)
    hours = re.search(r'(\d+)H', duration_str)
    minutes = re.search(r'(\d+)M', duration_str)
    
    total = 0
    if days:
        total += int(days.group(1)) * WORK_DAY_MINUTES
    if hours:
        total += int(hours.group(1)) * 60
    if minutes:
        total += int(minutes.group(1))
        
    return total

# Нормализация даты
from datetime import datetime, timezone, timedelta

def normalize_to_date_str(iso_date_str):
    """
    Принимает '2026-04-30T21:25:49.432+0000'
    Возвращает строку '2026-04-30' в UTC
    """
    # Убираем лишние знаки в конце для парсинга, если они есть
    clean_str = iso_date_str.replace("+0000", "+00:00").replace("+0300", "+03:00")
    
    # Превращаем в объект datetime
    dt = datetime.fromisoformat(clean_str)
    
    # Переводим в UTC и забираем только дату
    return dt.astimezone(timezone.utc).strftime('%Y-%m-%d')