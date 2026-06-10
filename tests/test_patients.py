"""
Тесты CRUD-эндпоинтов /patients.
Изолированная БД и TestClient предоставляются через tests/conftest.py.
"""

from tests.conftest import client

_PATIENT = {
    "full_name": "Тест Тестов",
    "iin": "123456789012",
    "phone": "+77011234567",
    "birth_date": "1990-01-01",
    "gender": "М",
}


# ---- CREATE ----

def test_create_patient_returns_201():
    resp = client.post("/patients/", json=_PATIENT)
    assert resp.status_code == 201
    body = resp.json()
    assert body["iin"] == "123456789012"
    assert body["full_name"] == "Тест Тестов"
    assert "id" in body
    assert "created_at" in body


def test_create_patient_duplicate_iin_returns_400():
    client.post("/patients/", json=_PATIENT)
    resp = client.post("/patients/", json=_PATIENT)
    assert resp.status_code == 400


def test_create_patient_invalid_iin_returns_422():
    resp = client.post("/patients/", json={**_PATIENT, "iin": "123"})
    assert resp.status_code == 422


def test_create_patient_invalid_phone_returns_422():
    resp = client.post("/patients/", json={**_PATIENT, "phone": "12345"})
    assert resp.status_code == 422


# ---- LIST ----

def test_list_patients_empty():
    resp = client.get("/patients/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_patients_returns_all():
    client.post("/patients/", json=_PATIENT)
    client.post("/patients/", json={**_PATIENT, "iin": "000000000001"})
    resp = client.get("/patients/")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_patients_pagination():
    for i in range(5):
        client.post("/patients/", json={**_PATIENT, "iin": f"00000000000{i}"})
    resp = client.get("/patients/?skip=2&limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ---- GET ----

def test_get_patient_by_id():
    created = client.post("/patients/", json=_PATIENT).json()
    resp = client.get(f"/patients/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_patient_not_found_returns_404():
    resp = client.get("/patients/9999")
    assert resp.status_code == 404


# ---- UPDATE ----

def test_update_patient_full_name():
    created = client.post("/patients/", json=_PATIENT).json()
    resp = client.patch(f"/patients/{created['id']}", json={"full_name": "Новое Имя"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["full_name"] == "Новое Имя"
    assert body["iin"] == "123456789012"  # ИИН не изменился


def test_update_patient_phone_normalised():
    # Валидатор снимает пробелы/скобки/дефисы, но не конвертирует 8→+7.
    created = client.post("/patients/", json=_PATIENT).json()
    resp = client.patch(f"/patients/{created['id']}", json={"phone": "+7 (777) 123-45-67"})
    assert resp.status_code == 200
    assert resp.json()["phone"] == "+77771234567"


def test_update_patient_not_found_returns_404():
    resp = client.patch("/patients/9999", json={"full_name": "Никто"})
    assert resp.status_code == 404


# ---- DELETE ----

def test_delete_patient_returns_204():
    created = client.post("/patients/", json=_PATIENT).json()
    resp = client.delete(f"/patients/{created['id']}")
    assert resp.status_code == 204


def test_delete_patient_then_get_returns_404():
    created = client.post("/patients/", json=_PATIENT).json()
    client.delete(f"/patients/{created['id']}")
    resp = client.get(f"/patients/{created['id']}")
    assert resp.status_code == 404


def test_delete_patient_not_found_returns_404():
    resp = client.delete("/patients/9999")
    assert resp.status_code == 404
