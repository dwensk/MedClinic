"""
Тесты CRUD-эндпоинтов /appointments.
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
}
_PATIENT = {
    "full_name": "Тест Пациентов",
    "iin": "000000000001",
    "phone": "+77019999999",
}


def _future(days=1):
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mk_doctor():
    dept_id = client.post("/departments/", json=_DEPT).json()["id"]
    return client.post("/doctors/", json={**_DOCTOR, "department_id": dept_id}).json()["id"]


def _mk_patient(iin="000000000001"):
    return client.post("/patients/", json={**_PATIENT, "iin": iin}).json()["id"]


def _appt(doctor_id, patient_id, dt=None):
    return {
        "doctor_id": doctor_id,
        "patient_id": patient_id,
        "scheduled_at": dt or _future(),
        "reason": "Консультация",
    }


# ---- CREATE ----

def test_create_appointment_returns_201():
    doc_id = _mk_doctor()
    pat_id = _mk_patient()
    resp = client.post("/appointments/", json=_appt(doc_id, pat_id))
    assert resp.status_code == 201
    body = resp.json()
    assert body["doctor_id"] == doc_id
    assert body["patient_id"] == pat_id
    assert body["status"] == "scheduled"
    assert "id" in body
    assert "created_at" in body


def test_create_appointment_unknown_doctor_returns_404():
    pat_id = _mk_patient()
    resp = client.post("/appointments/", json=_appt(9999, pat_id))
    assert resp.status_code == 404


def test_create_appointment_unknown_patient_returns_404():
    doc_id = _mk_doctor()
    resp = client.post("/appointments/", json=_appt(doc_id, 9999))
    assert resp.status_code == 404


def test_create_appointment_past_datetime_returns_422():
    doc_id = _mk_doctor()
    pat_id = _mk_patient()
    past = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    resp = client.post("/appointments/", json=_appt(doc_id, pat_id, dt=past))
    assert resp.status_code == 422


def test_create_appointment_double_booking_returns_409():
    doc_id = _mk_doctor()
    pat1_id = _mk_patient(iin="000000000001")
    pat2_id = _mk_patient(iin="000000000002")
    dt = _future(days=3)
    client.post("/appointments/", json=_appt(doc_id, pat1_id, dt=dt))
    resp = client.post("/appointments/", json=_appt(doc_id, pat2_id, dt=dt))
    assert resp.status_code == 409


def test_create_appointment_same_slot_cancelled_ok():
    # Отменённая запись не блокирует слот.
    doc_id = _mk_doctor()
    pat1_id = _mk_patient(iin="000000000001")
    pat2_id = _mk_patient(iin="000000000002")
    dt = _future(days=4)
    first = client.post("/appointments/", json=_appt(doc_id, pat1_id, dt=dt)).json()
    client.patch(f"/appointments/{first['id']}", json={"status": "cancelled"})
    resp = client.post("/appointments/", json=_appt(doc_id, pat2_id, dt=dt))
    assert resp.status_code == 201


# ---- LIST ----

def test_list_appointments_empty():
    resp = client.get("/appointments/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_appointments():
    doc_id = _mk_doctor()
    pat_id = _mk_patient()
    client.post("/appointments/", json=_appt(doc_id, pat_id))
    resp = client.get("/appointments/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_appointments_filter_by_doctor():
    doc_id = _mk_doctor()
    pat_id = _mk_patient()
    client.post("/appointments/", json=_appt(doc_id, pat_id))
    resp = client.get(f"/appointments/?doctor_id={doc_id}")
    assert resp.status_code == 200
    assert all(a["doctor_id"] == doc_id for a in resp.json())


def test_list_appointments_filter_by_patient():
    doc_id = _mk_doctor()
    pat_id = _mk_patient()
    client.post("/appointments/", json=_appt(doc_id, pat_id))
    resp = client.get(f"/appointments/?patient_id={pat_id}")
    assert resp.status_code == 200
    assert all(a["patient_id"] == pat_id for a in resp.json())


# ---- GET ----

def test_get_appointment_by_id():
    doc_id = _mk_doctor()
    pat_id = _mk_patient()
    created = client.post("/appointments/", json=_appt(doc_id, pat_id)).json()
    resp = client.get(f"/appointments/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_appointment_not_found_returns_404():
    resp = client.get("/appointments/9999")
    assert resp.status_code == 404


# ---- UPDATE ----

def test_update_appointment_status():
    doc_id = _mk_doctor()
    pat_id = _mk_patient()
    created = client.post("/appointments/", json=_appt(doc_id, pat_id)).json()
    resp = client.patch(f"/appointments/{created['id']}", json={"status": "completed"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


def test_update_appointment_reason():
    doc_id = _mk_doctor()
    pat_id = _mk_patient()
    created = client.post("/appointments/", json=_appt(doc_id, pat_id)).json()
    resp = client.patch(f"/appointments/{created['id']}", json={"reason": "Повторный приём"})
    assert resp.status_code == 200
    assert resp.json()["reason"] == "Повторный приём"


def test_update_appointment_past_datetime_returns_422():
    doc_id = _mk_doctor()
    pat_id = _mk_patient()
    created = client.post("/appointments/", json=_appt(doc_id, pat_id)).json()
    past = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    resp = client.patch(f"/appointments/{created['id']}", json={"scheduled_at": past})
    assert resp.status_code == 422


def test_update_appointment_not_found_returns_404():
    resp = client.patch("/appointments/9999", json={"status": "cancelled"})
    assert resp.status_code == 404


# ---- DELETE ----

def test_delete_appointment_returns_204():
    doc_id = _mk_doctor()
    pat_id = _mk_patient()
    created = client.post("/appointments/", json=_appt(doc_id, pat_id)).json()
    resp = client.delete(f"/appointments/{created['id']}")
    assert resp.status_code == 204


def test_delete_appointment_then_get_returns_404():
    doc_id = _mk_doctor()
    pat_id = _mk_patient()
    created = client.post("/appointments/", json=_appt(doc_id, pat_id)).json()
    client.delete(f"/appointments/{created['id']}")
    resp = client.get(f"/appointments/{created['id']}")
    assert resp.status_code == 404


def test_delete_appointment_not_found_returns_404():
    resp = client.delete("/appointments/9999")
    assert resp.status_code == 404
