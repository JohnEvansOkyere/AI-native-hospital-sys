import os
import json
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal, Optional

import aiosqlite
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from db import init_db, get_db, DB_PATH
from services.bot import process_message, trigger_care_reminder, trigger_checkin
from services.ai import generate_weekly_report, display_first_name
from services import stt

VOICE_DIR = Path(__file__).parent / "voice_notes"
VOICE_DIR.mkdir(exist_ok=True)

load_dotenv()


# ── WebSocket connection manager ──────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: dict[int, list[WebSocket]] = {}

    async def connect(self, patient_id: int, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(patient_id, []).append(ws)

    def disconnect(self, patient_id: int, ws: WebSocket):
        if patient_id in self.active:
            self.active[patient_id] = [w for w in self.active[patient_id] if w != ws]

    async def broadcast(self, patient_id: int, data: dict):
        for ws in self.active.get(patient_id, []):
            try:
                await ws.send_json(data)
            except Exception:
                pass

    # broadcast to all connected clients (for alerts dashboard)
    async def broadcast_all(self, data: dict):
        for connections in self.active.values():
            for ws in connections:
                try:
                    await ws.send_json(data)
                except Exception:
                    pass


manager = ConnectionManager()


# ── App lifespan ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="VeloxaCare API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def compute_adherence(patient_id: int, db: aiosqlite.Connection, days: int = 14) -> int:
    cursor = await db.execute(
        f"SELECT response FROM adherence_logs WHERE patient_id=? AND log_date > date('now', '-{days} days')",
        (patient_id,)
    )
    rows = await cursor.fetchall()
    if not rows:
        return 0
    yes_count = sum(1 for r in rows if r[0] == "yes")
    return round(yes_count / len(rows) * 100)


async def compute_care_completion(patient_id: int, db: aiosqlite.Connection, days: int = 14) -> int:
    cursor = await db.execute(
        f"SELECT response FROM care_logs WHERE patient_id=? AND log_date > date('now', '-{days} days')",
        (patient_id,),
    )
    rows = await cursor.fetchall()
    if not rows:
        return 0
    done_count = sum(1 for r in rows if r[0] == "done")
    return round(done_count / len(rows) * 100)


async def get_patient_full(patient_id: int, db: aiosqlite.Connection) -> dict:
    cursor = await db.execute("SELECT * FROM patients WHERE id=?", (patient_id,))
    p = await cursor.fetchone()
    if not p:
        return None
    cols = [d[0] for d in cursor.description]
    patient = dict(zip(cols, p))

    category = patient.get("category") or "chronic"
    adherence_pct = await compute_adherence(patient_id, db)
    care_completion_pct = await compute_care_completion(patient_id, db)
    patient["care_completion_pct"] = care_completion_pct if category != "chronic" else adherence_pct
    # Keep the old field for existing clients while the UI migrates to the
    # category-neutral care_completion_pct field.
    patient["adherence_pct"] = patient["care_completion_pct"]

    # Adherence last 14 days
    cursor = await db.execute(
        "SELECT log_date, response FROM adherence_logs WHERE patient_id=? ORDER BY log_date DESC LIMIT 14",
        (patient_id,)
    )
    logs = await cursor.fetchall()
    patient["adherence_logs"] = [{"date": r[0], "response": r[1]} for r in logs]

    cursor = await db.execute(
        "SELECT log_date, activity, response, details FROM care_logs WHERE patient_id=? ORDER BY log_date DESC, id DESC LIMIT 14",
        (patient_id,),
    )
    care_logs = await cursor.fetchall()
    patient["care_logs"] = [
        {"date": r[0], "activity": r[1], "response": r[2], "details": r[3]}
        for r in care_logs
    ]

    # Active escalations
    cursor = await db.execute(
        "SELECT id, reason, risk_level, details, created_at FROM escalations WHERE patient_id=? AND resolved=0",
        (patient_id,)
    )
    escs = await cursor.fetchall()
    patient["escalations"] = [
        {"id": e[0], "reason": e[1], "risk_level": e[2], "details": json.loads(e[3]), "created_at": e[4]}
        for e in escs
    ]

    # Last checkin
    cursor = await db.execute(
        "SELECT reading_type, reading_value, risk_level, created_at FROM checkin_logs WHERE patient_id=? ORDER BY created_at DESC LIMIT 1",
        (patient_id,)
    )
    chk = await cursor.fetchone()
    patient["last_checkin"] = {"type": chk[0], "value": chk[1], "risk": chk[2], "at": chk[3]} if chk else None

    # Streak
    cursor = await db.execute(
        "SELECT response FROM adherence_logs WHERE patient_id=? ORDER BY log_date DESC LIMIT 14",
        (patient_id,)
    )
    streak_rows = await cursor.fetchall()
    streak = 0
    for r in streak_rows:
        if r[0] == "yes":
            streak += 1
        else:
            break
    patient["streak"] = streak

    # Conversation state
    cursor = await db.execute("SELECT current_flow FROM conversation_state WHERE patient_id=?", (patient_id,))
    cs = await cursor.fetchone()
    patient["current_flow"] = cs[0] if cs else "idle"

    return patient


# ── Routes: patients ──────────────────────────────────────────────────────────

@app.get("/api/patients")
async def list_patients():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id FROM patients WHERE status='active' ORDER BY risk_level ASC, name ASC")
        rows = await cursor.fetchall()
        result = []
        for (pid,) in rows:
            p = await get_patient_full(pid, db)
            if p:
                result.append(p)
        return result


@app.get("/api/patients/{patient_id}")
async def get_patient(patient_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        p = await get_patient_full(patient_id, db)
        if not p:
            raise HTTPException(404, "Patient not found")
        return p


class EnrollRequest(BaseModel):
    name: str
    phone: str
    age: Optional[int] = None
    category: Literal["dental", "eye", "chronic", "general"] = "general"
    condition: str = ""
    drug_name: str = ""
    drug_dosage: str = ""
    service_type: str = ""
    care_instructions: str = ""
    next_follow_up: str = ""
    recall_date: str = ""
    doctor_name: str = "Dr. Mensah"


@app.post("/api/patients")
async def enroll_patient(body: EnrollRequest):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            category_defaults = {
                "dental": ("Dental care", "Dental follow-up", "Follow the aftercare instructions from your dental team."),
                "eye": ("Eye care", "Eye follow-up", "Follow the care instructions from your eye-care team."),
                "chronic": (body.condition or "Hypertension", "Chronic-care follow-up", ""),
                "general": (body.condition or "General care", "Clinic follow-up", ""),
            }
            default_condition, default_service, default_instructions = category_defaults[body.category]
            condition = body.condition or default_condition
            service_type = body.service_type or default_service
            care_instructions = body.care_instructions or default_instructions
            cursor = await db.execute(
                """INSERT INTO patients (name, phone, age, condition, drug_name, drug_dosage,
                   category, service_type, care_instructions, next_follow_up, recall_date,
                   enrolled_at, doctor_name, risk_level)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'green')""",
                (body.name, body.phone, body.age, condition, body.drug_name or "", body.drug_dosage or "",
                 body.category, service_type, care_instructions, body.next_follow_up, body.recall_date,
                 date.today().isoformat(), body.doctor_name)
            )
            pid = cursor.lastrowid
            await db.execute(
                "INSERT INTO conversation_state (patient_id, current_flow, context) VALUES (?, 'idle', '{}')",
                (pid,)
            )
            await db.commit()

            # Welcome message
            first = display_first_name(body.name)
            if body.category == "dental":
                welcome = (
                    f"Welcome to VeloxaCare, {first}! 👋 I’ll check on your {service_type.lower()} recovery, "
                    "help with your approved aftercare, and remind you when it is time to return. Reply START to begin."
                )
            elif body.category == "eye":
                welcome = (
                    f"Welcome to VeloxaCare, {first}! 👋 I’ll check on your eye-care follow-up and remind you about your next visit. Reply START to begin."
                )
            else:
                welcome = (
                    f"Welcome to VeloxaCare, {first}! 👋 I’ll help you stay on track with your care and follow-up. Reply START to begin."
                )
            now = datetime.now().isoformat()
            await db.execute(
                "INSERT INTO messages (patient_id, direction, body, created_at) VALUES (?,?,?,?)",
                (pid, "outbound", welcome, now)
            )
            await db.commit()

            p = await get_patient_full(pid, db)
            await manager.broadcast_all({"type": "patient_enrolled", "patient": p})
            return p
        except Exception as e:
            if "UNIQUE" in str(e):
                raise HTTPException(400, "Phone number already registered")
            raise HTTPException(500, str(e))


# ── Routes: messages ──────────────────────────────────────────────────────────

@app.get("/api/patients/{patient_id}/messages")
async def get_messages(patient_id: int, limit: int = 50):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, direction, body, reason, created_at, audio_file, stt_provider, stt_language, stt_latency_ms "
            "FROM messages WHERE patient_id=? ORDER BY created_at DESC LIMIT ?",
            (patient_id, limit)
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r[0], "direction": r[1], "body": r[2], "reason": r[3], "created_at": r[4],
                "audio_file": r[5] or None, "stt_provider": r[6] or None,
                "stt_language": r[7] or None, "stt_latency_ms": r[8] or None,
            }
            for r in reversed(rows)
        ]


