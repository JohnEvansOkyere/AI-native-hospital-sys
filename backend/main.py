import os
import json
import logging
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal, Optional
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi import (FastAPI, WebSocket, WebSocketDisconnect, HTTPException,
                     UploadFile, File, Form, Query, Request)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel

# One canonical local environment file at the repository root. Hosted
# deployments continue to use their injected process environment.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import db as db_store  # noqa: E402
from db import init_db, get_db, DB_PATH, Connection, insert_returning_id  # noqa: E402
from config import (cors_origins, demo_tools_enabled, environment,  # noqa: E402
                    missing_production_config, production_like)
from services.bot import process_message, trigger_care_reminder, trigger_checkin  # noqa: E402
from services.ai import generate_weekly_report, display_first_name  # noqa: E402
from services import appointments, auth, stt, translate, tts, whatsapp  # noqa: E402

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
        async with db_store.connect() as db:
            await auth.ensure_bootstrap_admin(db)
        DB_ERROR = None
    except Exception as e:
        DB_ERROR = f"{type(e).__name__}: {e}"
        logging.getLogger(__name__).error(
            "Database init failed — service is up but has no data. "
            "Check DATABASE_URL and the applied PostgreSQL migrations. %s", DB_ERROR
        )
    yield


app = FastAPI(
    title="VeloxaCare API", lifespan=lifespan,
    docs_url=None if production_like() else "/docs",
    redoc_url=None if production_like() else "/redoc",
    openapi_url=None if production_like() else "/openapi.json",
)

allowed_origins = cors_origins()
if not allowed_origins and not production_like():
    allowed_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


PUBLIC_API_PATHS = {"/api/auth/login", "/api/cron/hourly"}
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
SETUP_WRITE_PATHS = {"/api/auth/logout", "/api/settings/clinic", "/api/patients"}


def setup_write_allowed(path: str) -> bool:
    return path in SETUP_WRITE_PATHS or path == "/api/staff" or path.startswith("/api/staff/")


@app.middleware("http")
async def staff_security(request: Request, call_next):
    """Enforce authentication and CSRF at the server boundary."""
    path = request.url.path
    if not path.startswith("/api/") or path in PUBLIC_API_PATHS:
        return await call_next(request)
    missing_config = missing_production_config()
    if DB_ERROR:
        return JSONResponse({"detail": "Database unavailable", "error": DB_ERROR}, status_code=503)
    # The durable production database is non-negotiable. Other provider setup
    # can be completed from an authenticated workspace: health stays degraded
    # and messaging/clinical actions remain blocked, while admins may configure
    # the clinic and save consent-pending patient records without contacting them.
    if "DATABASE_URL" in missing_config:
        return JSONResponse(
            {"detail": "Production configuration incomplete", "missing": missing_config},
            status_code=503,
        )
    try:
        async with db_store.connect() as db:
            session = await auth.get_session(db, request.cookies.get(auth.COOKIE_NAME, ""))
    except Exception as exc:
        return JSONResponse({"detail": "Authentication store unavailable", "error": str(exc)}, status_code=503)
    if not session:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)
    if request.method not in SAFE_METHODS:
        supplied = request.headers.get("x-csrf-token", "")
        if not supplied or not secrets.compare_digest(supplied, session["csrf_token"]):
            return JSONResponse({"detail": "Invalid CSRF token"}, status_code=403)
    if missing_config and request.method not in SAFE_METHODS and not setup_write_allowed(path):
        return JSONResponse(
            {"detail": "Production integrations incomplete; clinical writes are disabled",
             "missing": missing_config},
            status_code=503,
        )
    request.state.staff = session
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), geolocation=(), microphone=(self)"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    if production_like():
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# ── Helpers ───────────────────────────────────────────────────────────────────

def require_admin(request: Request) -> dict:
    staff = request.state.staff
    if staff["role"] != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return staff


async def record_audit(
    db: Connection, staff: dict, action: str, subject_type: str,
    subject_id: int | str, details: dict | None = None,
) -> None:
    await db.execute(
        """INSERT INTO audit_events
           (staff_user_id, staff_name, action, subject_type, subject_id, details, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (staff["id"], staff["name"], action, subject_type, str(subject_id),
         json.dumps(details or {}), datetime.now().isoformat()),
    )


class LoginRequest(BaseModel):
    email: str
    password: str


class StaffCreateRequest(BaseModel):
    email: str
    name: str
    role: Literal["admin", "care_team"] = "care_team"
    password: str


class ClinicSettingsRequest(BaseModel):
    clinic_name: str
    timezone: str = "Africa/Accra"
    escalation_phone: str = ""


class StaffStatusRequest(BaseModel):
    active: bool


class StaffPasswordRequest(BaseModel):
    password: str


@app.post("/api/auth/login")
async def login(body: LoginRequest, request: Request, response: Response):
    if DB_ERROR:
        raise HTTPException(status_code=503, detail="Database unavailable")
    async with db_store.connect() as db:
        user = await auth.authenticate(db, body.email, body.password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials or account temporarily locked")
        session = await auth.create_session(
            db, user["id"], request.headers.get("user-agent", ""),
            request.client.host if request.client else "",
        )
    response.set_cookie(
        value=session["token"],
        **auth.cookie_options(request.url.scheme, request.url.hostname or ""),
    )
    return {
        "user": user, "csrf_token": session["csrf_token"],
        "expires_at": session["expires_at"], "demo_enabled": demo_tools_enabled(),
    }


@app.get("/api/auth/me")
async def current_staff(request: Request):
    staff = request.state.staff
    return {
        "user": {key: staff[key] for key in ("id", "email", "name", "role")},
        "csrf_token": staff["csrf_token"], "expires_at": staff["expires_at"],
        "demo_enabled": demo_tools_enabled(),
    }


@app.post("/api/auth/logout", status_code=204)
async def logout(request: Request, response: Response):
    async with db_store.connect() as db:
        await auth.revoke_session(db, request.cookies.get(auth.COOKIE_NAME, ""))
    response.delete_cookie(auth.COOKIE_NAME, path="/")


@app.get("/api/staff")
async def list_staff(request: Request):
    require_admin(request)
    async with db_store.connect() as db:
        cursor = await db.execute(
            "SELECT id, email, name, role, active, last_login_at, created_at FROM staff_users ORDER BY name"
        )
        return [
            {"id": row[0], "email": row[1], "name": row[2], "role": row[3],
             "active": bool(row[4]), "last_login_at": row[5], "created_at": row[6]}
            for row in await cursor.fetchall()
        ]


@app.post("/api/staff", status_code=201)
async def create_staff(body: StaffCreateRequest, request: Request):
    actor = require_admin(request)
    email, name = body.email.strip().lower(), body.name.strip()
    if "@" not in email or not name:
        raise HTTPException(status_code=400, detail="A valid email and name are required")
    try:
        password_hash = auth.hash_password(body.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    async with db_store.connect() as db:
        try:
            staff_id = await insert_returning_id(
                db,
                """INSERT INTO staff_users (email, name, role, password_hash, active, created_at)
                   VALUES (?,?,?,?,1,?)""",
                (email, name, body.role, password_hash, auth.utc_now().isoformat()),
            )
            await record_audit(db, actor, "staff.created", "staff_user", staff_id,
                               {"email": email, "role": body.role})
            await db.commit()
        except Exception as exc:
            if "unique" in str(exc).lower():
                raise HTTPException(status_code=409, detail="A staff account with that email exists")
            raise
    return {"id": staff_id, "email": email, "name": name, "role": body.role, "active": True}


@app.get("/api/settings/clinic")
async def get_clinic_settings():
    async with db_store.connect() as db:
        row = await (await db.execute(
            "SELECT clinic_name, timezone, escalation_phone, updated_at FROM clinic_settings WHERE id=1"
        )).fetchone()
    return {"clinic_name": row[0], "timezone": row[1], "escalation_phone": row[2], "updated_at": row[3]}


@app.patch("/api/settings/clinic")
async def update_clinic_settings(body: ClinicSettingsRequest, request: Request):
    staff = require_admin(request)
    try:
        ZoneInfo(body.timezone)
    except Exception:
        raise HTTPException(status_code=400, detail="Unknown timezone")
    if not body.clinic_name.strip():
        raise HTTPException(status_code=400, detail="Clinic name is required")
    async with db_store.connect() as db:
        await db.execute(
            """UPDATE clinic_settings SET clinic_name=?, timezone=?, escalation_phone=?,
                      updated_at=?, updated_by=? WHERE id=1""",
            (body.clinic_name.strip(), body.timezone, body.escalation_phone.strip(),
             datetime.now().isoformat(), staff["id"]),
        )
        await record_audit(db, staff, "clinic_settings.updated", "clinic", 1,
                           {"clinic_name": body.clinic_name.strip(), "timezone": body.timezone})
        await db.commit()
    return {"clinic_name": body.clinic_name.strip(), "timezone": body.timezone,
            "escalation_phone": body.escalation_phone.strip()}


@app.patch("/api/staff/{staff_id}/status")
async def update_staff_status(staff_id: int, body: StaffStatusRequest, request: Request):
    actor = require_admin(request)
    if staff_id == actor["id"] and not body.active:
        raise HTTPException(status_code=409, detail="You cannot deactivate your own account")
    async with db_store.connect() as db:
        row = await (await db.execute("SELECT role FROM staff_users WHERE id=?", (staff_id,))).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Staff account not found")
        if row[0] == "admin" and not body.active:
            count = await (await db.execute(
                "SELECT COUNT(*) FROM staff_users WHERE role='admin' AND active=1"
            )).fetchone()
            if count[0] <= 1:
                raise HTTPException(status_code=409, detail="At least one active administrator is required")
        await db.execute("UPDATE staff_users SET active=? WHERE id=?", (int(body.active), staff_id))
        if not body.active:
            await db.execute("DELETE FROM staff_sessions WHERE user_id=?", (staff_id,))
        await record_audit(db, actor, "staff.status_changed", "staff_user", staff_id,
                           {"active": body.active})
        await db.commit()
    return {"id": staff_id, "active": body.active}


@app.post("/api/staff/{staff_id}/password", status_code=204)
async def reset_staff_password(staff_id: int, body: StaffPasswordRequest, request: Request):
    actor = require_admin(request)
    try:
        password_hash = auth.hash_password(body.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    async with db_store.connect() as db:
        cursor = await db.execute("UPDATE staff_users SET password_hash=? WHERE id=?", (password_hash, staff_id))
        if cursor.rowcount != 1:
            raise HTTPException(status_code=404, detail="Staff account not found")
        await db.execute("DELETE FROM staff_sessions WHERE user_id=?", (staff_id,))
        await record_audit(db, actor, "staff.password_reset", "staff_user", staff_id)
        await db.commit()


@app.get("/api/audit")
async def get_audit_events(request: Request, limit: int = 100):
    require_admin(request)
    limit = max(1, min(limit, 500))
    async with db_store.connect() as db:
        cursor = await db.execute(
            """SELECT id, staff_user_id, staff_name, action, subject_type,
                      subject_id, details, created_at
               FROM audit_events ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        )
        return [
            {"id": row[0], "staff_user_id": row[1], "staff_name": row[2],
             "action": row[3], "subject_type": row[4], "subject_id": row[5],
             "details": json.loads(row[6]), "created_at": row[7]}
            for row in await cursor.fetchall()
        ]

