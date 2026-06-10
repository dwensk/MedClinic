from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import require_role
from app.database import get_db
from app.enums import AppointmentStatus, UserRole
from app.models import Appointment, Doctor, Patient
from app.schemas import AppointmentCreate, AppointmentUpdate, AppointmentRead

router = APIRouter(tags=["Записи на приём"])

# Записями управляют и администратор, и врачи.
_any_staff = Depends(require_role(UserRole.admin, UserRole.doctor))


@router.get("/", response_model=list[AppointmentRead], dependencies=[_any_staff])
def list_appointments(
    skip: int = 0,
    limit: int = 100,
    doctor_id: int | None = None,
    patient_id: int | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Appointment)
    if doctor_id is not None:
        q = q.filter(Appointment.doctor_id == doctor_id)
    if patient_id is not None:
        q = q.filter(Appointment.patient_id == patient_id)
    return q.offset(skip).limit(limit).all()


@router.post(
    "/",
    response_model=AppointmentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_any_staff],
)
def create_appointment(data: AppointmentCreate, db: Session = Depends(get_db)):
    if not db.get(Doctor, data.doctor_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Врач не найден")
    if not db.get(Patient, data.patient_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пациент не найден")
    # Двойная запись: один врач не может принимать двух пациентов одновременно.
    conflict = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == data.doctor_id,
            Appointment.scheduled_at == data.scheduled_at,
            Appointment.status != AppointmentStatus.cancelled,
        )
        .first()
    )
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Врач уже занят в указанное время",
        )
    appointment = Appointment(**data.model_dump())
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


@router.get("/{appt_id}", response_model=AppointmentRead, dependencies=[_any_staff])
def get_appointment(appt_id: int, db: Session = Depends(get_db)):
    appt = db.get(Appointment, appt_id)
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена")
    return appt


@router.patch("/{appt_id}", response_model=AppointmentRead, dependencies=[_any_staff])
def update_appointment(appt_id: int, data: AppointmentUpdate, db: Session = Depends(get_db)):
    appt = db.get(Appointment, appt_id)
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(appt, field, value)
    db.commit()
    db.refresh(appt)
    return appt


@router.delete("/{appt_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_any_staff])
def delete_appointment(appt_id: int, db: Session = Depends(get_db)):
    appt = db.get(Appointment, appt_id)
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена")
    db.delete(appt)
    db.commit()
