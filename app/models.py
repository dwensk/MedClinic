"""
ORM-модели (SQLAlchemy 2.0, стиль Mapped / mapped_column).

Структура БД (7 связанных таблиц):

    users ──1:1── doctors ──N:1── departments
                     │
                     ├──1:N── schedules
                     └──1:N── appointments ──N:1── patients
                                   │
                                   └──1:1── medical_records

Нормализация: данные авторизации (users) отделены от профиля врача (doctors),
справочник отделений (departments) вынесен отдельно, медкарта (medical_records)
привязана к конкретному приёму (appointments).
"""

from datetime import datetime, date, time

from sqlalchemy import (
    String, Integer, Text, ForeignKey, DateTime, Date, Time,
    Enum as SAEnum, Boolean, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import UserRole, AppointmentStatus


class User(Base):
    """Пользователь системы (администратор или врач) — данные для входа."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.doctor, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Связь 1:1 — у пользователя-врача есть профиль Doctor.
    doctor: Mapped["Doctor | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class Department(Base):
    """Отделение клиники (справочник): кардиология, терапия и т. д."""
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    doctors: Mapped[list["Doctor"]] = relationship(back_populates="department")


class Doctor(Base):
    """Профиль врача. Привязан к учётной записи User (1:1) и к отделению (N:1)."""
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False)

    iin: Mapped[str] = mapped_column(String(12), unique=True, index=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    specialization: Mapped[str] = mapped_column(String(120), nullable=False)
    cabinet: Mapped[str | None] = mapped_column(String(20), nullable=True)

    user: Mapped["User"] = relationship(back_populates="doctor")
    department: Mapped["Department"] = relationship(back_populates="doctors")
    schedules: Mapped[list["Schedule"]] = relationship(
        back_populates="doctor", cascade="all, delete-orphan"
    )
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="doctor")


class Patient(Base):
    """Пациент клиники."""
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    iin: Mapped[str] = mapped_column(String(12), unique=True, index=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    appointments: Mapped[list["Appointment"]] = relationship(back_populates="patient")


class Schedule(Base):
    """График работы врача по дням недели."""
    __tablename__ = "schedules"
    # Один врач не может иметь два графика на один и тот же день недели.
    __table_args__ = (UniqueConstraint("doctor_id", "weekday", name="uq_doctor_weekday"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"))
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)   # 0 = Пн ... 6 = Вс
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    doctor: Mapped["Doctor"] = relationship(back_populates="schedules")


class Appointment(Base):
    """Запись пациента к врачу на конкретное время."""
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), nullable=False)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        SAEnum(AppointmentStatus), default=AppointmentStatus.scheduled, nullable=False
    )
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)  # повод обращения
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    doctor: Mapped["Doctor"] = relationship(back_populates="appointments")
    patient: Mapped["Patient"] = relationship(back_populates="appointments")
    # Связь 1:1 — у состоявшегося приёма есть медицинская запись.
    medical_record: Mapped["MedicalRecord | None"] = relationship(
        back_populates="appointment", uselist=False, cascade="all, delete-orphan"
    )


class MedicalRecord(Base):
    """Медицинская запись (результат приёма): диагноз, назначения."""
    __tablename__ = "medical_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    diagnosis: Mapped[str] = mapped_column(Text, nullable=False)
    prescription: Mapped[str | None] = mapped_column(Text, nullable=True)  # назначения / рецепт
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    appointment: Mapped["Appointment"] = relationship(back_populates="medical_record")
