from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_role
from app.database import get_db
from app.enums import UserRole
from app.models import Department
from app.schemas import DepartmentCreate, DepartmentUpdate, DepartmentRead

router = APIRouter(tags=["Отделения"])


@router.get("/", response_model=list[DepartmentRead], dependencies=[Depends(get_current_user)])
def list_departments(db: Session = Depends(get_db)):
    return db.query(Department).all()


@router.post(
    "/",
    response_model=DepartmentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.admin))],
)
def create_department(data: DepartmentCreate, db: Session = Depends(get_db)):
    # Название отделения уникально в рамках клиники.
    if db.query(Department).filter(Department.name == data.name).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Отделение с таким названием уже существует",
        )
    dept = Department(**data.model_dump())
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


@router.get("/{dept_id}", response_model=DepartmentRead, dependencies=[Depends(get_current_user)])
def get_department(dept_id: int, db: Session = Depends(get_db)):
    dept = db.get(Department, dept_id)
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Отделение не найдено")
    return dept


@router.patch(
    "/{dept_id}",
    response_model=DepartmentRead,
    dependencies=[Depends(require_role(UserRole.admin))],
)
def update_department(dept_id: int, data: DepartmentUpdate, db: Session = Depends(get_db)):
    dept = db.get(Department, dept_id)
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Отделение не найдено")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(dept, field, value)
    db.commit()
    db.refresh(dept)
    return dept


@router.delete(
    "/{dept_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.admin))],
)
def delete_department(dept_id: int, db: Session = Depends(get_db)):
    dept = db.get(Department, dept_id)
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Отделение не найдено")
    # Нельзя удалить отделение, к которому прикреплены врачи.
    if dept.doctors:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Нельзя удалить отделение: к нему прикреплены врачи",
        )
    db.delete(dept)
    db.commit()
