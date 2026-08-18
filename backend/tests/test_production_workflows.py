"""High-value boundary tests for the clinic pilot workflow."""

import os
import sys
import tempfile
import asyncio
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.environ.update({
    "APP_ENV": "development",
    "DEMO_SEED": "1",
    "ENABLE_DEMO_TOOLS": "1",
    "DB_PATH": str(Path(tempfile.gettempdir()) / f"veloxacare-tests-{os.getpid()}.db"),
    "DATABASE_URL": "",
    "TURSO_DATABASE_URL": "",
    "TURSO_AUTH_TOKEN": "",
    "CRON_SECRET": "test-cron-secret",
    "META_MEDICATION_REMINDER_TEMPLATE": "",
    "BOOTSTRAP_ADMIN_EMAIL": "",
    "BOOTSTRAP_ADMIN_PASSWORD": "",
    "BOOTSTRAP_ADMIN_NAME": "",
})

import db  # noqa: E402
import main as main_module  # noqa: E402
from main import app, _claim_whatsapp_event, _finish_whatsapp_event  # noqa: E402
from config import demo_tools_enabled  # noqa: E402
from services import whatsapp  # noqa: E402


@pytest.fixture(scope="module")
def client():
    path = Path(db.DB_PATH)
    path.unlink(missing_ok=True)
    with TestClient(app) as test_client:
        yield test_client
    path.unlink(missing_ok=True)


@pytest.fixture(scope="module")
def staff(client: TestClient):
    response = client.post("/api/auth/login", json={
        "email": "admin@veloxacare.local",
        "password": "VeloxaCare-Local-Only",
    })
    assert response.status_code == 200
    return {"client": client, "csrf": response.json()["csrf_token"]}


def test_clinical_api_requires_authentication(client: TestClient):
    response = client.get("/api/patients")
    assert response.status_code == 401
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/-1"):
            pass


def test_session_allows_reads_and_csrf_protects_writes(staff):
    client, csrf = staff["client"], staff["csrf"]
    assert client.get("/api/patients").status_code == 200
    with client.websocket_connect("/ws/-1") as websocket:
        assert websocket is not None
    assert client.get("/api/stt/status").status_code == 200
    alert_id = client.get("/api/alerts").json()[0]["id"]
    assert client.post(f"/api/alerts/{alert_id}/acknowledge").status_code == 403
    acknowledged = client.post(
        f"/api/alerts/{alert_id}/acknowledge", headers={"X-CSRF-Token": csrf},
    )
    assert acknowledged.status_code == 200
    assert acknowledged.json()["assigned_to_name"] == "Local Demo Administrator"


def test_incomplete_integrations_allow_pending_enrollment_but_block_messaging(staff, monkeypatch):
    client, csrf = staff["client"], staff["csrf"]
    monkeypatch.setattr(
        main_module, "missing_production_config",
        lambda: ["META_APP_SECRET", "CRON_SECRET", "META_MEDICATION_REMINDER_TEMPLATE"],
    )
    assert client.get("/api/auth/me").status_code == 200
    assert client.get("/api/patients").status_code == 200
    pending = client.post(
        "/api/patients", headers={"X-CSRF-Token": csrf}, json={
            "name": "Setup Pending", "phone": "+233249999990", "age": 48,
            "category": "chronic", "condition": "Hypertension",
            "drug_name": "Amlodipine", "drug_dosage": "5mg once daily",
            "doctor_name": "Dr. Test", "preferred_language": "en",
            "reminder_time": "08:00", "consent_granted": False,
        },
    )
    assert pending.status_code == 200
    assert pending.json()["consent_status"] == "pending"
    assert pending.json()["welcome_delivery"]["mode"] == "consent_pending"

    blocked = client.post(
        "/api/patients", headers={"X-CSRF-Token": csrf}, json={
            "name": "Messaging Blocked", "phone": "+233249999989", "age": 48,
            "category": "chronic", "condition": "Hypertension",
            "drug_name": "Amlodipine", "drug_dosage": "5mg once daily",
            "doctor_name": "Dr. Test", "preferred_language": "en",
            "reminder_time": "08:00", "consent_granted": True,
        },
    )
    assert blocked.status_code == 503
    assert "Save this patient with consent unchecked" in blocked.json()["detail"]

    patient_id = pending.json()["id"]
    communication_blocked = client.patch(
        f"/api/patients/{patient_id}/communication",
        headers={"X-CSRF-Token": csrf},
        json={"consent_status": "granted", "communication_opt_in": True},
    )
    assert communication_blocked.status_code == 503
    assert "clinical writes are disabled" in communication_blocked.json()["detail"]


def test_enrollment_does_not_message_without_consent(staff):
    client, csrf = staff["client"], staff["csrf"]
    response = client.post("/api/patients", headers={"X-CSRF-Token": csrf}, json={
        "name": "Consent Pending", "phone": "+233249999991", "age": 50,
        "category": "chronic", "condition": "Hypertension",
        "drug_name": "Amlodipine", "drug_dosage": "5mg once daily",
        "doctor_name": "Dr. Test", "preferred_language": "en",
        "reminder_time": "08:00", "consent_granted": False,
    })
    assert response.status_code == 200
    patient = response.json()
    assert patient["consent_status"] == "pending"
    assert patient["welcome_delivery"]["mode"] == "consent_pending"
    assert client.get(f"/api/patients/{patient['id']}/messages").json() == []


def test_patient_stop_and_start_control_consent(staff):
    client, csrf = staff["client"], staff["csrf"]
    patient_id = client.get("/api/patients").json()[0]["id"]
    stopped = client.post(
        f"/api/patients/{patient_id}/messages", headers={"X-CSRF-Token": csrf},
        json={"message": "STOP"},
    )
    assert stopped.status_code == 200
    patient = client.get(f"/api/patients/{patient_id}").json()
    assert patient["consent_status"] == "withdrawn"
    assert not patient["communication_opt_in"]

    started = client.post(
        f"/api/patients/{patient_id}/messages", headers={"X-CSRF-Token": csrf},
        json={"message": "START"},
    )
    assert started.status_code == 200
    patient = client.get(f"/api/patients/{patient_id}").json()
    assert patient["consent_status"] == "granted"
    assert patient["communication_opt_in"]


def test_cron_rejects_missing_secret(client: TestClient):
    assert client.get("/api/cron/hourly").status_code == 401


def test_whatsapp_idempotency_survives_process_memory(client: TestClient):
    message_id = "wamid.durable-test"
    assert asyncio.run(_claim_whatsapp_event(message_id))
    asyncio.run(_finish_whatsapp_event(message_id))
    assert not asyncio.run(_claim_whatsapp_event(message_id))


def test_cron_records_a_durable_failed_dispatch(staff):
    client, csrf = staff["client"], staff["csrf"]
    patient_id = client.get("/api/patients").json()[0]["id"]
    hour = datetime.now(ZoneInfo("Africa/Accra")).strftime("%H:00")
    updated = client.patch(
        f"/api/patients/{patient_id}/communication",
        headers={"X-CSRF-Token": csrf},
        json={"reminder_time": hour, "consent_status": "granted", "communication_opt_in": True, "paused": False},
    )
    assert updated.status_code == 200
    run = client.get("/api/cron/hourly", headers={"Authorization": "Bearer test-cron-secret"})
    assert run.status_code == 200
    assert run.json()["due"] >= 1
    assert run.json()["failed"] >= 1


def test_production_mode_disables_demo_and_requires_webhook_signature(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("META_APP_SECRET", raising=False)
    assert not demo_tools_enabled()
    assert not whatsapp.verify_signature(b"{}", None)
