"""
Тесты валидаторов и схем.
Запуск:  pytest -q
"""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.validators import validate_iin, validate_phone, validate_future_datetime
from app.schemas import PatientCreate, AppointmentCreate


# ---- ИИН ----
def test_iin_valid():
    assert validate_iin("123456789012") == "123456789012"


@pytest.mark.parametrize("bad", ["12345", "1234567890123", "12345678901a", ""])
def test_iin_invalid(bad):
    with pytest.raises(ValueError):
        validate_iin(bad)


# ---- Телефон ----
def test_phone_normalization():
    assert validate_phone("+7 (701) 123-45-67") == "+77011234567"


def test_phone_invalid():
    with pytest.raises(ValueError):
        validate_phone("12345")


# ---- Дата приёма ----
def test_future_datetime_ok():
    future = datetime.now(timezone.utc) + timedelta(days=1)
    assert validate_future_datetime(future) == future


def test_past_datetime_rejected():
    past = datetime.now(timezone.utc) - timedelta(days=1)
    with pytest.raises(ValueError):
        validate_future_datetime(past)


# ---- Интеграция со схемами ----
def test_patient_schema_bad_iin():
    with pytest.raises(ValidationError):
        PatientCreate(full_name="Тест Тестов", iin="123", phone="+77011234567")


def test_appointment_schema_past_date():
    past = datetime.now(timezone.utc) - timedelta(days=1)
    with pytest.raises(ValidationError):
        AppointmentCreate(doctor_id=1, patient_id=1, scheduled_at=past)
