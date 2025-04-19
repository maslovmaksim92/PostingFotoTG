from datetime import date
from babel.dates import format_date

def format_russian_date(date_obj: date) -> str:
    """
    Преобразует дату в формат "19 апреля 2025" на русском языке.
    """
    try:
        return format_date(date_obj, format='d MMMM y', locale='ru')
    except Exception:
        return date_obj.strftime("%Y-%m-%d")