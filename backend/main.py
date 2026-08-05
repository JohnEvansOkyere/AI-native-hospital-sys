import os
import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal, Optional

import db as db_store
from dotenv import load_dotenv
from fastapi import (FastAPI, WebSocket, WebSocketDisconnect, HTTPException,
                     UploadFile, File, Form, Query, Request)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from db import init_db, get_db, DB_PATH, Connection
from services.bot import process_message, trigger_care_reminder, trigger_checkin
from services.ai import generate_weekly_report, display_first_name
from services import stt, whatsapp

load_dotenv()

# Serverless bundles are read-only apart from /tmp, and creating this at import
# time would take the whole app down on boot. Resolve the location eagerly but
# create the directory lazily, at the point something actually stores audio.
#
# On /tmp the files are per-instance and vanish on cold start: a voice note can
# be transcribed and answered, but playing it back later may 404. The transcript
# and its provenance live in the database, which is what the clinical record
# actually depends on.
VOICE_DIR = Path(os.getenv("VOICE_DIR") or
                 ("/tmp/voice_notes" if os.getenv("VERCEL") else Path(__file__).parent / "voice_notes"))


def ensure_voice_dir() -> Path:
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    return VOICE_DIR


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

# Set when startup schema/seed fails, and surfaced by /health. Kept as a string
# rather than re-raising because a database that can't be reached must not take
# the whole service down with it.
DB_ERROR: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Prepare the database, but never let a bad one prevent the app booting.

    An exception here kills the ASGI startup, so on a serverless host *every*
    route then fails with an opaque platform error — including /health, the one
    endpoint you need in order to diagnose it. Misconfigured storage is exactly
    the case where the service must stay up and say so.
    """
    global DB_ERROR
    try:
        await init_db()
        DB_ERROR = None
    except Exception as e:
        DB_ERROR = f"{type(e).__name__}: {e}"
        logging.getLogger(__name__).error(
            "Database init failed — service is up but has no data. "
            "Check TURSO_DATABASE_URL / TURSO_AUTH_TOKEN. %s", DB_ERROR
        )
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

async def compute_adherence(patient_id: int, db: Connection, days: int = 14) -> int:
    cursor = await db.execute(
        f"SELECT response FROM adherence_logs WHERE patient_id=? AND log_date > date('now', '-{days} days')",
        (patient_id,)
    )
    rows = await cursor.fetchall()
    if not rows:
        return 0
    yes_count = sum(1 for r in rows if r[0] == "yes")
    return round(yes_count / len(rows) * 100)


async def compute_care_completion(patient_id: int, db: Connection, days: int = 14) -> int:
    cursor = await db.execute(
        f"SELECT response FROM care_logs WHERE patient_id=? AND log_date > date('now', '-{days} days')",
        (patient_id,),
    )
    rows = await cursor.fetchall()
    if not rows:
        return 0
    done_count = sum(1 for r in rows if r[0] == "done")
    return round(done_count / len(rows) * 100)


async def get_patient_full(patient_id: int, db: Connection) -> dict:
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

    # Keep the last handled cases beside the live record. This is the outcome
    # side of the signal -> action -> outcome loop and gives staff an audit
    # trail without mixing resolved work back into the urgent queue.
    cursor = await db.execute(
        """SELECT id, reason, risk_level, details, created_at, resolution_code,
                  resolution_note, resolved_by, resolved_at
           FROM escalations
           WHERE patient_id=? AND resolved=1
           ORDER BY resolved_at DESC LIMIT 5""",
        (patient_id,),
    )
    resolved_escalations = await cursor.fetchall()
    patient["recent_resolutions"] = [
        {
            "id": e[0], "reason": e[1], "risk_level": e[2],
            "details": json.loads(e[3]), "created_at": e[4],
            "resolution_code": e[5], "resolution_note": e[6],
            "resolved_by": e[7], "resolved_at": e[8],
        }
        for e in resolved_escalations
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
    async with db_store.connect() as db:
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
    async with db_store.connect() as db:
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
    async with db_store.connect() as db:
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
    async with db_store.connect() as db:
        cursor = await db.execute(
            "SELECT id, direction, body, reason, created_at, channel, audio_file, stt_provider, stt_language, stt_latency_ms "
            "FROM messages WHERE patient_id=? ORDER BY created_at DESC LIMIT ?",
            (patient_id, limit)
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r[0], "direction": r[1], "body": r[2], "reason": r[3], "created_at": r[4],
                "channel": r[5] or "simulator",
                "audio_file": r[6] or None, "stt_provider": r[7] or None,
                "stt_language": r[8] or None, "stt_latency_ms": r[9] or None,
            }
            for r in reversed(rows)
        ]


class InboundMessage(BaseModel):
    message: str


class OutreachRequest(BaseModel):
    message: str


ResolutionCode = Literal[
    "patient_contacted",
    "appointment_booked",
    "nhis_alternative_arranged",
    "refill_arranged",
    "clinician_reviewed",
    "other",
]


class ResolveAlertRequest(BaseModel):
    resolution_code: ResolutionCode
    note: str = ""
    resolved_by: str = "Care team"


async def ingest_patient_message(patient_id: int, text: str, voice: dict | None = None,
                                 channel: str = "simulator"):
    """Run one inbound patient turn: log it, let the bot act, broadcast everything.

    Every transport lands here — the simulator, WhatsApp, and anything added
    later. Text and voice both take the exact same path through
    process_message(), including escalation. That equivalence is what lets the
    benchmark's escalation-accuracy metric describe the real product rather than
    a parallel test harness, and it's why new channels must never get their own
    copy of this logic.
    """
    now = datetime.now().isoformat()
    voice = voice or {}

    async with db_store.connect() as db:
        # Log inbound
        cursor = await db.execute(
            "INSERT INTO messages (patient_id, direction, body, created_at, channel, audio_file, stt_provider, stt_language, stt_latency_ms) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (patient_id, "inbound", text, now, channel, voice.get("audio_file", ""),
             voice.get("stt_provider", ""), voice.get("stt_language", ""),
             voice.get("stt_latency_ms", 0))
        )
        inbound_id = cursor.lastrowid
        await db.commit()

        inbound_msg = {
            "id": inbound_id, "direction": "inbound", "body": text, "reason": None, "created_at": now,
            "channel": channel,
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
            "INSERT INTO messages (patient_id, direction, body, reason, created_at, channel) VALUES (?,?,?,?,?,?)",
            (patient_id, "outbound", bot_reply, reason, bot_now, channel)
        )
        outbound_id = cursor.lastrowid
        await db.commit()

        outbound_msg = {
            "id": outbound_id, "direction": "outbound", "body": bot_reply,
            "reason": reason, "created_at": bot_now, "channel": channel,
            "audio_file": None, "stt_provider": None, "stt_language": None, "stt_latency_ms": None,
        }
        await manager.broadcast(patient_id, {"type": "message", "message": outbound_msg})

        # Push updated patient stats
        p = await get_patient_full(patient_id, db)

        # Reply over the transport the patient actually used. The dashboard sees
        # the message either way via the broadcast above.
        if channel == "whatsapp":
            await whatsapp.send_text(p["phone"], bot_reply)
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
    async with db_store.connect() as db:
        cursor = await db.execute("SELECT id FROM patients WHERE id=?", (patient_id,))
        if await cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Patient not found")

    suffix = Path(audio.filename or "").suffix.lower() or ".webm"
    if suffix not in ALLOWED_AUDIO_SUFFIXES:
        raise HTTPException(status_code=400, detail=f"Unsupported audio format '{suffix}'")

    # Store under a generated name — never the client-supplied filename, and
    # never anything patient-identifying (consent/de-identification promise).
    stored_name = f"p{patient_id}_{uuid.uuid4().hex[:12]}{suffix}"
    dest = ensure_voice_dir() / stored_name
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


# ── Routes: WhatsApp Cloud API ────────────────────────────────────────────────
#
# The real transport. Same agent logic as the simulator — these handlers resolve
# the sender to a patient, turn voice notes into text, and hand off to
# ingest_patient_message(). No conversation logic lives here.

# Meta retries deliveries aggressively; without this a patient gets two replies
# to one message. Bounded so a long-running process can't grow without limit.
_seen_wa_messages: dict[str, float] = {}
_SEEN_LIMIT = 2000


def _already_handled(message_id: str) -> bool:
    if not message_id:
        return False
    if message_id in _seen_wa_messages:
        return True
    if len(_seen_wa_messages) >= _SEEN_LIMIT:
        oldest = sorted(_seen_wa_messages, key=_seen_wa_messages.get)[:_SEEN_LIMIT // 2]
        for k in oldest:
            _seen_wa_messages.pop(k, None)
    _seen_wa_messages[message_id] = datetime.now().timestamp()
    return False


async def _patient_by_phone(phone: str) -> Optional[dict]:
    """Resolve an inbound WhatsApp number to an enrolled patient.

    Compared digits-only: Meta sends E.164 without '+', patients are stored with
    it. Falls back to a suffix match so a number stored without its country code
    still resolves.
    """
    target = whatsapp.normalize_phone(phone)
    async with db_store.connect() as db:
        cursor = await db.execute("SELECT id, name, phone FROM patients")
        rows = await cursor.fetchall()
    for pid, name, stored in rows:
        digits = whatsapp.normalize_phone(stored or "")
        if not digits:
            continue
        if digits == target or digits.endswith(target[-9:]) or target.endswith(digits[-9:]):
            return {"id": pid, "name": name, "phone": stored}
    return None


@app.get("/webhook/whatsapp")
async def whatsapp_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """Meta's one-time verification handshake when you save the webhook URL."""
    try:
        return PlainTextResponse(str(whatsapp.verify_challenge(
            hub_mode, hub_verify_token, hub_challenge)))
    except ValueError:
        raise HTTPException(status_code=403, detail="Verification token mismatch")