class InboundMessage(BaseModel):
    message: str


async def ingest_patient_message(patient_id: int, text: str, voice: dict | None = None):
    """Run one inbound patient turn: log it, let the bot act, broadcast everything.

    Text messages and voice notes both land here, so a transcribed voice note
    takes the exact same path through process_message() — including escalation.
    That equivalence is what lets the benchmark's escalation-accuracy metric
    describe the real product rather than a parallel test harness.
    """
    now = datetime.now().isoformat()
    voice = voice or {}

    async with aiosqlite.connect(DB_PATH) as db:
        # Log inbound
        cursor = await db.execute(
            "INSERT INTO messages (patient_id, direction, body, created_at, audio_file, stt_provider, stt_language, stt_latency_ms) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (patient_id, "inbound", text, now, voice.get("audio_file", ""),
             voice.get("stt_provider", ""), voice.get("stt_language", ""),
             voice.get("stt_latency_ms", 0))
        )
        inbound_id = cursor.lastrowid
        await db.commit()

        inbound_msg = {
            "id": inbound_id, "direction": "inbound", "body": text, "reason": None, "created_at": now,
            "audio_file": voice.get("audio_file") or None,
            "stt_provider": voice.get("stt_provider") or None,
            "stt_language": voice.get("stt_language") or None,
            "stt_latency_ms": voice.get("stt_latency_ms") or None,
        }
        await manager.broadcast(patient_id, {"type": "message", "message": inbound_msg})

        # Process and get bot reply
        bot_reply, reason, escalation_created = await process_message(patient_id, text, db)

        # Log outbound
        bot_now = datetime.now().isoformat()
        cursor = await db.execute(
            "INSERT INTO messages (patient_id, direction, body, reason, created_at) VALUES (?,?,?,?,?)",
            (patient_id, "outbound", bot_reply, reason, bot_now)
        )
        outbound_id = cursor.lastrowid
        await db.commit()

        outbound_msg = {
            "id": outbound_id, "direction": "outbound", "body": bot_reply,
            "reason": reason, "created_at": bot_now,
            "audio_file": None, "stt_provider": None, "stt_language": None, "stt_latency_ms": None,
        }
        await manager.broadcast(patient_id, {"type": "message", "message": outbound_msg})

        # Push updated patient stats
        p = await get_patient_full(patient_id, db)
        await manager.broadcast(patient_id, {"type": "patient_updated", "patient": p})
        await manager.broadcast_all({"type": "patient_updated", "patient": p})

        if escalation_created:
            cursor = await db.execute(
                "SELECT id, reason, risk_level, details, created_at FROM escalations WHERE patient_id=? ORDER BY id DESC LIMIT 1",
                (patient_id,)
            )
            esc = await cursor.fetchone()
            if esc:
                esc_data = {"id": esc[0], "reason": esc[1], "risk_level": esc[2], "details": json.loads(esc[3]), "created_at": esc[4], "patient_id": patient_id, "patient_name": p["name"]}
                await manager.broadcast_all({"type": "escalation", "escalation": esc_data})

        return {"inbound": inbound_msg, "reply": outbound_msg, "escalation_created": escalation_created}


