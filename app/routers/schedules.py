from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models, schemas
from app.dependencies import require_doctor, require_admin, get_current_user

router = APIRouter(prefix="/schedules", tags=["Жұмыс кестесі"])


@router.get("/doctor/{doctor_id}", response_model=List[schemas.ScheduleResponse])
def get_doctor_schedules(doctor_id: int, db: Session = Depends(get_db)):
    """Дәрігердің жұмыс кестесін көру"""
    return db.query(models.Schedule).filter(models.Schedule.doctor_id == doctor_id).all()


@router.post("/", response_model=schemas.ScheduleResponse, status_code=201)
def create_schedule(data: schemas.ScheduleCreate, db: Session = Depends(get_db),
                    current_user: models.User = Depends(get_current_user)):
    """Жұмыс кестесін қосу — Дәрігер немесе Әкімші"""
    if current_user.role not in (models.RoleEnum.doctor, models.RoleEnum.admin):
        raise HTTPException(status_code=403, detail="Рұқсат жоқ")

    doctor = db.query(models.Doctor).filter(models.Doctor.id == data.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Дәрігер табылмады")

    # Дәрігер тек өзінің кестесін жасай алады
    if current_user.role == models.RoleEnum.doctor and doctor.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Тек өз кестеңізді жасай аласыз")

    # Бір күнде бір кесте ғана
    existing = db.query(models.Schedule).filter(
        models.Schedule.doctor_id == data.doctor_id,
        models.Schedule.day_of_week == data.day_of_week
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Бұл күнге кесте бұрыннан жасалған: {data.day_of_week}")

    schedule = models.Schedule(**data.model_dump())
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


@router.put("/{schedule_id}", response_model=schemas.ScheduleResponse)
def update_schedule(schedule_id: int, data: schemas.ScheduleCreate, db: Session = Depends(get_db),
                    current_user: models.User = Depends(get_current_user)):
    """Жұмыс кестесін жаңарту"""
    schedule = db.query(models.Schedule).filter(models.Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Кесте табылмады")

    doctor = db.query(models.Doctor).filter(models.Doctor.id == schedule.doctor_id).first()
    if current_user.role != models.RoleEnum.admin and doctor.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Рұқсат жоқ")

    for field, value in data.model_dump().items():
        setattr(schedule, field, value)
    db.commit()
    db.refresh(schedule)
    return schedule


@router.delete("/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: int, db: Session = Depends(get_db),
                    _: models.User = Depends(require_admin)):
    """Кестені өшіру — тек Әкімші"""
    schedule = db.query(models.Schedule).filter(models.Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Кесте табылмады")
    db.delete(schedule)
    db.commit()
