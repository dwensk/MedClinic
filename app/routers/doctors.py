from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.database import get_db
from app import models, schemas
from app.dependencies import require_admin, get_current_user

router = APIRouter(prefix="/doctors", tags=["Дәрігерлер"])


@router.get("/", response_model=List[schemas.DoctorResponse])
def list_doctors(specialty: Optional[str] = None, db: Session = Depends(get_db)):
    """Барлық дәрігерлерді көру (фильтр: мамандық)"""
    query = db.query(models.Doctor).options(joinedload(models.Doctor.user))
    if specialty:
        query = query.filter(models.Doctor.specialty.ilike(f"%{specialty}%"))
    return query.all()


@router.get("/{doctor_id}", response_model=schemas.DoctorResponse)
def get_doctor(doctor_id: int, db: Session = Depends(get_db)):
    """Дәрігер профилін көру"""
    doctor = db.query(models.Doctor).options(joinedload(models.Doctor.user)).filter(
        models.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Дәрігер табылмады")
    return doctor


@router.post("/", response_model=schemas.DoctorResponse, status_code=201)
def create_doctor(data: schemas.DoctorCreate, db: Session = Depends(get_db),
                  _: models.User = Depends(require_admin)):
    """Дәрігер профилін жасау — тек Әкімші"""
    user = db.query(models.User).filter(models.User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пайдаланушы табылмады")

    existing = db.query(models.Doctor).filter(models.Doctor.user_id == data.user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Бұл пайдаланушының дәрігер профилі бар")

    doctor = models.Doctor(**data.model_dump())
    db.add(doctor)

    user.role = models.RoleEnum.doctor
    db.commit()
    db.refresh(doctor)
    return db.query(models.Doctor).options(joinedload(models.Doctor.user)).filter(
        models.Doctor.id == doctor.id).first()


@router.patch("/{doctor_id}", response_model=schemas.DoctorResponse)
def update_doctor(doctor_id: int, data: schemas.DoctorUpdate, db: Session = Depends(get_db),
                  current_user: models.User = Depends(get_current_user)):
    """Дәрігер профилін жаңарту"""
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Дәрігер табылмады")

    # Тек өз профилін немесе Admin жаңарта алады
    if current_user.role != models.RoleEnum.admin and doctor.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Рұқсат жоқ")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(doctor, field, value)
    db.commit()
    db.refresh(doctor)
    return db.query(models.Doctor).options(joinedload(models.Doctor.user)).filter(
        models.Doctor.id == doctor.id).first()


@router.delete("/{doctor_id}", status_code=204)
def delete_doctor(doctor_id: int, db: Session = Depends(get_db),
                  _: models.User = Depends(require_admin)):
    """Дәрігер профилін өшіру — тек Әкімші"""
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Дәрігер табылмады")
    db.delete(doctor)
    db.commit()
