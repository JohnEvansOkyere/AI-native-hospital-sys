"""High-value boundary tests for the clinic pilot workflow."""

import json
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
    # Hermetic: no model calls leave the test run, whatever the local .env holds.
    "ANTHROPIC_API_KEY": "",
    "GROQ_API_KEY": "",
    "META_MEDICATION_REMINDER_TEMPLATE": "",
    "BOOTSTRAP_ADMIN_EMAIL": "",
    "BOOTSTRAP_ADMIN_PASSWORD": "",
    "BOOTSTRAP_ADMIN_NAME": "",
})

import db  # noqa: E402
import main as main_module  # noqa: E402
from main import app, _enqueue_whatsapp_message  # noqa: E402
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
        main_module, "missing_messaging_config", lambda: ["META_APP_SECRET", "CRON_SECRET"],
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


def test_missing_reminder_template_does_not_block_care_team_writes(monkeypatch):
    """A missing reminder template degrades scheduled reminders only. It must
    never stop the care team from contacting a patient."""
    import config
    monkeypatch.setenv("APP_ENV", "production")
    for name in config.MESSAGING_REQUIRED:
        monkeypatch.setenv(name, "set")
    monkeypatch.delenv("META_MEDICATION_REMINDER_TEMPLATE", raising=False)
    assert config.missing_messaging_config() == []
    assert config.missing_production_config() == ["META_MEDICATION_REMINDER_TEMPLATE"]


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
    message = {"id": "wamid.durable-test", "from": "233000000000", "type": "text",
               "text": {"body": "hello"}}
    assert asyncio.run(_enqueue_whatsapp_message(message)) == "wamid.durable-test"
    assert asyncio.run(_enqueue_whatsapp_message(message)) == ""


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


def test_public_password_reset_is_not_exposed(client: TestClient):
    # A separate client: signing in again here must not replace the shared
    # staff session the other tests rely on.
    client = TestClient(app)
    response = client.post("/api/auth/password-reset", json={
        "email": "admin@veloxacare.local", "password": "x",
    })
    assert response.status_code in {401, 404, 405}
    login = client.post("/api/auth/login", json={
        "email": "admin@veloxacare.local", "password": "VeloxaCare-Local-Only",
    })
    assert login.status_code == 200


def test_failed_processing_replies_with_safety_message_and_opens_case(staff, monkeypatch):
    client = staff["client"]
    patient = client.get("/api/patients").json()[0]
    sent: list[tuple[str, str]] = []

    async def fake_send_text(to: str, body: str) -> bool:
        sent.append((to, body))
        return True

    async def broken_ingest(*args, **kwargs):
        raise RuntimeError("simulated database outage")

    monkeypatch.setattr(whatsapp, "send_text", fake_send_text)
    monkeypatch.setattr(main_module, "ingest_patient_message", broken_ingest)

    result = asyncio.run(main_module._process_whatsapp_message({
        "id": "wamid.processing-failure-test",
        "from": whatsapp.normalize_phone(patient["phone"]),
        "type": "text",
        "text": {"body": "my chest is very tight"},
    }))

    assert result["status"] == "processing_failed"
    assert len(sent) == 1
    assert "112" in sent[0][1] and "193" in sent[0][1]
    case = next(
        alert for alert in client.get("/api/alerts").json()
        if alert["patient_id"] == patient["id"]
        and alert["details"].get("reason") == "processing_failed"
    )
    assert case["risk_level"] == "red"
    assert case["details"]["last_message"] == "my chest is very tight"


def _send_as_patient(client: TestClient, csrf: str, patient_id: int, text: str) -> dict:
    response = client.post(
        f"/api/patients/{patient_id}/messages",
        headers={"X-CSRF-Token": csrf}, json={"message": text},
    )
    assert response.status_code == 200
    return response.json()


def _open_case_for(client: TestClient, patient_id: int, predicate) -> dict:
    return next(
        alert for alert in client.get("/api/alerts").json()
        if alert["patient_id"] == patient_id and predicate(alert)
    )


