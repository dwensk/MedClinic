"""
Тесты JWT-авторизации и ролевого доступа.

Снимают mock get_current_user из conftest, чтобы проверять настоящую JWT-логику.
"""

import bcrypt as _bcrypt
import pytest

from app.auth import get_current_user
from app.enums import UserRole
from app.models import User
from tests.conftest import (
    app,
    client,
    _TestSession,
    _override_get_current_user,
)


def _mk_user(email: str, password: str, role: UserRole = UserRole.admin) -> User:
    """Создаёт пользователя в тестовой БД с настоящим bcrypt-хэшем (rounds=4 для скорости)."""
    hashed = _bcrypt.hashpw(password.encode(), _bcrypt.gensalt(rounds=4)).decode()
    db = _TestSession()
    try:
        user = User(
            email=email,
            hashed_password=hashed,
            full_name="Тест",
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def _login(email: str, password: str) -> dict:
    return client.post("/auth/login", data={"username": email, "password": password})


@pytest.fixture(autouse=True)
def _real_auth():
    """Убирает mock-авторизацию — в этом модуле проверяем настоящий JWT."""
    app.dependency_overrides.pop(get_current_user, None)
    yield
    app.dependency_overrides[get_current_user] = _override_get_current_user


# ---- Вход ----

def test_login_admin_returns_token():
    _mk_user("admin@test.kz", "secret123", UserRole.admin)
    resp = _login("admin@test.kz", "secret123")
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_doctor_returns_token():
    _mk_user("doc@test.kz", "pass456", UserRole.doctor)
    resp = _login("doc@test.kz", "pass456")
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password_returns_401():
    _mk_user("admin@test.kz", "correct")
    resp = _login("admin@test.kz", "wrong")
    assert resp.status_code == 401


def test_login_unknown_email_returns_401():
    resp = _login("nobody@test.kz", "pass")
    assert resp.status_code == 401


def test_login_inactive_user_returns_403():
    db = _TestSession()
    try:
        hashed = _bcrypt.hashpw(b"pass", _bcrypt.gensalt(rounds=4)).decode()
        user = User(email="inactive@test.kz", hashed_password=hashed,
                    full_name="Тест", role=UserRole.doctor, is_active=False)
        db.add(user)
        db.commit()
    finally:
        db.close()
    resp = _login("inactive@test.kz", "pass")
    assert resp.status_code == 403


# ---- 401 без токена ----

def test_get_departments_without_token_returns_401():
    assert client.get("/departments/").status_code == 401


def test_get_doctors_without_token_returns_401():
    assert client.get("/doctors/").status_code == 401


def test_get_appointments_without_token_returns_401():
    assert client.get("/appointments/").status_code == 401


def test_get_patients_without_token_returns_401():
    assert client.get("/patients/").status_code == 401


def test_post_departments_without_token_returns_401():
    assert client.post("/departments/", json={"name": "Терапия"}).status_code == 401


# ---- 401 с испорченным токеном ----

def test_bad_token_returns_401():
    resp = client.get("/departments/", headers={"Authorization": "Bearer not.a.token"})
    assert resp.status_code == 401


# ---- 403: доктор обращается к admin-only маршруту ----

def _auth_header(email: str, password: str) -> dict:
    token = _login(email, password).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_doctor_cannot_create_department():
    _mk_user("doc@test.kz", "pass", UserRole.doctor)
    resp = client.post(
        "/departments/",
        json={"name": "Терапия"},
        headers=_auth_header("doc@test.kz", "pass"),
    )
    assert resp.status_code == 403


def test_doctor_cannot_delete_department():
    admin = _mk_user("adm@test.kz", "adm123", UserRole.admin)
    _mk_user("doc@test.kz", "doc123", UserRole.doctor)

    dept = client.post(
        "/departments/",
        json={"name": "Терапия"},
        headers=_auth_header("adm@test.kz", "adm123"),
    ).json()

    resp = client.delete(
        f"/departments/{dept['id']}",
        headers=_auth_header("doc@test.kz", "doc123"),
    )
    assert resp.status_code == 403


def test_doctor_cannot_patch_department():
    _mk_user("adm@test.kz", "adm", UserRole.admin)
    _mk_user("doc@test.kz", "doc", UserRole.doctor)

    dept = client.post(
        "/departments/",
        json={"name": "Терапия"},
        headers=_auth_header("adm@test.kz", "adm"),
    ).json()

    resp = client.patch(
        f"/departments/{dept['id']}",
        json={"name": "Кардиология"},
        headers=_auth_header("doc@test.kz", "doc"),
    )
    assert resp.status_code == 403


# ---- 200: admin на admin-only маршруте ----

def test_admin_can_create_department():
    _mk_user("adm@test.kz", "secret", UserRole.admin)
    resp = client.post(
        "/departments/",
        json={"name": "Терапия"},
        headers=_auth_header("adm@test.kz", "secret"),
    )
    assert resp.status_code == 201


# ---- Доктор читает открытые маршруты ----

def test_doctor_can_list_departments():
    _mk_user("doc@test.kz", "pass", UserRole.doctor)
    resp = client.get("/departments/", headers=_auth_header("doc@test.kz", "pass"))
    assert resp.status_code == 200


def test_doctor_can_list_appointments():
    _mk_user("doc@test.kz", "pass", UserRole.doctor)
    resp = client.get("/appointments/", headers=_auth_header("doc@test.kz", "pass"))
    assert resp.status_code == 200