async def compute_adherence(patient_id: int, db: Connection, days: int = 14) -> int:
    cursor = await db.execute(
        "SELECT response FROM adherence_logs WHERE patient_id=? AND log_date>?",
        (patient_id, (date.today() - timedelta(days=days)).isoformat())
    )
    rows = await cursor.fetchall()
    if not rows:
        return 0
    yes_count = sum(1 for r in rows if r[0] == "yes")
    return round(yes_count / len(rows) * 100)


async def compute_care_completion(patient_id: int, db: Connection, days: int = 14) -> int:
    cursor = await db.execute(
        "SELECT response FROM care_logs WHERE patient_id=? AND log_date>?",
        (patient_id, (date.today() - timedelta(days=days)).isoformat()),
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
        """SELECT e.id, e.reason, e.risk_level, e.details, e.created_at,
                  e.assigned_to, owner.name, e.acknowledged_at, e.due_at,
                  e.notification_status
           FROM escalations e LEFT JOIN staff_users owner ON owner.id=e.assigned_to
           WHERE e.patient_id=? AND e.resolved=0 ORDER BY e.created_at DESC""",
        (patient_id,)
    )
    escs = await cursor.fetchall()
    patient["escalations"] = [
        {"id": e[0], "reason": e[1], "risk_level": e[2], "details": json.loads(e[3]),
         "created_at": e[4], "assigned_to": e[5], "assigned_to_name": e[6],
         "acknowledged_at": e[7], "due_at": e[8], "notification_status": e[9]}
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
    if not patient["last_checkin"]:
        # Older demo data recorded the safety escalation before checkin_logs was
        # introduced. Keep the clinical dashboard internally consistent by
        # showing that auditable reading instead of claiming there is none.
        reading_escalation = next(
            (item for item in patient["escalations"] if item["details"].get("reading")),
            None,
        )
        if reading_escalation:
            patient["last_checkin"] = {
                "type": "blood_pressure",
                "value": reading_escalation["details"]["reading"],
                "risk": reading_escalation["risk_level"],
                "at": reading_escalation["created_at"],
            }

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

    cursor = await db.execute(
        """SELECT consent_status, method, recorded_by, note, created_at
           FROM consent_events WHERE patient_id=? ORDER BY created_at DESC LIMIT 10""",
        (patient_id,),
    )
    patient["consent_history"] = [
        {"status": row[0], "method": row[1], "recorded_by": row[2],
         "note": row[3], "created_at": row[4]}
        for row in await cursor.fetchall()
    ]

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
    preferred_language: Literal["en", "tw-en", "gaa-en", "ewe-en", "pcm-en"] = "en"
    reminder_time: str = "08:00"
    consent_granted: bool = False


class PatientCommunicationRequest(BaseModel):
    preferred_language: Optional[Literal["en", "tw-en", "gaa-en", "ewe-en", "pcm-en"]] = None
    reminder_time: Optional[str] = None
    consent_status: Optional[Literal["pending", "granted", "withdrawn"]] = None
    communication_opt_in: Optional[bool] = None
    paused: Optional[bool] = None


@app.post("/api/patients")
async def enroll_patient(body: EnrollRequest, request: Request):
    require_admin(request)
    missing_config = missing_production_config()
    if missing_config and body.consent_granted:
        raise HTTPException(
            status_code=503,
            detail=(
                "WhatsApp setup is incomplete. Save this patient with consent unchecked for now; "
                "messaging can be activated after the missing production integrations are configured."
            ),
        )
    if production_like() and body.category != "chronic":
        raise HTTPException(
            status_code=400,
            detail="The production pilot currently enrols hypertension chronic-care patients only",
        )
    try:
        datetime.strptime(body.reminder_time, "%H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Reminder time must be HH:MM")
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
            pid = await insert_returning_id(
                db,
                """INSERT INTO patients (name, phone, age, condition, drug_name, drug_dosage,
                   category, service_type, care_instructions, next_follow_up, recall_date,
                   enrolled_at, doctor_name, risk_level, preferred_language,
                   reminder_time, consent_status, consent_recorded_at,
                   consent_recorded_by, communication_opt_in)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'green',?,?,?,?,?,?)""",
                (body.name, body.phone, body.age, condition, body.drug_name or "", body.drug_dosage or "",
                 body.category, service_type, care_instructions, body.next_follow_up, body.recall_date,
                 date.today().isoformat(), body.doctor_name, body.preferred_language,
                 body.reminder_time, "granted" if body.consent_granted else "pending",
                 datetime.now().isoformat() if body.consent_granted else None,
                 request.state.staff["name"] if body.consent_granted else "",
                 int(body.consent_granted))
            )
            await db.execute(
                "INSERT INTO conversation_state (patient_id, current_flow, context) VALUES (?, 'idle', '{}')",
                (pid,)
            )
            await db.execute(
                """INSERT INTO consent_events
                   (patient_id, consent_status, method, recorded_by, note, created_at)
                   VALUES (?,?,?,?,?,?)""",
                (pid, "granted" if body.consent_granted else "pending", "staff_enrollment",
                 request.state.staff["name"],
                 "Patient agreed to WhatsApp care messages" if body.consent_granted else "Consent not yet recorded",
                 datetime.now().isoformat()),
            )
            await record_audit(
                db, request.state.staff, "patient.enrolled", "patient", pid,
                {"consent_status": "granted" if body.consent_granted else "pending",
                 "preferred_language": body.preferred_language},
            )
            await db.commit()

            # Welcome message. A newly enrolled patient is normally outside
            # WhatsApp's 24-hour service window, so prefer an approved template.
            # If no template is configured we still try the exact free-text
            # welcome: that succeeds when the patient recently messaged the
            # clinic, and otherwise returns Meta's reason to the operator.
            first = display_first_name(body.name)
            welcome = (
                f"Welcome to VeloxaCare, {first}! 👋 I’ll help you stay on track "
                "with your care and follow-up. Reply START to begin."
            )
            template_name = os.getenv("META_WELCOME_TEMPLATE", "").strip()
            template_language = os.getenv("META_WELCOME_TEMPLATE_LANGUAGE", "en_US").strip() or "en_US"
            if not body.consent_granted:
                delivery = whatsapp.SendResult(False, error="Consent is pending; no message was sent")
                delivery_mode = "consent_pending"
            elif template_name:
                delivery = await whatsapp.send_template(
                    body.phone, template_name, template_language, [first],
                )
                delivery_mode = "template"
            else:
                delivery = await whatsapp.send_text_result(body.phone, welcome)
                delivery_mode = "free_text"

            channel = "whatsapp" if whatsapp.is_configured() else "simulator"
            if body.consent_granted:
                now = datetime.now().isoformat()
                await db.execute(
                    """INSERT INTO messages
                       (patient_id, direction, body, created_at, channel, delivery_status,
                        delivery_error, external_message_id) VALUES (?,?,?,?,?,?,?,?)""",
                    (pid, "outbound", welcome, now, channel,
                     "accepted" if delivery.delivered else "failed",
                     delivery.error, delivery.message_id)
                )
                await db.commit()

            p = await get_patient_full(pid, db)
            if not body.consent_granted:
                delivery_note = "Patient saved with consent pending. No WhatsApp message was sent."
            elif delivery.delivered:
                delivery_note = (
                    "WhatsApp accepted the approved welcome template; delivery status will update in the conversation."
                    if delivery_mode == "template"
                    else "WhatsApp accepted the welcome; delivery status will update in the conversation."
                )
            elif template_name:
                delivery_note = delivery.error or "WhatsApp did not accept the welcome template."
            elif whatsapp.is_configured():
                delivery_note = (
                    f"{delivery.error or 'WhatsApp did not accept the welcome.'} "
                    "Configure the approved META_WELCOME_TEMPLATE for new patients."
                )
            else:
                delivery_note = "WhatsApp credentials are not configured; welcome saved locally only."
            p["welcome_delivery"] = {
                "delivered": delivery.delivered,
                "channel": channel,
                "mode": delivery_mode,
                "message_id": delivery.message_id,
                "note": delivery_note,
            }
            await manager.broadcast_all({"type": "patient_enrolled", "patient": p})
            return p
        except Exception as e:
            if "UNIQUE" in str(e):
                raise HTTPException(400, "Phone number already registered")
            raise HTTPException(500, str(e))


@app.patch("/api/patients/{patient_id}/communication")
async def update_patient_communication(
    patient_id: int, body: PatientCommunicationRequest, request: Request,
):
    updates, params = [], []
    if body.reminder_time is not None:
        try:
            datetime.strptime(body.reminder_time, "%H:%M")
        except ValueError:
            raise HTTPException(status_code=400, detail="Reminder time must be HH:MM")
    for field in ("preferred_language", "reminder_time", "consent_status"):
        value = getattr(body, field)
        if value is not None:
            updates.append(f"{field}=?")
            params.append(value)
    for field in ("communication_opt_in", "paused"):
        value = getattr(body, field)
        if value is not None:
            updates.append(f"{field}=?")
            params.append(int(value))
    if body.consent_status is not None:
        updates.extend(["consent_recorded_at=?", "consent_recorded_by=?"])
        params.extend([datetime.now().isoformat(), request.state.staff["name"]])
        if body.consent_status != "granted":
            updates.append("communication_opt_in=0")
    if not updates:
        raise HTTPException(status_code=400, detail="No communication settings supplied")
    params.append(patient_id)
    async with db_store.connect() as db:
        cursor = await db.execute("SELECT id FROM patients WHERE id=?", (patient_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Patient not found")
        await db.execute(f"UPDATE patients SET {', '.join(updates)} WHERE id=?", tuple(params))
        if body.consent_status is not None:
            await db.execute(
                """INSERT INTO consent_events
                   (patient_id, consent_status, method, recorded_by, note, created_at)
                   VALUES (?,?,'staff_update',?,?,?)""",
                (patient_id, body.consent_status, request.state.staff["name"],
                 "Communication consent updated in clinic workspace", datetime.now().isoformat()),
            )
        await record_audit(
            db, request.state.staff, "patient.communication_updated", "patient", patient_id,
            body.model_dump(exclude_none=True),
        )
        await db.commit()
        patient = await get_patient_full(patient_id, db)
    await manager.broadcast_all({"type": "patient_updated", "patient": patient})
    return patient


# ── Routes: messages ──────────────────────────────────────────────────────────

@app.get("/api/patients/{patient_id}/messages")
async def get_messages(patient_id: int, limit: int = 50):
    async with db_store.connect() as db:
        cursor = await db.execute(
            "SELECT id, direction, body, reason, created_at, channel, audio_file, stt_provider, "
            "stt_language, stt_latency_ms, tts_provider, tts_voice, tts_latency_ms, "
            "delivery_status, delivery_error, external_message_id, spoken_body "
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
                "tts_provider": r[10] or None, "tts_voice": r[11] or None,
                "tts_latency_ms": r[12] or None,
                "delivery_status": r[13] or None,
                "delivery_error": r[14] or None,
                "external_message_id": r[15] or None,
                "spoken_body": r[16] or None,
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


class AppointmentCreateRequest(BaseModel):
    patient_id: int
    appointment_date: str
    appointment_time: str
    clinician_name: str = ""
    visit_type: str = ""


class AppointmentUpdateRequest(BaseModel):
    appointment_date: Optional[str] = None
    appointment_time: Optional[str] = None
    status: Optional[Literal["confirmed", "cancelled", "completed", "no_show"]] = None


async def speak_reply(text: str, language: str, accept: tuple):
    """Voice a reply — in the patient's own language when we truly can.

    When the pair has a real voice (Khaya: Twi, Ewe) *and* translation is
    configured, the reply is translated first and spoken by that voice, because
    a Twi voice reading English text is worse than an accented English voice
    doing it. Every other case — including any failure along the way — falls
    back to the existing chain speaking the English reply, so this path can
    only ever add capability, never take it away.

    Returns (SynthesisResult, spoken_body): spoken_body is the translated text
    the voice actually said, or "" when the audio speaks the reply verbatim.
    The stored message body stays English either way — spoken_body is what
    keeps the clinical record honest about what the patient heard.
    """
    if translate.can_render(language) and language in tts.KHAYA_TTS_LANG:
        translated = await translate.translate(text, language)
        if translated.ok:
            native = await tts.synthesize(
                translated.text, language=language, provider="khaya", accept=accept,
            )
            if native.ok:
                native.meta["translation"] = {
                    "provider": translated.provider,
                    "target": translated.target,
                    "latency_ms": translated.latency_ms,
                }
                return native, translated.text
    return await tts.synthesize(text, language=language, accept=accept), ""


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
        inbound_id = await insert_returning_id(
            db,
            "INSERT INTO messages (patient_id, direction, body, created_at, channel, audio_file, stt_provider, stt_language, stt_latency_ms) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (patient_id, "inbound", text, now, channel, voice.get("audio_file", ""),
             voice.get("stt_provider", ""), voice.get("stt_language", ""),
             voice.get("stt_latency_ms", 0))
        )
        await db.commit()

        inbound_msg = {
            "id": inbound_id, "direction": "inbound", "body": text, "reason": None, "created_at": now,
            "channel": channel,
            "audio_file": voice.get("audio_file") or None,
            "stt_provider": voice.get("stt_provider") or None,
            "stt_language": voice.get("stt_language") or None,
            "stt_latency_ms": voice.get("stt_latency_ms") or None,
            "tts_provider": None, "tts_voice": None, "tts_latency_ms": None,
        }
        await manager.broadcast(patient_id, {"type": "message", "message": inbound_msg})

        # Consent keywords are deterministic boundary rules, never an LLM
        # interpretation. A patient can stop outreach from the same channel at
        # any time; START records a fresh affirmative opt-in.
        normalized = text.strip().upper()
        if normalized in {"STOP", "UNSUBSCRIBE", "PAUSE"}:
            await db.execute(
                """UPDATE patients SET consent_status='withdrawn', communication_opt_in=0,
                          paused=1, consent_recorded_at=?, consent_recorded_by='Patient WhatsApp'
                   WHERE id=?""",
                (datetime.now().isoformat(), patient_id),
            )
            await db.execute(
                """INSERT INTO consent_events
                   (patient_id, consent_status, method, recorded_by, note, created_at)
                   VALUES (?,'withdrawn','patient_message','Patient WhatsApp',?,?)""",
                (patient_id, normalized, datetime.now().isoformat()),
            )
            await db.commit()
            bot_reply = (
                "Your VeloxaCare messages are now stopped. You can still contact your clinic directly. "
                "Reply START if you want to receive care messages again."
            )
            reason, escalation_created = None, False
        elif normalized == "START":
            await db.execute(
                """UPDATE patients SET consent_status='granted', communication_opt_in=1,
                          paused=0, consent_recorded_at=?, consent_recorded_by='Patient WhatsApp'
                   WHERE id=?""",
                (datetime.now().isoformat(), patient_id),
            )
            await db.execute(
                """INSERT INTO consent_events
                   (patient_id, consent_status, method, recorded_by, note, created_at)
                   VALUES (?,'granted','patient_message','Patient WhatsApp','START',?)""",
                (patient_id, datetime.now().isoformat()),
            )
            await db.commit()
            bot_reply = (
                "You’re set up to receive VeloxaCare messages. Reply STOP at any time to pause them."
            )
            reason, escalation_created = None, False
        else:
            # Process and get bot reply
            bot_reply, reason, escalation_created = await process_message(patient_id, text, db)

        # Answer in the modality the patient used: a voice note gets a spoken
        # reply. Patients who send voice are disproportionately the ones who
        # read with difficulty, so replying in text alone would throw away the
        # accessibility the voice channel just bought us.
        #
        # Synthesised in the same language hint the transcript came in on, and
        # before the row is written so the message arrives with its audio
        # already attached rather than appearing mute and then updating.
        spoken = None
        spoken_body = ""
        if tts.should_speak(bool(voice)):
            spoken, spoken_body = await speak_reply(
                bot_reply,
                language=voice.get("stt_language") or os.getenv("WHATSAPP_STT_LANGUAGE", "en"),
                # WhatsApp takes MP3, and Ogg/Opus as a true voice-note bubble;
                # browsers take either. Ask for Ogg first so the real channel
                # gets the nicer rendering, and let the provider chain decide.
                accept=("ogg", "mp3") if channel == "whatsapp" else tts.DEFAULT_ACCEPT,
            )

        reply_audio = ""
        if spoken and spoken.ok:
            reply_audio = f"p{patient_id}_reply_{uuid.uuid4().hex[:12]}{spoken.suffix}"
            try:
                (ensure_voice_dir() / reply_audio).write_bytes(spoken.audio)
            except OSError as e:
                # Read-only disk: the patient still hears the reply over
                # WhatsApp, only the dashboard replay is lost.
                logging.getLogger(__name__).warning("Could not store spoken reply: %s", e)
                reply_audio = ""

        # Log outbound
        bot_now = datetime.now().isoformat()
        outbound_id = await insert_returning_id(
            db,
            "INSERT INTO messages (patient_id, direction, body, reason, created_at, channel, "
            "audio_file, tts_provider, tts_voice, tts_latency_ms, spoken_body) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (patient_id, "outbound", bot_reply, reason, bot_now, channel, reply_audio,
             spoken.provider if reply_audio else "", spoken.voice if reply_audio else "",
             spoken.latency_ms if reply_audio else 0,
             spoken_body if reply_audio else "")
        )
        await db.commit()

        outbound_msg = {
            "id": outbound_id, "direction": "outbound", "body": bot_reply,
            "reason": reason, "created_at": bot_now, "channel": channel,
            "audio_file": reply_audio or None,
            "stt_provider": None, "stt_language": None, "stt_latency_ms": None,
            "tts_provider": spoken.provider if reply_audio else None,
            "tts_voice": spoken.voice if reply_audio else None,
            "tts_latency_ms": spoken.latency_ms if reply_audio else None,
            "spoken_body": (spoken_body if reply_audio else "") or None,
        }
        await manager.broadcast(patient_id, {"type": "message", "message": outbound_msg})

        # Push updated patient stats
        p = await get_patient_full(patient_id, db)

        # Reply over the transport the patient actually used. The dashboard sees
        # the message either way via the broadcast above.
        if channel == "whatsapp":
            # Text first, then the voice note. The text is the durable record
            # and stays readable, searchable and forwardable to a family member;
            # the audio is what the patient who can't read it needs. Set
            # TTS_WHATSAPP_SEND_TEXT=0 for voice-only replies.
            # Voice-only still falls back to text when synthesis failed —
            # otherwise a dead TTS key means the patient gets nothing at all.
            if not (spoken and spoken.ok) or os.getenv("TTS_WHATSAPP_SEND_TEXT", "1") != "0":
                await whatsapp.send_text(p["phone"], bot_reply)
            if spoken and spoken.ok:
                await whatsapp.send_audio(
                    p["phone"], spoken.audio, spoken.mime, f"reply{spoken.suffix}"
                )
        await manager.broadcast(patient_id, {"type": "patient_updated", "patient": p})
        await manager.broadcast_all({"type": "patient_updated", "patient": p})

        changed_appointment = await appointments.latest_changed_since(db, patient_id, now)
        if changed_appointment:
            await manager.broadcast_all({
                "type": "appointment_updated",
                "appointment": changed_appointment,
            })

        if escalation_created:
            cursor = await db.execute(
                "SELECT id, reason, risk_level, details, created_at FROM escalations WHERE patient_id=? ORDER BY id DESC LIMIT 1",
                (patient_id,)
            )
            esc = await cursor.fetchone()
            if esc:
                due_at = (datetime.now() + timedelta(hours=4 if esc[2] == "red" else 24)).isoformat()
                settings = await (await db.execute(
                    "SELECT escalation_phone FROM clinic_settings WHERE id=1"
                )).fetchone()
                alert_phone = (settings[0] if settings else "") or ""
                alert_template = os.getenv("META_STAFF_ALERT_TEMPLATE", "").strip()
                if alert_phone and alert_template:
                    notification = await whatsapp.send_template(
                        alert_phone, alert_template,
                        os.getenv("META_STAFF_ALERT_TEMPLATE_LANGUAGE", "en_US"),
                        [p["name"], esc[2].upper(), esc[1][:120]],
                    )
                    notification_status = "accepted" if notification.delivered else "failed"
                else:
                    notification = whatsapp.SendResult(
                        False, error="Staff alert phone or approved template is not configured",
                    )
                    notification_status = "dashboard_only"
                await db.execute(
                    """UPDATE escalations SET due_at=?, notification_status=?,
                              notification_error=?, notification_message_id=? WHERE id=?""",
                    (due_at, notification_status, notification.error,
                     notification.message_id, esc[0]),
                )
                await db.commit()
                esc_data = {
                    "id": esc[0], "reason": esc[1], "risk_level": esc[2],
                    "details": json.loads(esc[3]), "created_at": esc[4],
                    "patient_id": patient_id, "patient_name": p["name"],
                    "assigned_to": None, "assigned_to_name": None,
                    "acknowledged_at": None, "due_at": due_at,
                    "notification_status": notification_status,
                }
                await manager.broadcast_all({"type": "escalation", "escalation": esc_data})

        return {"inbound": inbound_msg, "reply": outbound_msg, "escalation_created": escalation_created}


@app.post("/api/patients/{patient_id}/messages")
async def send_patient_message(patient_id: int, body: InboundMessage):
    """Simulate patient sending a WhatsApp text message."""
    if not demo_tools_enabled():
        raise HTTPException(status_code=404, detail="Simulator is disabled in production")
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


@app.get("/api/tts/status")
async def tts_status():
    """Which voice answers the patient, and whether it speaks at all.

    Same honesty rule as /api/stt/status: report the provider that is actually
    serving, not the one that is merely configured. `mode` matters as much as
    the provider here — on 'mirror' a typed message gets no audio by design, and
    that is not a fault to go hunting for mid-demo.
    """
    configured = tts.configured_providers()
    pinned = os.getenv("TTS_PROVIDER") or None
    # Benched providers are excluded from "active" too: during an outage the
    # honest answer to "which voice is speaking" is the fallback, not the one at
    # the head of the chain that every request is currently skipping.
    cooling = {n: round(tts.cooling_down(n)) for n in configured if tts.cooling_down(n)}
    healthy = [n for n in configured if n not in tts._degraded and n not in cooling]
    active = pinned if pinned in healthy else next(
        (n for n in tts.provider_order() if n in healthy), None
    )
    return {
        "configured": configured,
        "pinned": pinned,
        "active": active,
        "degraded": tts._degraded,
        "cooling_down": cooling,
        "mode": tts.mode(),
        "enabled": bool(configured) and tts.mode() != "off",
        # Whether replies can be translated into the patient's language before
        # being spoken (Khaya MT) — the difference between a Twi voice note
        # answered in Twi and one answered in English audio.
        "translation": translate.available(),
        "native_voice_pairs": sorted(tts.KHAYA_TTS_LANG) if translate.available() else [],
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
    if not demo_tools_enabled():
        raise HTTPException(status_code=404, detail="Simulator is disabled in production")
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
                "tts_provider": None, "tts_voice": None, "tts_latency_ms": None,
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

# Meta retries deliveries aggressively. This claim lives in the durable store,
# not process memory, because separate serverless instances see the same retry.
async def _claim_whatsapp_event(message_id: str) -> bool:
    if not message_id:
        return True
    async with db_store.connect() as db:
        cursor = await db.execute(
            """INSERT INTO inbound_events
               (external_message_id, status, received_at) VALUES (?, 'processing', ?)
               ON CONFLICT(external_message_id) DO NOTHING""",
            (message_id, datetime.now().isoformat()),
        )
        await db.commit()
        if cursor.rowcount == 1:
            return True
        existing = await (await db.execute(
            "SELECT status FROM inbound_events WHERE external_message_id=?", (message_id,),
        )).fetchone()
        if existing and existing[0] in {"failed", "processing"}:
            retry = await db.execute(
                """UPDATE inbound_events SET status='processing', error='', received_at=?
                   WHERE external_message_id=? AND
                     (status='failed' OR (status='processing' AND received_at<?))""",
                (datetime.now().isoformat(), message_id,
                 (datetime.now() - timedelta(minutes=5)).isoformat()),
            )
            await db.commit()
            return retry.rowcount == 1
        return False


async def _finish_whatsapp_event(message_id: str, status: str = "processed", error: str = "") -> None:
    if not message_id:
        return
    async with db_store.connect() as db:
        await db.execute(
            "UPDATE inbound_events SET status=?, processed_at=?, error=? WHERE external_message_id=?",
            (status, datetime.now().isoformat(), error[:1000], message_id),
        )
        await db.commit()


async def _record_whatsapp_statuses(statuses: list[dict]) -> int:
    """Persist Meta's sent/delivered/read/failed receipts for outbound messages."""
    updates: list[dict] = []
    async with db_store.connect() as db:
        for receipt in statuses:
            message_id = str(receipt.get("id") or "")
            status = str(receipt.get("status") or "")
            if not message_id or status not in {"sent", "delivered", "read", "failed"}:
                continue
            errors = receipt.get("errors") or []
            error = ""
            if errors:
                first_error = errors[0] or {}
                title = str(first_error.get("title") or first_error.get("message") or "Delivery failed")
                code = first_error.get("code")
                error = f"Meta {code}: {title}" if code else title
            cursor = await db.execute(
                "SELECT id, patient_id FROM messages WHERE external_message_id=? LIMIT 1",
                (message_id,),
            )
            row = await cursor.fetchone()
            if not row:
                continue
            await db.execute(
                "UPDATE messages SET delivery_status=?, delivery_error=? WHERE id=?",
                (status, error, row[0]),
            )
            updates.append({
                "message_id": row[0], "patient_id": row[1],
                "delivery_status": status, "delivery_error": error,
            })
        await db.commit()

    for update in updates:
        event = {"type": "message_delivery", **update}
        await manager.broadcast(update["patient_id"], event)
        await manager.broadcast_all(event)
    return len(updates)


async def _patient_by_phone(phone: str) -> Optional[dict]:
    """Resolve an inbound WhatsApp number to an enrolled patient.

    Compared digits-only: Meta sends E.164 without '+', patients are stored with
    it. Falls back to a suffix match so a number stored without its country code
    still resolves.
    """
    target = whatsapp.normalize_phone(phone)
    async with db_store.connect() as db:
        cursor = await db.execute("SELECT id, name, phone, preferred_language FROM patients")
        rows = await cursor.fetchall()
    for pid, name, stored, preferred_language in rows:
        digits = whatsapp.normalize_phone(stored or "")
        if not digits:
            continue
        if digits == target or digits.endswith(target[-9:]) or target.endswith(digits[-9:]):
            return {"id": pid, "name": name, "phone": stored,
                    "preferred_language": preferred_language or "en"}
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


async def _process_whatsapp_message(message: dict) -> dict:
    """Process one item from a possibly batched Meta webhook payload."""
    message_id = message.get("id", "")
    sender = message.get("from", "")
    msg_type = message.get("type", "")

    if not await _claim_whatsapp_event(message_id):
        return {"status": "duplicate_ignored"}
    try:
        patient = await _patient_by_phone(sender)
        if patient is None:
            # Unknown numbers are never auto-enrolled: enrolment is a consented
            # clinical act, not a side effect of texting.
            await whatsapp.send_text(
                sender,
                "Hello! This number isn't registered with the clinic yet. "
                "Please contact your care team to be enrolled.",
            )
            await _finish_whatsapp_event(message_id)
            return {"status": "unknown_sender"}

        if msg_type == "text":
            text = (message.get("text", {}).get("body") or "").strip()
            if not text:
                await _finish_whatsapp_event(message_id)
                return {"status": "empty"}
            await ingest_patient_message(patient["id"], text, channel="whatsapp")
            await _finish_whatsapp_event(message_id)
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
                await _finish_whatsapp_event(message_id)
                return {"status": "media_failed"}

            language = patient.get("preferred_language") or os.getenv("WHATSAPP_STT_LANGUAGE", "en")
            result = await stt.transcribe(str(stored), language=language)
            if not result.ok:
                await whatsapp.send_text(
                    sender,
                    "Sorry, I couldn't hear that clearly. Please send it again, or type your message.",
                )
                await _finish_whatsapp_event(message_id)
                return {"status": "stt_failed", "error": result.error}

            await ingest_patient_message(
                patient["id"], result.text,
                voice={
                    "audio_file": stored.name, "stt_provider": result.provider,
                    "stt_language": language, "stt_latency_ms": result.latency_ms,
                },
                channel="whatsapp",
            )
            await _finish_whatsapp_event(message_id)
            return {"status": "ok"}

        await whatsapp.send_text(
            sender,
            "I can read text and listen to voice notes. Please send one of those.",
        )
        await _finish_whatsapp_event(message_id)
        return {"status": "unsupported_type"}
    except Exception as exc:
        logging.getLogger(__name__).exception("WhatsApp message processing failed")
        await _finish_whatsapp_event(message_id, "failed", f"{type(exc).__name__}: {exc}")
        return {"status": "processing_failed"}


@app.post("/webhook/whatsapp")
async def whatsapp_receive(request: Request):
    """Validate and process every message and receipt in a Meta webhook batch."""
    raw = await request.body()
    if not whatsapp.verify_signature(raw, request.headers.get("x-hub-signature-256")):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")
    try:
        body = json.loads(raw)
        values = [
            change.get("value") or {}
            for entry in body.get("entry", [])
            for change in entry.get("changes", [])
        ]
    except Exception:
        return {"status": "ignored"}
    updated = 0
    results = []
    for value in values:
        updated += await _record_whatsapp_statuses(value.get("statuses") or [])
        for message in value.get("messages") or []:
            results.append(await _process_whatsapp_message(message))
    return {"status": "processed", "messages": results, "delivery_updates": updated}


@app.get("/api/voice/{filename}")
async def get_voice_note(filename: str):
    """Serve a stored voice note back for replay in the chat pane."""
    # Resolve and confine to VOICE_DIR — filename comes off the wire.
    path = (VOICE_DIR / filename).resolve()
    if path.parent != VOICE_DIR.resolve() or not path.is_file():
        raise HTTPException(status_code=404, detail="Voice note not found")
    return FileResponse(path)


# ── Routes: actions ───────────────────────────────────────────────────────────

async def send_care_team_message(
    patient_id: int, body: str, db: Connection, staff: dict | None = None,
) -> dict:
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

    cursor = await db.execute(
        """SELECT name, phone, consent_status, communication_opt_in, paused
           FROM patients WHERE id=?""",
        (patient_id,),
    )
    patient = await cursor.fetchone()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if patient[2] != "granted" or not patient[3] or patient[4]:
        raise HTTPException(
            status_code=409,
            detail="Patient communication is not active. Confirm consent and unpause outreach first.",
        )

    delivery = whatsapp.SendResult(False, error="WhatsApp credentials are not configured")
    channel = "whatsapp" if whatsapp.is_configured() else "simulator"
    if whatsapp.is_configured():
        delivery = await whatsapp.send_text_result(patient[1], body)

    now = datetime.now().isoformat()
    message_id = await insert_returning_id(
        db,
        """INSERT INTO messages
           (patient_id, direction, body, created_at, channel, delivery_status,
            delivery_error, external_message_id) VALUES (?,?,?,?,?,?,?,?)""",
        (patient_id, "outbound", body, now, channel,
         "accepted" if delivery.delivered else "failed",
        delivery.error, delivery.message_id),
    )
    if staff:
        await record_audit(
            db, staff, "patient.outreach_sent", "patient", patient_id,
            {"message_id": message_id, "delivery_status": "accepted" if delivery.delivered else "failed"},
        )
    await db.commit()
    message = {
        "id": message_id,
        "direction": "outbound",
        "body": body,
        "reason": None,
        "created_at": now,
        "channel": channel,
        "audio_file": None,
        "stt_provider": None,
        "stt_language": None,
        "stt_latency_ms": None,
        "tts_provider": None,
        "tts_voice": None,
        "tts_latency_ms": None,
        "delivery_status": "accepted" if delivery.delivered else "failed",
        "delivery_error": delivery.error or None,
        "external_message_id": delivery.message_id or None,
    }
    event = {"type": "message", "message": message, "patient_id": patient_id}
    await manager.broadcast(patient_id, event)
    await manager.broadcast_all(event)
    return {
        "message": message,
        "delivered": delivery.delivered,
        "channel": channel,
        "delivery_note": (
            "WhatsApp accepted the message; delivery status will update in the conversation"
            if delivery.delivered else delivery.error
        ),
    }


@app.post("/api/patients/{patient_id}/outreach")
async def send_outreach(patient_id: int, body: OutreachRequest, request: Request):
    """Send a human-authored care-team message to a patient."""
    async with db_store.connect() as db:
        return await send_care_team_message(patient_id, body.message, db, request.state.staff)

@app.post("/api/patients/{patient_id}/remind")
async def send_reminder(patient_id: int, request: Request):
    """Send the category-specific care reminder."""
    async with db_store.connect() as db:
        reminder = await trigger_care_reminder(patient_id, db)
        if not reminder:
            raise HTTPException(status_code=404, detail="Patient not found")
        return await send_care_team_message(patient_id, reminder, db, request.state.staff)


@app.post("/api/patients/{patient_id}/checkin")
async def send_checkin(patient_id: int, request: Request):
    """Send the category-specific check-in prompt."""
    async with db_store.connect() as db:
        prompt = await trigger_checkin(patient_id, db)
        if not prompt:
            raise HTTPException(status_code=404, detail="Patient not found")
        return await send_care_team_message(patient_id, prompt, db, request.state.staff)


# ── Scheduled outreach ───────────────────────────────────────────────────────

@app.get("/api/cron/hourly")
async def hourly_reminders(request: Request):
    """Dispatch due reminders once, with durable retry and delivery records."""
    expected = os.getenv("CRON_SECRET", "")
    supplied = request.headers.get("authorization", "")
    if not expected or not secrets.compare_digest(supplied, f"Bearer {expected}"):
        raise HTTPException(status_code=401, detail="Invalid cron authorization")

    now = datetime.now(ZoneInfo("Africa/Accra"))
    dispatch_date, hour = now.date().isoformat(), f"{now.hour:02d}"
    template_name = os.getenv("META_MEDICATION_REMINDER_TEMPLATE", "").strip()
    template_language = os.getenv("META_MEDICATION_REMINDER_TEMPLATE_LANGUAGE", "en_US").strip() or "en_US"
    sent, failed, skipped = 0, 0, 0

    async with db_store.connect() as db:
        await db.execute("DELETE FROM staff_sessions WHERE expires_at<=?", (auth.utc_now().isoformat(),))
        await db.execute(
            "DELETE FROM inbound_events WHERE received_at<?",
            ((datetime.now() - timedelta(days=30)).isoformat(),),
        )
        cursor = await db.execute(
            """SELECT id, name, phone, drug_name, drug_dosage, preferred_language
               FROM patients
               WHERE status='active' AND category='chronic' AND consent_status='granted'
                 AND communication_opt_in=1 AND paused=0
                 AND substr(reminder_time,1,2)=? ORDER BY id""",
            (hour,),
        )
        patients_due = await cursor.fetchall()

        for patient_id, name, phone, drug, dosage, preferred_language in patients_due:
            timestamp = now.isoformat()
            await db.execute(
                """INSERT INTO reminder_dispatches
                   (patient_id, reminder_kind, dispatch_date, scheduled_for, status,
                    attempts, created_at, updated_at)
                   VALUES (?, 'medication', ?, ?, 'pending', 0, ?, ?)
                   ON CONFLICT(patient_id, reminder_kind, dispatch_date) DO NOTHING""",
                (patient_id, dispatch_date, timestamp, timestamp, timestamp),
            )
            claim = await db.execute(
                """UPDATE reminder_dispatches SET status='sending', attempts=attempts+1, updated_at=?
                   WHERE patient_id=? AND reminder_kind='medication' AND dispatch_date=?
                     AND status IN ('pending','failed') AND attempts<3""",
                (timestamp, patient_id, dispatch_date),
            )
            await db.commit()
            if claim.rowcount != 1:
                skipped += 1
                continue

            body = await trigger_care_reminder(patient_id, db)
            language_suffix = {
                "tw-en": "TWI", "gaa-en": "GA", "ewe-en": "EWE", "pcm-en": "PIDGIN",
            }.get(preferred_language, "EN")
            patient_template = os.getenv(
                f"META_MEDICATION_REMINDER_TEMPLATE_{language_suffix}", template_name,
            ).strip()
            patient_template_language = os.getenv(
                f"META_MEDICATION_REMINDER_TEMPLATE_LANGUAGE_{language_suffix}", template_language,
            ).strip() or template_language
            if not patient_template:
                delivery = whatsapp.SendResult(False, error="Medication reminder template is not configured")
            else:
                delivery = await whatsapp.send_template(
                    phone, patient_template, patient_template_language,
                    [display_first_name(name), drug or "your medicine", dosage or "as prescribed"],
                )
            status = "sent" if delivery.delivered else "failed"
            await db.execute(
                """UPDATE reminder_dispatches
                   SET status=?, last_error=?, external_message_id=?, updated_at=?
                   WHERE patient_id=? AND reminder_kind='medication' AND dispatch_date=?""",
                (status, delivery.error, delivery.message_id, datetime.now().isoformat(),
                 patient_id, dispatch_date),
            )
            message_id = await insert_returning_id(
                db,
                """INSERT INTO messages
                   (patient_id, direction, body, created_at, channel, delivery_status,
                    delivery_error, external_message_id) VALUES (?,?,?,?,?,?,?,?)""",
                (patient_id, "outbound", body, datetime.now().isoformat(), "whatsapp",
                 "accepted" if delivery.delivered else "failed", delivery.error, delivery.message_id),
            )
            await db.commit()
            event = {
                "type": "message", "patient_id": patient_id,
                "message": {"id": message_id, "direction": "outbound",
                            "body": body, "created_at": datetime.now().isoformat(),
                            "channel": "whatsapp", "delivery_status": "accepted" if delivery.delivered else "failed",
                            "delivery_error": delivery.error or None,
                            "external_message_id": delivery.message_id or None},
            }
            await manager.broadcast(patient_id, event)
            await manager.broadcast_all(event)
            if delivery.delivered:
                sent += 1
            else:
                failed += 1
        await db.commit()
    return {"status": "ok", "date": dispatch_date, "due": len(patients_due),
            "sent": sent, "failed": failed, "skipped": skipped}


# ── Routes: appointments ─────────────────────────────────────────────────────

def _validated_appointment_date(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail="Appointment date must be YYYY-MM-DD")
    error = appointments.validate_appointment_date(parsed)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return parsed


def _validate_appointment_time(value: str) -> str:
    if value not in appointments.ALL_SLOTS:
        choices = ", ".join(appointments.format_time(slot) for slot in appointments.ALL_SLOTS)
        raise HTTPException(status_code=400, detail=f"Choose a clinic time: {choices}")
    return value


@app.get("/api/appointments")
async def get_appointments(status: Optional[str] = None, include_past: bool = True):
    async with db_store.connect() as db:
        rows = await appointments.list_appointments(db, include_past=include_past)
        return [item for item in rows if not status or item["status"] == status]


@app.get("/api/patients/{patient_id}/appointments")
async def get_patient_appointments(patient_id: int):
    async with db_store.connect() as db:
        return await appointments.list_appointments(db, patient_id=patient_id)


@app.post("/api/appointments")
async def create_staff_appointment(body: AppointmentCreateRequest):
    _validated_appointment_date(body.appointment_date)
    _validate_appointment_time(body.appointment_time)
    async with db_store.connect() as db:
        cursor = await db.execute(
            "SELECT doctor_name, service_type, condition FROM patients WHERE id=?",
            (body.patient_id,),
        )
        patient = await cursor.fetchone()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        clinician = body.clinician_name.strip() or patient[0] or "Dr. Mensah"
        visit_type = body.visit_type.strip() or patient[1] or f"{patient[2]} review"
        try:
            appointment = await appointments.create_appointment(
                db, body.patient_id, body.appointment_date, body.appointment_time,
                clinician, visit_type,
            )
        except Exception as exc:
            if "unique" in str(exc).lower() or "constraint" in str(exc).lower():
                raise HTTPException(status_code=409, detail="That clinic slot has already been booked")
            raise
        await manager.broadcast_all({"type": "appointment_updated", "appointment": appointment})
        return appointment


@app.patch("/api/appointments/{appointment_id}")
async def update_appointment(appointment_id: int, body: AppointmentUpdateRequest):
    async with db_store.connect() as db:
        current = await appointments.get_appointment(db, appointment_id)
        if not current:
            raise HTTPException(status_code=404, detail="Appointment not found")

        appointment = current
        if body.appointment_date is not None or body.appointment_time is not None:
            next_date = body.appointment_date or current["appointment_date"]
            next_time = body.appointment_time or current["appointment_time"]
            _validated_appointment_date(next_date)
            _validate_appointment_time(next_time)
            cursor = await db.execute(
                """SELECT id FROM appointments WHERE clinician_name=? AND appointment_date=?
                   AND appointment_time=? AND status='confirmed' AND id<>?""",
                (current["clinician_name"], next_date, next_time, appointment_id),
            )
            if await cursor.fetchone():
                raise HTTPException(status_code=409, detail="That clinic slot has already been booked")
            appointment = await appointments.reschedule_appointment(
                db, appointment_id, next_date, next_time,
            )
        if body.status is not None:
            appointment = await appointments.update_status(db, appointment_id, body.status)

        await manager.broadcast_all({"type": "appointment_updated", "appointment": appointment})
        return appointment


# ── Routes: alerts ────────────────────────────────────────────────────────────

@app.get("/api/alerts")
async def get_alerts():
    async with db_store.connect() as db:
        cursor = await db.execute(
            """SELECT e.id, e.patient_id, p.name, e.reason, e.risk_level, e.details,
                      e.created_at, e.assigned_to, owner.name, e.acknowledged_at,
                      e.due_at, e.notification_status
               FROM escalations e JOIN patients p ON e.patient_id=p.id
               LEFT JOIN staff_users owner ON owner.id=e.assigned_to
               WHERE e.resolved=0 ORDER BY e.risk_level ASC, e.created_at DESC""",
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r[0], "patient_id": r[1], "patient_name": r[2],
                "reason": r[3], "risk_level": r[4],
                "details": json.loads(r[5]), "created_at": r[6],
                "assigned_to": r[7], "assigned_to_name": r[8],
                "acknowledged_at": r[9], "due_at": r[10],
                "notification_status": r[11],
            }
            for r in rows
        ]


@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int, request: Request):
    staff, now = request.state.staff, datetime.now().isoformat()
    async with db_store.connect() as db:
        cursor = await db.execute(
            "SELECT patient_id, acknowledged_at FROM escalations WHERE id=? AND resolved=0",
            (alert_id,),
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Open alert not found")
        await db.execute(
            """UPDATE escalations SET assigned_to=?, acknowledged_by=?,
                      acknowledged_at=COALESCE(acknowledged_at, ?)
               WHERE id=?""",
            (staff["id"], staff["id"], now, alert_id),
        )
        await record_audit(db, staff, "escalation.acknowledged", "escalation", alert_id)
        await db.commit()
        patient = await get_patient_full(row[0], db)
    event = {
        "type": "alert_acknowledged", "alert_id": alert_id, "patient_id": row[0],
        "assigned_to": staff["id"], "assigned_to_name": staff["name"],
        "acknowledged_at": row[1] or now, "patient": patient,
    }
    await manager.broadcast_all(event)
    return event


@app.post("/api/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: int, body: ResolveAlertRequest, request: Request):
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
        resolved_by = request.state.staff["name"]
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
        await record_audit(
            db, request.state.staff, "escalation.resolved", "escalation", alert_id,
            {"resolution_code": body.resolution_code, "patient_id": patient_id},
        )
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


@app.get("/api/worklist/today")
async def today_worklist(request: Request):
    """One operational queue: urgent cases, due follow-ups and failed delivery."""
    staff = request.state.staff
    today = date.today().isoformat()
    now = datetime.now().isoformat()
    async with db_store.connect() as db:
        alert_cursor = await db.execute(
            """SELECT e.id, e.patient_id, p.name, e.reason, e.risk_level, e.created_at,
                      e.acknowledged_at, e.assigned_to, owner.name, e.due_at, e.details,
                      e.notification_status
               FROM escalations e JOIN patients p ON p.id=e.patient_id
               LEFT JOIN staff_users owner ON owner.id=e.assigned_to
               WHERE e.resolved=0
               ORDER BY CASE WHEN e.assigned_to=? THEN 0 WHEN e.assigned_to IS NULL THEN 1 ELSE 2 END,
                        CASE e.risk_level WHEN 'red' THEN 0 ELSE 1 END, e.created_at""",
            (staff["id"],),
        )
        appointment_cursor = await db.execute(
            """SELECT a.id, a.patient_id, p.name, a.appointment_time, a.clinician_name,
                      a.visit_type, a.status
               FROM appointments a JOIN patients p ON p.id=a.patient_id
               WHERE a.appointment_date=? AND a.status='confirmed' ORDER BY a.appointment_time""",
            (today,),
        )
        failure_cursor = await db.execute(
            """SELECT m.id, m.patient_id, p.name, m.body, m.delivery_error, m.created_at
               FROM messages m JOIN patients p ON p.id=m.patient_id
               WHERE m.direction='outbound' AND m.delivery_status='failed'
                 AND m.created_at>=? ORDER BY m.created_at DESC LIMIT 25""",
            ((datetime.now() - timedelta(days=7)).isoformat(),),
        )
        due_cursor = await db.execute(
            """SELECT p.id, p.name, p.reminder_time FROM patients p
               LEFT JOIN reminder_dispatches d ON d.patient_id=p.id
                 AND d.reminder_kind='medication' AND d.dispatch_date=?
               WHERE p.status='active' AND p.category='chronic' AND p.consent_status='granted'
                 AND p.communication_opt_in=1 AND p.paused=0 AND p.reminder_time<=?
                 AND (d.id IS NULL OR d.status='failed')
               ORDER BY p.reminder_time, p.name""",
            (today, datetime.now().strftime("%H:%M")),
        )
        alerts = [
            {"id": r[0], "patient_id": r[1], "patient_name": r[2], "reason": r[3],
             "risk_level": r[4], "created_at": r[5], "acknowledged_at": r[6],
             "assigned_to": r[7], "assigned_to_name": r[8], "due_at": r[9],
             "details": json.loads(r[10]), "notification_status": r[11],
             "overdue": bool(r[9] and r[9] < now)}
            for r in await alert_cursor.fetchall()
        ]
        appointments_today = [
            {"id": r[0], "patient_id": r[1], "patient_name": r[2], "appointment_time": r[3],
             "clinician_name": r[4], "visit_type": r[5], "status": r[6]}
            for r in await appointment_cursor.fetchall()
        ]
        failed = [
            {"id": r[0], "patient_id": r[1], "patient_name": r[2], "body": r[3],
             "delivery_error": r[4], "created_at": r[5]}
            for r in await failure_cursor.fetchall()
        ]
        reminders_due = [
            {"patient_id": r[0], "patient_name": r[1], "reminder_time": r[2]}
            for r in await due_cursor.fetchall()
        ]
    return {
        "date": today, "alerts": alerts, "appointments": appointments_today,
        "failed_deliveries": failed, "reminders_due": reminders_due,
        "counts": {"open_alerts": len(alerts),
                   "unacknowledged": sum(1 for item in alerts if not item["acknowledged_at"]),
                   "appointments": len(appointments_today), "failed_deliveries": len(failed),
                   "reminders_due": len(reminders_due)},
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
    async with db_store.connect() as db:
        session = await auth.get_session(db, websocket.cookies.get(auth.COOKIE_NAME, ""))
    if not session:
        await websocket.close(code=4401)
        return
    await manager.connect(patient_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(patient_id, websocket)


@app.websocket("/ws/global")
async def websocket_global(websocket: WebSocket):
    async with db_store.connect() as db:
        session = await auth.get_session(db, websocket.cookies.get(auth.COOKIE_NAME, ""))
    if not session:
        await websocket.close(code=4401)
        return
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
    database_reachable = False
    if not DB_ERROR:
        try:
            async with db_store.connect() as db:
                database_reachable = bool(await (await db.execute("SELECT 1")).fetchone())
        except Exception:
            database_reachable = False
    return {
        "status": "degraded" if DB_ERROR or missing_production_config() or not database_reachable else "ok",
        "service": "VeloxaCare API",
        "environment": environment(),
        "demo_enabled": demo_tools_enabled(),
        "missing_production_config": missing_production_config(),
        "whatsapp_configured": whatsapp.is_configured(),
        "whatsapp_welcome_template_configured": bool(os.getenv("META_WELCOME_TEMPLATE", "").strip()),
        "stt_providers": stt.configured_providers(),
        "webhook": "/webhook/whatsapp",
        # Which store is in use, and why it isn't working if it isn't. Without
        # this a storage misconfiguration is invisible until a query fails.
        "database": (
            "supabase-postgres" if db_store.postgres_configured()
            else "turso" if db_store.turso_configured()
            else f"sqlite:{DB_PATH}"
        ),
        "database_reachable": database_reachable,
        "database_error": bool(DB_ERROR),
        "database_error_detail": DB_ERROR if DB_ERROR and not production_like() else None,
    }


# ── Serve frontend ────────────────────────────────────────────────────────────

# Mounted last: StaticFiles at "/" swallows every unmatched path, so it must not
# shadow the API routes above. Only present after `npm run build`; in dev the
# dashboard is served by Vite on :5173 instead.
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")