def test_rules_beat_the_llm_and_first_barrier_opens_a_case(staff, monkeypatch):
    from services import bot

    async def llm_says_forgot(*args, **kwargs):
        return "forgot"

    async def llm_says_other(*args, **kwargs):
        return "other"

    monkeypatch.setattr(bot, "detect_reason_ai", llm_says_forgot)
    monkeypatch.setattr(bot, "classify_intent", llm_says_other)
    client, csrf = staff["client"], staff["csrf"]
    patient_id = client.get("/api/patients").json()[-1]["id"]
    text = "I couldn't afford it this week so I forgot"

    result = _send_as_patient(client, csrf, patient_id, text)

    assert result["reply"]["reason"] == "cost"
    assert result["escalation_created"]
    case = _open_case_for(
        client, patient_id, lambda a: a["details"].get("last_message") == text,
    )
    assert case["details"]["reason"] == "cost"
    assert case["risk_level"] in {"amber", "red"}


def test_low_bp_in_free_text_opens_a_case(staff):
    client, csrf = staff["client"], staff["csrf"]
    patient_id = client.get("/api/patients").json()[-1]["id"]
    asyncio.run(_reset_flow(patient_id))

    result = _send_as_patient(client, csrf, patient_id, "my reading today is 85/50")

    assert "Excellent" not in result["reply"]["body"]
    assert result["escalation_created"]
    _open_case_for(client, patient_id, lambda a: a["details"].get("reading") == "85/50")


def test_calm_reading_does_not_clear_an_open_red_case(staff):
    client, csrf = staff["client"], staff["csrf"]
    patient_id = client.get("/api/patients").json()[-1]["id"]
    asyncio.run(_reset_flow(patient_id))

    _send_as_patient(client, csrf, patient_id, "my reading is 172/104")
    result = _send_as_patient(client, csrf, patient_id, "checked again, 124/80")

    assert not result["escalation_created"]
    patient = next(p for p in client.get("/api/patients").json() if p["id"] == patient_id)
    assert patient["risk_level"] == "red"


def test_elevated_bp_opens_a_case_only_when_it_repeats(staff):
    client, csrf = staff["client"], staff["csrf"]
    patient_id = client.get("/api/patients").json()[-1]["id"]
    asyncio.run(_reset_flow(patient_id))
    asyncio.run(_clear_bp_history(patient_id))

    first = _send_as_patient(client, csrf, patient_id, "my bp is 139/90")
    assert not first["escalation_created"]
    assert "bottom number (90) is a bit high" in first["reply"]["body"]

    second = _send_as_patient(client, csrf, patient_id, "rested and checked, 142/91")
    assert second["escalation_created"]
    _open_case_for(client, patient_id, lambda a: a["details"].get("reading") == "142/91")


def test_side_effect_repeated_same_day_is_one_report_not_a_missed_dose(staff):
    client, csrf = staff["client"], staff["csrf"]
    patient_id = client.get("/api/patients").json()[-1]["id"]
    asyncio.run(_reset_flow(patient_id))
    asyncio.run(_clear_bp_history(patient_id))
    before = asyncio.run(_adherence_rows(patient_id))

    first = _send_as_patient(client, csrf, patient_id, "my legs are swelling since I started this medicine")
    second = _send_as_patient(client, csrf, patient_id, "the swelling is still there")

    assert first["escalation_created"] and not second["escalation_created"]
    assert asyncio.run(_adherence_rows(patient_id)) == before
    patient = next(p for p in client.get("/api/patients").json() if p["id"] == patient_id)
    assert patient["risk_level"] == "amber"


def test_emergency_reply_names_numbers_and_keeps_the_reading(staff):
    client, csrf = staff["client"], staff["csrf"]
    patient_id = client.get("/api/patients").json()[-1]["id"]

    result = _send_as_patient(client, csrf, patient_id, "190/120 and my lips are swelling")

    body = result["reply"]["body"]
    assert "112" in body and "193" in body
    assert result["escalation_created"]
    readings = asyncio.run(_latest_reading(patient_id))
    assert readings == "190/120"


async def _reset_flow(patient_id: int) -> None:
    async with db.connect() as conn:
        await conn.execute("DELETE FROM conversation_state WHERE patient_id=?", (patient_id,))
        await conn.commit()


async def _clear_bp_history(patient_id: int) -> None:
    async with db.connect() as conn:
        await conn.execute("DELETE FROM checkin_logs WHERE patient_id=?", (patient_id,))
        await conn.execute("UPDATE escalations SET resolved=1 WHERE patient_id=?", (patient_id,))
        await conn.commit()


