from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import date, datetime
from app.models import RoleEnum, StatusEnum
import re


# ─── USER SCHEMAS ─────────────────────────────────────────────
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 6:
            raise ValueError("Құпия сөз кемінде 6 таңбадан тұруы керек")
        return v

    @field_validator("phone")
    @classmethod
    def phone_format(cls, v):
        if v and not re.match(r"^\+?[\d\s\-\(\)]{7,15}$", v):
            raise ValueError("Телефон нөмірі дұрыс форматта емес")
        return v


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: RoleEnum
    phone: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None


# ─── AUTH SCHEMAS ─────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ─── DOCTOR SCHEMAS ───────────────────────────────────────────
class DoctorCreate(BaseModel):
    user_id: int
    specialty: str
    cabinet: Optional[str] = None
    experience_years: int = 0
    bio: Optional[str] = None

    @field_validator("experience_years")
    @classmethod
    def exp_non_negative(cls, v):
        if v < 0:
            raise ValueError("Тәжірибе жылдары теріс болмауы керек")
        return v


class DoctorResponse(BaseModel):
    id: int
    user_id: int
    specialty: str
    cabinet: Optional[str]
    experience_years: int
    bio: Optional[str]
    user: UserResponse

    model_config = {"from_attributes": True}


class DoctorUpdate(BaseModel):
    specialty: Optional[str] = None
    cabinet: Optional[str] = None
    experience_years: Optional[int] = None
    bio: Optional[str] = None


# ─── SCHEDULE SCHEMAS ─────────────────────────────────────────
VALID_DAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
TIME_PATTERN = re.compile(r"^\d{2}:\d{2}$")


class ScheduleCreate(BaseModel):
    doctor_id: int
    day_of_week: str
    start_time: str
    end_time: str
    slot_duration_min: int = 30

    @field_validator("day_of_week")
    @classmethod
    def valid_day(cls, v):
        if v.lower() not in VALID_DAYS:
            raise ValueError(f"Қате күн: {v}. Дұрыс мәндер: {VALID_DAYS}")
        return v.lower()

    @field_validator("start_time", "end_time")
    @classmethod
    def valid_time(cls, v):
        if not TIME_PATTERN.match(v):
            raise ValueError("Уақыт форматы HH:MM болуы керек (мысалы: 09:00)")
        return v

    @field_validator("slot_duration_min")
    @classmethod
    def valid_slot(cls, v):
        if v < 10 or v > 120:
            raise ValueError("Слот ұзақтығы 10-120 минут аралығында болуы керек")
        return v


class ScheduleResponse(BaseModel):
    id: int
    doctor_id: int
    day_of_week: str
    start_time: str
    end_time: str
    slot_duration_min: int

    model_config = {"from_attributes": True}


# ─── APPOINTMENT SCHEMAS ──────────────────────────────────────
class AppointmentCreate(BaseModel):
    doctor_id: int
    appointment_date: date
    appointment_time: str
    reason: Optional[str] = None

    @field_validator("appointment_time")
    @classmethod
    def valid_time(cls, v):
        if not TIME_PATTERN.match(v):
            raise ValueError("Уақыт форматы HH:MM болуы керек")
        return v

    @field_validator("appointment_date")
    @classmethod
    def future_date(cls, v):
        if v < date.today():
            raise ValueError("Жазылу күні бүгіннен кем болмауы керек")
        return v


class AppointmentResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    appointment_date: date
    appointment_time: str
    status: StatusEnum
    reason: Optional[str]

    model_config = {"from_attributes": True}


class AppointmentStatusUpdate(BaseModel):
    status: StatusEnum


# ─── MEDICAL RECORD SCHEMAS ────────────────────────────────────
class MedicalRecordCreate(BaseModel):
    patient_id: int
    appointment_id: Optional[int] = None
    diagnosis: str
    prescription: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("diagnosis")
    @classmethod
    def non_empty(cls, v):
        if not v.strip():
            raise ValueError("Диагноз бос болмауы керек")
        return v


class MedicalRecordResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    appointment_id: Optional[int]
    diagnosis: str
    prescription: Optional[str]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
