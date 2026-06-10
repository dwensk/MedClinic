"""
Кастомные серверные валидаторы.

Используются Pydantic-схемами (schemas.py) через @field_validator.
Каждая функция либо возвращает очищенное значение, либо бросает ValueError
с понятным сообщением (FastAPI превратит его в ответ 422).
"""

import re
from datetime import datetime, timezone

# ИИН — ровно 12 цифр.
_IIN_PATTERN = re.compile(r"^\d{12}$")

# Телефон РК: +7XXXXXXXXXX или 8XXXXXXXXXX (10 цифр после кода).
_PHONE_PATTERN = re.compile(r"^(\+7|8)\d{10}$")


def validate_iin(value: str) -> str:
    """
    Проверка ИИН: должен состоять РОВНО из 12 числовых символов.

    >>> validate_iin("123456789012")
    '123456789012'
    """
    value = value.strip()
    if not _IIN_PATTERN.match(value):
        raise ValueError("ИИН должен содержать ровно 12 цифр")
    return value


def validate_phone(value: str) -> str:
    """
    Проверка и нормализация номера телефона.
    Убирает пробелы, скобки и дефисы, затем проверяет формат РК.
    Возвращает номер в чистом виде, напр. '+77011234567'.
    """
    cleaned = re.sub(r"[\s\-()]", "", value)
    if not _PHONE_PATTERN.match(cleaned):
        raise ValueError("Неверный формат телефона. Пример: +77011234567 или 87011234567")
    return cleaned


def validate_future_datetime(value: datetime) -> datetime:
    """
    Проверка даты/времени приёма: НЕЛЬЗЯ записаться на прошедшее время.

    Сравнение делается в UTC. Если на вход пришла «наивная» дата (без таймзоны),
    считаем её UTC.
    """
    now = datetime.now(timezone.utc)
    compare = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if compare < now:
        raise ValueError("Нельзя записаться на прошедшую дату/время")
    return value


def validate_iin_checksum(value: str) -> str:
    """
    (Опционально, для продвинутой проверки.)

    Полная проверка контрольного разряда ИИН РК по официальному алгоритму.
    По умолчанию НЕ используется в схемах (силлабус требует только 12 цифр),
    но вы можете подключить её, заменив validate_iin на эту функцию.
    """
    value = validate_iin(value)  # сперва базовая проверка «12 цифр»
    weights_1 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    weights_2 = [3, 4, 5, 6, 7, 8, 9, 10, 11, 1, 2]
    digits = [int(d) for d in value]

    checksum = sum(d * w for d, w in zip(digits, weights_1)) % 11
    if checksum == 10:
        checksum = sum(d * w for d, w in zip(digits, weights_2)) % 11
    if checksum == 10 or checksum != digits[11]:
        raise ValueError("Неверный контрольный разряд ИИН")
    return value