@app.post("/webhook/whatsapp")
async def whatsapp_receive(request: Request):
    """Inbound WhatsApp message — text or voice note.

    Always returns 200 once the signature checks out. Meta retries anything else,
    and a retry storm on a parse error is worse than dropping one message.
    """
    raw = await request.body()
    if not whatsapp.verify_signature(raw, request.headers.get("x-hub-signature-256")):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

    try:
        body = json.loads(raw)
        value = body["entry"][0]["changes"][0]["value"]
    except Exception:
        return {"status": "ignored"}

    if "messages" not in value:
        return {"status": "no_message"}       # delivery receipts, read status, etc.

    message = value["messages"][0]
    message_id = message.get("id", "")
    sender = message.get("from", "")
    msg_type = message.get("type", "")

    if _already_handled(message_id):
        return {"status": "duplicate_ignored"}

    patient = await _patient_by_phone(sender)
    if patient is None:
        # Unknown number: answer helpfully, never silently. Do not auto-enrol —
        # enrolment is a consented clinical act, not a side effect of texting.
        await whatsapp.send_text(
            sender,
            "Hello! This number isn't registered with the clinic yet. "
            "Please contact your care team to be enrolled.",
        )
        return {"status": "unknown_sender"}

    if msg_type == "text":
        text = (message.get("text", {}).get("body") or "").strip()
        if not text:
            return {"status": "empty"}
        await ingest_patient_message(patient["id"], text, channel="whatsapp")
        return {"status": "ok"}

    if msg_type in ("audio", "voice"):
        media_id = message.get(msg_type, {}).get("id")
        stored = await whatsapp.download_media(
            media_id, ensure_voice_dir(), f"p{patient['id']}_{uuid.uuid4().hex[:12]}"
        ) if media_id else None

        if stored is None:
            await whatsapp.send_text(
                sender, "Sorry, I couldn't download that voice note. Please try again."
            )
            return {"status": "media_failed"}

        # Language hint: WhatsApp gives us none, so use the deployment default.
        # Sahara's Ghanaian codes are what make this worth configuring.
        language = os.getenv("WHATSAPP_STT_LANGUAGE", "en")
        result = await stt.transcribe(str(stored), language=language)

        if not result.ok:
            await whatsapp.send_text(
                sender,
                "Sorry, I couldn't hear that clearly. Please send it again, or type your message.",
            )
            return {"status": "stt_failed", "error": result.error}

        await ingest_patient_message(
            patient["id"], result.text,
            voice={
                "audio_file": stored.name,
                "stt_provider": result.provider,
                "stt_language": language,
                "stt_latency_ms": result.latency_ms,
            },
            channel="whatsapp",
        )
        return {"status": "ok"}

    await whatsapp.send_text(
        sender,
        "I can read text and listen to voice notes. Please send one of those.",
    )
    return {"status": "unsupported_type"}


