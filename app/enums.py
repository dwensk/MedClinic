"""
Общие перечисления (enums).

Вынесены в отдельный модуль, чтобы их могли использовать
и ORM-модели (models.py), и Pydantic-схемы (schemas.py)
без циклических импортов.
"""

import enum


class UserRole(str, enum.Enum):
    """Роль пользователя системы."""
    admin = "admin"     # Администратор: управляет расписанием, врачами, пациентами
    doctor = "doctor"   # Врач: просматривает записи, ведёт приёмы


class AppointmentStatus(str, enum.Enum):
    """Статус записи на приём."""
    scheduled = "scheduled"     # Запланирована
    completed = "completed"     # Приём состоялся
    cancelled = "cancelled"     # Отменена
    no_show = "no_show"         # Пациент не пришёл
