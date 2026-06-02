from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models, schemas
from app.dependencies import get_current_user, require_doctor

router = APIRouter(prefix="/records", tags=["Медициналық карта"])


@router.post("/", response_model=schemas.MedicalRecordResponse, status_code=201)
def create_record(data: schemas.MedicalRecordCreate, db: Session = Depends(get_db),
                  current_user: models.User = Depends(require_doctor)):
    """Медициналық жазба жасау — тек Дәрігер"""
    doctor = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
    if not doctor and current_user.role != models.RoleEnum.admin:
        raise HTTPException(status_code=404, detail="Дәрігер профилі табылмады")

    patient = db.query(models.User).filter(models.User.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Пациент табылмады")

    record = models.MedicalRecord(
        doctor_id=doctor.id if doctor else 1,
        **data.model_dump()
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/patient/{patient_id}", response_model=List[schemas.MedicalRecordResponse])
def patient_records(patient_id: int, db: Session = Depends(get_db),
                    current_user: models.User = Depends(get_current_user)):
    """Пациенттің медициналық картасы"""
    # Пациент тек өз картасын, Дәрігер/Админ барлығын көре алады
    if current_user.role == models.RoleEnum.patient and current_user.id != patient_id:
        raise HTTPException(status_code=403, detail="Рұқсат жоқ")

    return db.query(models.MedicalRecord).filter(
        models.MedicalRecord.patient_id == patient_id
    ).order_by(models.MedicalRecord.created_at.desc()).all()


@router.get("/{record_id}", response_model=schemas.MedicalRecordResponse)
def get_record(record_id: int, db: Session = Depends(get_db),
               current_user: models.User = Depends(get_current_user)):
    """Жазбаны көру"""
    record = db.query(models.MedicalRecord).filter(models.MedicalRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Жазба табылмады")

    if current_user.role == models.RoleEnum.patient and record.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Рұқсат жоқ")
    return record


@router.patch("/{record_id}", response_model=schemas.MedicalRecordResponse)
def update_record(record_id: int, data: schemas.MedicalRecordCreate,
                  db: Session = Depends(get_db),
                  current_user: models.User = Depends(require_doctor)):
    """Жазбаны жаңарту — тек Дәрігер"""
    record = db.query(models.MedicalRecord).filter(models.MedicalRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Жазба табылмады")

    doctor = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
    if doctor and record.doctor_id != doctor.id and current_user.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Тек өз жазбаңызды жаңарта аласыз")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return record