@app.get("/api/voice/{filename}")
async def get_voice_note(filename: str):
    """Serve a stored voice note back for replay in the chat pane."""
    # Resolve and confine to VOICE_DIR — filename comes off the wire.
    path = (VOICE_DIR / filename).resolve()
    if path.parent != VOICE_DIR.resolve() or not path.is_file():
        raise HTTPException(status_code=404, detail="Voice note not found")
    return FileResponse(path)


# ── Routes: actions ───────────────────────────────────────────────────────────

async def send_care_team_message(patient_id: int, body: str, db: Connection) -> dict:
    """Deliver one approved care-team message and record the actual channel.

    With Meta configured this is a real WhatsApp send. Without it, the message
    is still written to the simulator conversation so the full workflow remains
    demo-able and never hard-fails because a key or network is missing.
    """
    body = body.strip()
    if not body:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    if len(body) > 1000:
        raise HTTPException(status_code=400, detail="Message must be 1000 characters or fewer")

    cursor = await db.execute("SELECT name, phone FROM patients WHERE id=?", (patient_id,))
    patient = await cursor.fetchone()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    delivered = False
    channel = "simulator"
    if whatsapp.is_configured():
        delivered = await whatsapp.send_text(patient[1], body)
        if delivered:
            channel = "whatsapp"

    now = datetime.now().isoformat()
    cursor = await db.execute(
        "INSERT INTO messages (patient_id, direction, body, created_at, channel) VALUES (?,?,?,?,?)",
        (patient_id, "outbound", body, now, channel),
    )
    await db.commit()
    message = {
        "id": cursor.lastrowid,
        "direction": "outbound",
        "body": body,
        "reason": None,
        "created_at": now,
        "channel": channel,
        "audio_file": None,
        "stt_provider": None,
        "stt_language": None,
        "stt_latency_ms": None,
    }
    event = {"type": "message", "message": message, "patient_id": patient_id}
    await manager.broadcast(patient_id, event)
    await manager.broadcast_all(event)
    return {
        "message": message,
        "delivered": delivered,
        "channel": channel,
        "delivery_note": (
            "Sent on WhatsApp" if delivered
            else "Saved to the demo conversation; WhatsApp delivery is not configured"
        ),
    }


