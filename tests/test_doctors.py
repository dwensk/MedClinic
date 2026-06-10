"""
Тесты CRUD-эндпоинтов /doctors.
"""

from datetime import datetime, timedelta, timezone

from tests.conftest import client

_DEPT = {"name": "Терапия", "description": "Терапевтическое отделение"}
_DOCTOR = {
    "email": "doc@test.kz",
    "password": "secret123",
    "full_name": "Тест Докторов",
    "iin": "123456789012",
    "phone": "+77011234567",
    "specialization": "Терапевт",
    "cabinet": "101",
}
_PATIENT = {
    "full_name": "Тест Пациентов",
    "iin": "000000000001",
    "phone": "+77019999999",
}


def _mk_dept():
    return client.post("/departments/", json=_DEPT).json()["id"]


def _mk_doctor(dept_id):
    return client.post("/doctors/", json={**_DOCTOR, "department_id": dept_id}).json()


# ---- CREATE ----

def test_create_doctor_returns_201():
    dept_id = _mk_dept()
    resp = client.post("/doctors/", json={**_DOCTOR, "department_id": dept_id})
    assert resp.status_code == 201
    body = resp.json()
    assert body["specialization"] == "Терапевт"
    assert body["iin"] == "123456789012"
    assert body["department_id"] == dept_id
    assert "id" in body


def test_create_doctor_unknown_department_returns_404():
    resp = client.post("/doctors/", json={**_DOCTOR, "department_id": 9999})
    assert resp.status_code == 404


def test_create_doctor_duplicate_email_returns_400():
    dept_id = _mk_dept()
    _mk_doctor(dept_id)
    resp = client.post("/doctors/", json={**_DOCTOR, "department_id": dept_id, "iin": "000000000099"})
    assert resp.status_code == 400


def test_create_doctor_duplicate_iin_returns_400():
    dept_id = _mk_dept()
    _mk_doctor(dept_id)
    resp = client.post("/doctors/", json={**_DOCTOR, "department_id": dept_id, "email": "other@test.kz"})
    assert resp.status_code == 400


# ---- LIST ----

def test_list_doctors_empty():
    resp = client.get("/doctors/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_doctors():
    dept_id = _mk_dept()
    _mk_doctor(dept_id)
    resp = client.get("/doctors/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_doctors_pagination():
    dept_id = _mk_dept()
    for i in range(4):
        client.post("/doctors/", json={
            **_DOCTOR,
            "department_id": dept_id,
            "email": f"doc{i}@test.kz",
            "iin": f"00000000000{i}",
        })
    resp = client.get("/doctors/?skip=1&limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ---- GET ----

def test_get_doctor_by_id():
    dept_id = _mk_dept()
    doctor = _mk_doctor(dept_id)
    resp = client.get(f"/doctors/{doctor['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == doctor["id"]


def test_get_doctor_not_found_returns_404():
    resp = client.get("/doctors/9999")
    assert resp.status_code == 404


# ---- UPDATE ----

def test_update_doctor_specialization():
    dept_id = _mk_dept()
    doctor = _mk_doctor(dept_id)
    resp = client.patch(f"/doctors/{doctor['id']}", json={"specialization": "Кардиолог"})
    assert resp.status_code == 200
    assert resp.json()["specialization"] == "Кардиолог"
    assert resp.json()["iin"] == "123456789012"  # ИИН не изменился


def test_update_doctor_department():
    dept_id = _mk_dept()
    dept2_id = client.post("/departments/", json={"name": "Кардиология"}).json()["id"]
    doctor = _mk_doctor(dept_id)
    resp = client.patch(f"/doctors/{doctor['id']}", json={"department_id": dept2_id})
    assert resp.status_code == 200
    assert resp.json()["department_id"] == dept2_id


def test_update_doctor_invalid_department_returns_404():
    dept_id = _mk_dept()
    doctor = _mk_doctor(dept_id)
    resp = client.patch(f"/doctors/{doctor['id']}", json={"department_id": 9999})
    assert resp.status_code == 404


def test_update_doctor_not_found_returns_404():
    resp = client.patch("/doctors/9999", json={"specialization": "Нет"})
    assert resp.status_code == 404


# ---- DELETE ----

def test_delete_doctor_returns_204():
    dept_id = _mk_dept()
    doctor = _mk_doctor(dept_id)
    resp = client.delete(f"/doctors/{doctor['id']}")
    assert resp.status_code == 204


def test_delete_doctor_then_get_returns_404():
    dept_id = _mk_dept()
    doctor = _mk_doctor(dept_id)
    client.delete(f"/doctors/{doctor['id']}")
    resp = client.get(f"/doctors/{doctor['id']}")
    assert resp.status_code == 404


def test_delete_doctor_not_found_returns_404():
    resp = client.delete("/doctors/9999")
    assert resp.status_code == 404


def test_delete_doctor_with_appointments_returns_409():
    dept_id = _mk_dept()
    doctor = _mk_doctor(dept_id)
    patient = client.post("/patients/", json=_PATIENT).json()
    future = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    client.post("/appointments/", json={
        "doctor_id": doctor["id"],
        "patient_id": patient["id"],
        "scheduled_at": future,
    })
    resp = client.delete(f"/doctors/{doctor['id']}")
    assert resp.status_code == 409
