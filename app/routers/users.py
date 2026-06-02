from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models, schemas
from app.dependencies import require_admin, get_current_user

router = APIRouter(prefix="/users", tags=["Пайдаланушылар"])


@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    """Өз профилімді көру"""
    return current_user


@router.patch("/me", response_model=schemas.UserResponse)
def update_me(data: schemas.UserUpdate, db: Session = Depends(get_db),
              current_user: models.User = Depends(get_current_user)):
    """Өз профилімді жаңарту"""
    if data.name:
        current_user.name = data.name
    if data.phone:
        current_user.phone = data.phone
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/", response_model=List[schemas.UserResponse])
def list_users(skip: int = 0, limit: int = 20, db: Session = Depends(get_db),
               _: models.User = Depends(require_admin)):
    """Барлық пайдаланушыларды көру — тек Әкімші"""
    return db.query(models.User).offset(skip).limit(limit).all()


@router.get("/{user_id}", response_model=schemas.UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db),
             _: models.User = Depends(require_admin)):
    """Пайдаланушы профилі — тек Әкімші"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пайдаланушы табылмады")
    return user


@router.patch("/{user_id}/role", response_model=schemas.UserResponse)
def change_role(user_id: int, role: models.RoleEnum, db: Session = Depends(get_db),
                _: models.User = Depends(require_admin)):
    """Пайдаланушы рөлін өзгерту — тек Әкімші"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пайдаланушы табылмады")
    user.role = role
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db),
                _: models.User = Depends(require_admin)):
    """Пайдаланушыны өшіру — тек Әкімші"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пайдаланушы табылмады")
    db.delete(user)
    db.commit()