@app.post("/api/patients/{patient_id}/messages")
async def send_patient_message(patient_id: int, body: InboundMessage):
    """Simulate patient sending a WhatsApp text message."""
    return await ingest_patient_message(patient_id, body.message)


# ── Routes: voice ─────────────────────────────────────────────────────────────

ALLOWED_AUDIO_SUFFIXES = {".webm", ".ogg", ".oga", ".m4a", ".mp3", ".mp4", ".wav", ".flac"}


@app.get("/api/stt/status")
async def stt_status():
    """Which speech models are live right now — the UI shows this so a demo
    never silently falls back to a different model than the operator expects."""
    configured = stt.configured_providers()
    pinned = os.getenv("STT_PROVIDER") or None
    # Skip providers that have actually failed — reporting a model as active when
    # every request to it falls through to another one is worse than silence.
    healthy = [n for n in configured if n not in stt._degraded]
    active = pinned if pinned in healthy else next(
        (n for n in stt.DEFAULT_ORDER if n in healthy), None
    )
    return {
        "configured": configured,
        "pinned": pinned,
        "active": active,
        "degraded": stt._degraded,
        "languages": stt.LANGUAGE_LABELS,
    }


@app.post("/api/patients/{patient_id}/voice")
async def send_patient_voice_note(
    patient_id: int,
    audio: UploadFile = File(...),
    language: str = Form("en"),
    provider: Optional[str] = Form(None),
):
    """Patient sends a WhatsApp voice note: transcribe it, then run the exact
    same agent turn a typed message would produce.

    `language` is a benchmark language_pair ("en" | "tw-en" | "pcm-en") and is a
    hint only — the transcript is whatever the model actually heard, code-switching
    included. `provider` pins a specific model, which is how we demo the same
    utterance through Sahara vs Whisper side by side.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id FROM patients WHERE id=?", (patient_id,))
        if await cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Patient not found")

    suffix = Path(audio.filename or "").suffix.lower() or ".webm"
    if suffix not in ALLOWED_AUDIO_SUFFIXES:
        raise HTTPException(status_code=400, detail=f"Unsupported audio format '{suffix}'")

    # Store under a generated name — never the client-supplied filename, and
    # never anything patient-identifying (consent/de-identification promise).
    stored_name = f"p{patient_id}_{uuid.uuid4().hex[:12]}{suffix}"
    dest = VOICE_DIR / stored_name
    dest.write_bytes(await audio.read())

    result = await stt.transcribe(str(dest), language=language, provider=provider)

    if not result.ok:
        # Graceful degradation: the patient gets a human answer, the operator
        # gets the real reason, and nothing 500s mid-demo.
        return {
            "inbound": None,
            "reply": {
                "id": -1, "direction": "outbound",
                "body": "Sorry, I couldn't hear that clearly. Please send it again, or type your message.",
                "reason": None, "created_at": datetime.now().isoformat(),
                "audio_file": None, "stt_provider": None, "stt_language": None, "stt_latency_ms": None,
            },
            "escalation_created": False,
            "transcription": {
                "text": "", "provider": result.provider, "language": language,
                "latency_ms": result.latency_ms, "error": result.error,
            },
        }

    payload = await ingest_patient_message(
        patient_id, result.text,
        voice={
            "audio_file": stored_name,
            "stt_provider": result.provider,
            "stt_language": language,
            "stt_latency_ms": result.latency_ms,
        },
    )
    payload["transcription"] = {
        "text": result.text, "provider": result.provider, "language": language,
        "latency_ms": result.latency_ms, "error": "",
    }
    return payload


@app.get("/api/voice/{filename}")
async def get_voice_note(filename: str):
    """Serve a stored voice note back for replay in the chat pane."""
    # Resolve and confine to VOICE_DIR — filename comes off the wire.
    path = (VOICE_DIR / filename).resolve()
    if path.parent != VOICE_DIR.resolve() or not path.is_file():
        raise HTTPException(status_code=404, detail="Voice note not found")
    return FileResponse(path)


# ── Routes: actions ───────────────────────────────────────────────────────────

@app.post("/api/patients/{patient_id}/remind")
async def send_reminder(patient_id: int):
    """Send the category-specific care reminder (demo trigger)."""
    async with aiosqlite.connect(DB_PATH) as db:
        reminder = await trigger_care_reminder(patient_id, db)
        now = datetime.now().isoformat()
        cursor = await db.execute(
            "INSERT INTO messages (patient_id, direction, body, created_at) VALUES (?,?,?,?)",
            (patient_id, "outbound", reminder, now)
        )
        mid = cursor.lastrowid
        await db.commit()
        msg = {"id": mid, "direction": "outbound", "body": reminder, "reason": None, "created_at": now}
        await manager.broadcast(patient_id, {"type": "message", "message": msg})
        return msg


@app.post("/api/patients/{patient_id}/checkin")
async def send_checkin(patient_id: int):
    """Send the category-specific check-in prompt."""
    async with aiosqlite.connect(DB_PATH) as db:
        prompt = await trigger_checkin(patient_id, db)
        now = datetime.now().isoformat()
        cursor = await db.execute(
            "INSERT INTO messages (patient_id, direction, body, created_at) VALUES (?,?,?,?)",
            (patient_id, "outbound", prompt, now)
        )
        mid = cursor.lastrowid
        await db.commit()
        msg = {"id": mid, "direction": "outbound", "body": prompt, "reason": None, "created_at": now}
        await manager.broadcast(patient_id, {"type": "message", "message": msg})
        return msg


# ── Routes: alerts ────────────────────────────────────────────────────────────

@app.get("/api/alerts")
async def get_alerts():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """SELECT e.id, e.patient_id, p.name, e.reason, e.risk_level, e.details, e.created_at
               FROM escalations e JOIN patients p ON e.patient_id=p.id
               WHERE e.resolved=0 ORDER BY e.risk_level ASC, e.created_at DESC""",
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r[0], "patient_id": r[1], "patient_name": r[2],
                "reason": r[3], "risk_level": r[4],
                "details": json.loads(r[5]), "created_at": r[6]
            }
            for r in rows
        ]


@app.post("/api/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE escalations SET resolved=1 WHERE id=?", (alert_id,))
        await db.commit()
        await manager.broadcast_all({"type": "alert_resolved", "alert_id": alert_id})
        return {"resolved": True}


# ── Routes: reports ───────────────────────────────────────────────────────────

@app.get("/api/reports/weekly")
async def weekly_report():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id FROM patients WHERE status='active'")
        rows = await cursor.fetchall()
        patients_data = []
        for (pid,) in rows:
            p = await get_patient_full(pid, db)
            if p:
                flags = []
                for esc in p.get("escalations", []):
                    flags.append(esc["reason"])
                patients_data.append({
                    "name": p["name"],
                    "condition": p["condition"],
                    "drug_name": p["drug_name"],
                    "adherence_pct": p["adherence_pct"],
                    "care_completion_pct": p["care_completion_pct"],
                    "category": p["category"],
                    "service_type": p["service_type"],
                    "risk_level": p["risk_level"],
                    "streak": p["streak"],
                    "last_checkin": p["last_checkin"],
                    "flags": "; ".join(flags) if flags else "None",
                    "doctor": p["doctor_name"],
                })
        report = await generate_weekly_report(patients_data)
        return {"report": report, "generated_at": datetime.now().isoformat()}


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws/{patient_id}")
async def websocket_endpoint(websocket: WebSocket, patient_id: int):
    await manager.connect(patient_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(patient_id, websocket)


@app.websocket("/ws/global")
async def websocket_global(websocket: WebSocket):
    await manager.connect(-1, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(-1, websocket)


# ── Serve frontend ────────────────────────────────────────────────────────────

frontend_dist = os.path.join(os.path.dirname(__file__), "..", "web", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")
