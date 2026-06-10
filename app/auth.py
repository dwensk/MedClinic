"""
Авторизация: хэширование паролей, JWT-токены, зависимости FastAPI.
"""
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt as _bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.enums import UserRole
from app.models import User
from app.schemas import UserRead

router = APIRouter(tags=["Авторизация"])

_ALGORITHM = "HS256"
_TOKEN_EXPIRE_HOURS = 8

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ---- Пароли ----

def _hash_password(password: str) -> str:
    """Хэширует пароль через bcrypt перед сохранением в БД."""
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    """Сверяет открытый пароль с хранимым bcrypt-хэшем."""
    return _bcrypt.checkpw(plain.encode(), hashed.encode())


# ---- JWT ----

def _create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=_TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": str(user.id), "role": user.role.value, "exp": expire},
        settings.SECRET_KEY,
        algorithm=_ALGORITHM,
    )


# ---- Эндпоинт входа ----

@router.post("/login")
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    """Вход по email/паролю — возвращает Bearer-токен."""
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not _verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учётная запись отключена",
        )
    return {"access_token": _create_access_token(user), "token_type": "bearer"}


# ---- Зависимости ----

def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> User:
    """Декодирует Bearer-токен и возвращает текущего пользователя."""
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить токен",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[_ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise exc
    except JWTError:
        raise exc
    user = db.get(User, int(user_id))
    if not user or not user.is_active:
        raise exc
    return user


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    """Возвращает профиль текущего авторизованного пользователя."""
    return current_user


def require_role(*roles: UserRole):
    """
    Фабрика зависимостей: требует, чтобы текущий пользователь имел одну из указанных ролей.

    Пример: dependencies=[Depends(require_role(UserRole.admin))]
    """
    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для выполнения операции",
            )
        return current_user
    return _check