async def _adherence_rows(patient_id: int) -> int:
    async with db.connect() as conn:
        row = await (await conn.execute(
            "SELECT COUNT(*) FROM adherence_logs WHERE patient_id=?", (patient_id,))).fetchone()
        return row[0]


async def _latest_reading(patient_id: int) -> str:
    async with db.connect() as conn:
        row = await (await conn.execute(
            "SELECT reading_value FROM checkin_logs WHERE patient_id=? ORDER BY id DESC LIMIT 1",
            (patient_id,),
        )).fetchone()
    return row[0] if row else ""


def _webhook_body(message: dict) -> dict:
    return {"entry": [{"changes": [{"value": {"messages": [message]}}]}]}


def _signed_webhook(client: TestClient, message: dict):
    import hashlib
    import hmac
    raw = json.dumps(_webhook_body(message)).encode()
    signature = hmac.new(b"test-app-secret", raw, hashlib.sha256).hexdigest()
    return client.post("/webhook/whatsapp", content=raw, headers={
        "Content-Type": "application/json", "X-Hub-Signature-256": f"sha256={signature}",
    })


async def _inbound_event(message_id: str) -> tuple:
    async with db.connect() as conn:
        return await (await conn.execute(
            "SELECT status, attempts FROM inbound_events WHERE external_message_id=?", (message_id,),
        )).fetchone()


def test_webhook_queues_then_processes_after_responding(staff, monkeypatch):
    client = staff["client"]
    patient = client.get("/api/patients").json()[0]
    sent: list[str] = []

    async def fake_send_text(to: str, body: str) -> bool:
        sent.append(body)
        return True

    monkeypatch.setattr(whatsapp, "send_text", fake_send_text)
    message = {"id": "wamid.queue-test", "from": whatsapp.normalize_phone(patient["phone"]),
               "type": "text", "text": {"body": "my reading is 128/82"}}

    monkeypatch.setenv("META_APP_SECRET", "test-app-secret")
    response = _signed_webhook(client, message)
    assert response.status_code == 200
    assert response.json()["queued"] == 1
    # TestClient runs background tasks before returning, as the server does
    # after sending the response.
    assert asyncio.run(_inbound_event("wamid.queue-test")) == ("processed", 1)
    assert any("128/82" in body for body in sent), sent

    retry = _signed_webhook(client, message)
    assert retry.json()["duplicates"] == 1


def test_sweep_never_reprocesses_a_half_finished_message(staff, monkeypatch):
    client = staff["client"]
    patient = client.get("/api/patients").json()[0]
    sent: list[str] = []

    async def fake_send_text(to: str, body: str) -> bool:
        sent.append(body)
        return True

    monkeypatch.setattr(whatsapp, "send_text", fake_send_text)
    message_id = "wamid.killed-mid-run"
    message = {"id": message_id, "from": whatsapp.normalize_phone(patient["phone"]),
               "type": "text", "text": {"body": "I could not afford my pills"}}

    async def simulate_killed_run():
        long_ago = "2000-01-01T00:00:00"
        async with db.connect() as conn:
            await conn.execute(
                """INSERT INTO inbound_events
                   (external_message_id, status, received_at, payload, attempts, started_at)
                   VALUES (?, 'processing', ?, ?, 1, ?)""",
                (message_id, long_ago, json.dumps(message), long_ago),
            )
            await conn.execute(
                """INSERT INTO messages (patient_id, direction, body, created_at, channel, external_message_id)
                   VALUES (?, 'inbound', ?, ?, 'whatsapp', ?)""",
                (patient["id"], "I could not afford my pills", long_ago, message_id),
            )
            await conn.commit()

    asyncio.run(simulate_killed_run())
    sweep = client.get("/api/cron/inbound", headers={"Authorization": "Bearer test-cron-secret"})

    assert sweep.status_code == 200
    assert "abandoned" in sweep.json()["results"]
    assert asyncio.run(_inbound_event(message_id))[0] == "failed"
    assert len(sent) == 1 and "112" in sent[0]
    _open_case_for(client, patient["id"], lambda a: a["details"].get("reason") == "processing_failed")


def test_inbound_sweep_requires_cron_secret(client: TestClient):
    assert client.get("/api/cron/inbound").status_code == 401
