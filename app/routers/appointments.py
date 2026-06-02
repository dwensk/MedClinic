from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import date
from app.database import get_db
from app import models, schemas
from app.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/appointments", tags=["Жазылулар"])


@router.post("/", response_model=schemas.AppointmentResponse, status_code=201)
def book_appointment(data: schemas.AppointmentCreate, db: Session = Depends(get_db),
                     current_user: models.User = Depends(get_current_user)):
    """Дәрігерге жазылу — пациент"""
    doctor = db.query(models.Doctor).filter(models.Doctor.id == data.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Дәрігер табылмады")

    # Бір уақытқа бірнеше жазылу болмасын
    conflict = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == data.doctor_id,
        models.Appointment.appointment_date == data.appointment_date,
        models.Appointment.appointment_time == data.appointment_time,
        models.Appointment.status.in_([models.StatusEnum.pending, models.StatusEnum.confirmed])
    ).first()
    if conflict:
        raise HTTPException(status_code=400, detail="Бұл уақытқа жазылу бар")

    appointment = models.Appointment(
        patient_id=current_user.id,
        doctor_id=data.doctor_id,
        appointment_date=data.appointment_date,
        appointment_time=data.appointment_time,
        reason=data.reason,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


@router.get("/my", response_model=List[schemas.AppointmentResponse])
def my_appointments(status: Optional[models.StatusEnum] = None,
                    db: Session = Depends(get_db),
                    current_user: models.User = Depends(get_current_user)):
    """Өзімнің жазылуларым"""
    query = db.query(models.Appointment).filter(models.Appointment.patient_id == current_user.id)
    if status:
        query = query.filter(models.Appointment.status == status)
    return query.order_by(models.Appointment.appointment_date).all()


@router.get("/doctor/{doctor_id}", response_model=List[schemas.AppointmentResponse])
def doctor_appointments(doctor_id: int, day: Optional[date] = None,
                        db: Session = Depends(get_db),
                        current_user: models.User = Depends(get_current_user)):
    """Дәрігердің жазылулары — Дәрігер немесе Әкімші"""
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Дәрігер табылмады")

    if current_user.role not in (models.RoleEnum.admin, models.RoleEnum.doctor):
        raise HTTPException(status_code=403, detail="Рұқсат жоқ")
    if current_user.role == models.RoleEnum.doctor and doctor.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Тек өз жазылуларыңызды көре аласыз")

    query = db.query(models.Appointment).filter(models.Appointment.doctor_id == doctor_id)
    if day:
        query = query.filter(models.Appointment.appointment_date == day)
    return query.order_by(models.Appointment.appointment_date, models.Appointment.appointment_time).all()


@router.get("/", response_model=List[schemas.AppointmentResponse])
def all_appointments(skip: int = 0, limit: int = 50, db: Session = Depends(get_db),
                     _: models.User = Depends(require_admin)):
    """Барлық жазылулар — тек Әкімші"""
    return db.query(models.Appointment).offset(skip).limit(limit).all()


@router.patch("/{appointment_id}/status", response_model=schemas.AppointmentResponse)
def update_status(appointment_id: int, data: schemas.AppointmentStatusUpdate,
                  db: Session = Depends(get_db),
                  current_user: models.User = Depends(get_current_user)):
    """Жазылу күйін өзгерту — Дәрігер (бекіту/болды) немесе Пациент (болдырмау)"""
    appt = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Жазылу табылмады")

    # Пациент тек "cancelled" қоя алады
    if current_user.role == models.RoleEnum.patient:
        if appt.patient_id != current_user.id:
            raise HTTPException(status_code=403, detail="Рұқсат жоқ")
        if data.status != models.StatusEnum.cancelled:
            raise HTTPException(status_code=403, detail="Пациент тек болдырмай алады")

    appt.status = data.status
    db.commit()
    db.refresh(appt)
    return appt


@router.delete("/{appointment_id}", status_code=204)
def delete_appointment(appointment_id: int, db: Session = Depends(get_db),
                       _: models.User = Depends(require_admin)):
    """Жазылуды өшіру — тек Әкімші"""
    appt = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Жазылу табылмады")
    db.delete(appt)
    db.commit()