@app.post("/api/patients/{patient_id}/outreach")
async def send_outreach(patient_id: int, body: OutreachRequest):
    """Send a human-authored care-team message to a patient."""
    async with db_store.connect() as db:
        return await send_care_team_message(patient_id, body.message, db)

@app.post("/api/patients/{patient_id}/remind")
async def send_reminder(patient_id: int):
    """Send the category-specific care reminder."""
    async with db_store.connect() as db:
        reminder = await trigger_care_reminder(patient_id, db)
        if not reminder:
            raise HTTPException(status_code=404, detail="Patient not found")
        return await send_care_team_message(patient_id, reminder, db)


@app.post("/api/patients/{patient_id}/checkin")
async def send_checkin(patient_id: int):
    """Send the category-specific check-in prompt."""
    async with db_store.connect() as db:
        prompt = await trigger_checkin(patient_id, db)
        if not prompt:
            raise HTTPException(status_code=404, detail="Patient not found")
        return await send_care_team_message(patient_id, prompt, db)


# ── Routes: alerts ────────────────────────────────────────────────────────────

@app.get("/api/alerts")
async def get_alerts():
    async with db_store.connect() as db:
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
async def resolve_alert(alert_id: int, body: ResolveAlertRequest):
    async with db_store.connect() as db:
        cursor = await db.execute(
            "SELECT patient_id FROM escalations WHERE id=? AND resolved=0",
            (alert_id,),
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Open alert not found")
        patient_id = row[0]

        note = body.note.strip()
        resolved_by = body.resolved_by.strip() or "Care team"
        if len(note) > 1000:
            raise HTTPException(status_code=400, detail="Resolution note must be 1000 characters or fewer")
        if len(resolved_by) > 100:
            raise HTTPException(status_code=400, detail="Resolved by must be 100 characters or fewer")

        resolved_at = datetime.now().isoformat()
        await db.execute(
            """UPDATE escalations
               SET resolved=1, resolution_code=?, resolution_note=?, resolved_by=?, resolved_at=?
               WHERE id=?""",
            (body.resolution_code, note, resolved_by, resolved_at, alert_id),
        )

        # Risk is active operational state, not a permanent label. Recalculate
        # it deterministically from the patient's remaining open alerts.
        cursor = await db.execute(
            """SELECT risk_level FROM escalations
               WHERE patient_id=? AND resolved=0
               ORDER BY CASE risk_level WHEN 'red' THEN 0 ELSE 1 END LIMIT 1""",
            (patient_id,),
        )
        remaining = await cursor.fetchone()
        risk_level = remaining[0] if remaining else "green"
        await db.execute("UPDATE patients SET risk_level=? WHERE id=?", (risk_level, patient_id))
        await db.commit()
        patient = await get_patient_full(patient_id, db)
        await manager.broadcast_all({
            "type": "alert_resolved",
            "alert_id": alert_id,
            "patient_id": patient_id,
            "patient": patient,
        })
        return {
            "resolved": True,
            "alert_id": alert_id,
            "patient_id": patient_id,
            "risk_level": risk_level,
            "resolved_at": resolved_at,
        }


# ── Routes: reports ───────────────────────────────────────────────────────────

@app.get("/api/reports/weekly")
async def weekly_report():
    async with db_store.connect() as db:
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


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Liveness check that also reports what's actually wired up — the fastest
    way to tell whether a tunnel reaches this process and whether WhatsApp and
    speech are configured, without sending a real message."""
    return {
        "status": "degraded" if DB_ERROR else "ok",
        "service": "VeloxaCare API",
        "whatsapp_configured": whatsapp.is_configured(),
        "stt_providers": stt.configured_providers(),
        "webhook": "/webhook/whatsapp",
        # Which store is in use, and why it isn't working if it isn't. Without
        # this a storage misconfiguration is invisible until a query fails.
        "database": "turso" if db_store.turso_configured() else f"sqlite:{DB_PATH}",
        "database_error": DB_ERROR,
    }


# ── Serve frontend ────────────────────────────────────────────────────────────

# Mounted last: StaticFiles at "/" swallows every unmatched path, so it must not
# shadow the API routes above. Only present after `npm run build`; in dev the
# dashboard is served by Vite on :5173 instead.
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")
