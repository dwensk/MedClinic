"""
Тесты CRUD-эндпоинтов /departments.
"""

from tests.conftest import client

_DEPT = {"name": "Терапия", "description": "Терапевтическое отделение"}

_DOCTOR = {
    "email": "doc@test.kz",
    "password": "secret123",
    "full_name": "Тест Докторов",
    "iin": "123456789012",
    "phone": "+77011234567",
    "specialization": "Терапевт",
}


# ---- CREATE ----

def test_create_department_returns_201():
    resp = client.post("/departments/", json=_DEPT)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Терапия"
    assert body["description"] == "Терапевтическое отделение"
    assert "id" in body


def test_create_department_duplicate_name_returns_400():
    client.post("/departments/", json=_DEPT)
    resp = client.post("/departments/", json=_DEPT)
    assert resp.status_code == 400


def test_create_department_no_description():
    resp = client.post("/departments/", json={"name": "Хирургия"})
    assert resp.status_code == 201
    assert resp.json()["description"] is None


# ---- LIST ----

def test_list_departments_empty():
    resp = client.get("/departments/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_departments():
    client.post("/departments/", json=_DEPT)
    client.post("/departments/", json={"name": "Кардиология"})
    resp = client.get("/departments/")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ---- GET ----

def test_get_department_by_id():
    created = client.post("/departments/", json=_DEPT).json()
    resp = client.get(f"/departments/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_department_not_found_returns_404():
    resp = client.get("/departments/9999")
    assert resp.status_code == 404


# ---- UPDATE ----

def test_update_department_name():
    created = client.post("/departments/", json=_DEPT).json()
    resp = client.patch(f"/departments/{created['id']}", json={"name": "Кардиология"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Кардиология"
    assert body["description"] == _DEPT["description"]  # описание не изменилось


def test_update_department_clear_description():
    created = client.post("/departments/", json=_DEPT).json()
    resp = client.patch(f"/departments/{created['id']}", json={"description": None})
    assert resp.status_code == 200
    assert resp.json()["description"] is None


def test_update_department_not_found_returns_404():
    resp = client.patch("/departments/9999", json={"name": "Нет"})
    assert resp.status_code == 404


# ---- DELETE ----

def test_delete_department_returns_204():
    created = client.post("/departments/", json=_DEPT).json()
    resp = client.delete(f"/departments/{created['id']}")
    assert resp.status_code == 204


def test_delete_department_then_get_returns_404():
    created = client.post("/departments/", json=_DEPT).json()
    client.delete(f"/departments/{created['id']}")
    resp = client.get(f"/departments/{created['id']}")
    assert resp.status_code == 404


def test_delete_department_not_found_returns_404():
    resp = client.delete("/departments/9999")
    assert resp.status_code == 404


def test_delete_department_with_doctor_returns_409():
    dept = client.post("/departments/", json=_DEPT).json()
    client.post("/doctors/", json={**_DOCTOR, "department_id": dept["id"]})
    resp = client.delete(f"/departments/{dept['id']}")
    assert resp.status_code == 409
