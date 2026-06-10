"""
Pydantic-схемы (валидация входящих/исходящих данных).

Для каждой сущности — три типа схем:
- *Create  — данные на вход при создании (POST);
- *Update  — частичное обновление (PATCH), все поля опциональны;
- *Read    — данные на выход (GET), читаются прямо из ORM-объектов
             (model_config = from_attributes=True).
"""

from datetime import datetime, date, time

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

from app.enums import UserRole, AppointmentStatus
from app.validators import validate_iin, validate_phone, validate_future_datetime


# --------------------------------------------------------------------------- #
#  Department (Отделение)
# --------------------------------------------------------------------------- #
class DepartmentBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentRead(DepartmentBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None


# --------------------------------------------------------------------------- #
#  Patient (Пациент)
# --------------------------------------------------------------------------- #
class PatientBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    iin: str = Field(description="ИИН — ровно 12 цифр")
    phone: str
    birth_date: date | None = None
    gender: str | None = Field(default=None, max_length=10)

    # Кастомная валидация бизнес-полей.
    @field_validator("iin")
    @classmethod
    def _check_iin(cls, v: str) -> str:
        return validate_iin(v)

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, v: str) -> str:
        return validate_phone(v)


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = None
    birth_date: date | None = None
    gender: str | None = None

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, v):
        return validate_phone(v) if v is not None else v


class PatientRead(PatientBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


# --------------------------------------------------------------------------- #
#  Doctor (Врач) + связанная учётная запись User
# --------------------------------------------------------------------------- #
class DoctorCreate(BaseModel):
    # Поля учётной записи
    email: EmailStr
    password: str = Field(min_length=6, description="Пароль (будет захэширован)")
    full_name: str = Field(min_length=2, max_length=150)
    # Поля профиля врача
    department_id: int
    iin: str
    phone: str
    specialization: str = Field(min_length=2, max_length=120)
    cabinet: str | None = None

    @field_validator("iin")
    @classmethod
    def _check_iin(cls, v):
        return validate_iin(v)

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, v):
        return validate_phone(v)


class DoctorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    department_id: int
    iin: str
    phone: str
    specialization: str
    cabinet: str | None


class DoctorUpdate(BaseModel):
    department_id: int | None = None
    phone: str | None = None
    specialization: str | None = Field(default=None, min_length=2, max_length=120)
    cabinet: str | None = None

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, v):
        return validate_phone(v) if v is not None else v


# --------------------------------------------------------------------------- #
#  Schedule (График работы)
# --------------------------------------------------------------------------- #
class ScheduleCreate(BaseModel):
    doctor_id: int
    weekday: int = Field(ge=0, le=6, description="0 = Понедельник ... 6 = Воскресенье")
    start_time: time
    end_time: time

    @field_validator("end_time")
    @classmethod
    def _check_times(cls, end, info):
        start = info.data.get("start_time")
        if start and end <= start:
            raise ValueError("Время окончания должно быть позже времени начала")
        return end


class ScheduleRead(ScheduleCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


# --------------------------------------------------------------------------- #
#  Appointment (Запись на приём)
# --------------------------------------------------------------------------- #
class AppointmentBase(BaseModel):
    doctor_id: int
    patient_id: int
    scheduled_at: datetime
    reason: str | None = Field(default=None, max_length=255)

    # Ключевая бизнес-логика: дата приёма не должна быть в прошлом.
    @field_validator("scheduled_at")
    @classmethod
    def _check_future(cls, v: datetime) -> datetime:
        return validate_future_datetime(v)


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    scheduled_at: datetime | None = None
    status: AppointmentStatus | None = None
    reason: str | None = None

    @field_validator("scheduled_at")
    @classmethod
    def _check_future(cls, v):
        return validate_future_datetime(v) if v is not None else v


class AppointmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    doctor_id: int
    patient_id: int
    scheduled_at: datetime
    status: AppointmentStatus
    reason: str | None
    created_at: datetime


# --------------------------------------------------------------------------- #
#  MedicalRecord (Медицинская запись)
# --------------------------------------------------------------------------- #
class MedicalRecordCreate(BaseModel):
    appointment_id: int
    diagnosis: str = Field(min_length=2)
    prescription: str | None = None
    notes: str | None = None


class MedicalRecordRead(MedicalRecordCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


# --------------------------------------------------------------------------- #
#  User (текущий пользователь)
# --------------------------------------------------------------------------- #
class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
