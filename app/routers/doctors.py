from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_role, _hash_password
from app.database import get_db
from app.enums import UserRole
from app.models import Department, Doctor, User
from app.schemas import DoctorCreate, DoctorUpdate, DoctorRead

router = APIRouter(tags=["Врачи"])


@router.get("/", response_model=list[DoctorRead], dependencies=[Depends(get_current_user)])
def list_doctors(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Doctor).offset(skip).limit(limit).all()


@router.post(
    "/",
    response_model=DoctorRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.admin))],
)
def create_doctor(data: DoctorCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует",
        )
    if db.query(Doctor).filter(Doctor.iin == data.iin).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Врач с таким ИИН уже зарегистрирован",
        )
    if not db.get(Department, data.department_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Отделение не найдено")

    # Учётная запись и профиль врача создаются в одной транзакции.
    user = User(
        email=data.email,
        hashed_password=_hash_password(data.password),
        full_name=data.full_name,
        role=UserRole.doctor,
    )
    db.add(user)
    db.flush()

    doctor = Doctor(
        user_id=user.id,
        department_id=data.department_id,
        iin=data.iin,
        phone=data.phone,
        specialization=data.specialization,
        cabinet=data.cabinet,
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


@router.get("/{doctor_id}", response_model=DoctorRead, dependencies=[Depends(get_current_user)])
def get_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doctor = db.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Врач не найден")
    return doctor


@router.patch(
    "/{doctor_id}",
    response_model=DoctorRead,
    dependencies=[Depends(require_role(UserRole.admin))],
)
def update_doctor(doctor_id: int, data: DoctorUpdate, db: Session = Depends(get_db)):
    doctor = db.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Врач не найден")
    update_data = data.model_dump(exclude_unset=True)
    # Проверяем, что новое отделение существует (если оно меняется).
    if "department_id" in update_data and not db.get(Department, update_data["department_id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Отделение не найдено")
    for field, value in update_data.items():
        setattr(doctor, field, value)
    db.commit()
    db.refresh(doctor)
    return doctor


@router.delete(
    "/{doctor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.admin))],
)
def delete_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doctor = db.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Врач не найден")
    # Нельзя удалить врача с существующими записями на приём.
    if doctor.appointments:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Нельзя удалить врача: есть записи на приём",
        )
    # Удаляем пользователя — ORM-каскад удалит профиль врача.
    db.delete(doctor.user)
    db.commit()
