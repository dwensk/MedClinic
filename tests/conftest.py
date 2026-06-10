"""
Общая тестовая инфраструктура.

- Единый in-memory SQLite + StaticPool.
- get_db переопределён на тестовую БД.
- get_current_user переопределён mock-администратором, чтобы CRUD-тесты
  не зависели от реального JWT. Тесты в test_auth.py снимают этот override.
- _fresh_db (autouse) пересоздаёт схему перед каждым тестом.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.auth import get_current_user
from app.database import Base, get_db
from app.enums import UserRole
from app.models import User

_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = sessionmaker(bind=_engine, autoflush=False, autocommit=False)

# Мок-пользователь с правами администратора для CRUD-тестов.
_mock_admin = User(
    id=999,
    email="mock@admin.test",
    full_name="Mock Admin",
    role=UserRole.admin,
    is_active=True,
    hashed_password="mock",
)


def _override_get_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


def _override_get_current_user() -> User:
    return _mock_admin


app.dependency_overrides[get_db] = _override_get_db
app.dependency_overrides[get_current_user] = _override_get_current_user

client = TestClient(app)


@pytest.fixture(autouse=True)
def _fresh_db():
    """Пересоздаёт все таблицы перед каждым тестом и удаляет после."""
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)
