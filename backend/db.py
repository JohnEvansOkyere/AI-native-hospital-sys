import aiosqlite
import base64
import httpx
import json
import os
import re
from datetime import datetime, timedelta, date
from typing import Union
import random

# Local dev writes a file next to the app. On a serverless host the bundle is
# read-only, so fall back to the one writable location — but see connect():
# /tmp is per-instance and wiped on cold start, so it is a demo path only.
# Anything resembling a real deployment sets TURSO_DATABASE_URL.
DB_PATH = os.getenv("DB_PATH") or ("/tmp/veloxacare.db" if os.getenv("VERCEL") else "veloxacare.db")


def turso_configured() -> bool:
    return bool(os.getenv("TURSO_DATABASE_URL"))


def connect():
    """Open a database connection.

    Returns an async context manager exposing the aiosqlite surface this app
    uses (execute / fetchone / fetchall / lastrowid / commit), backed either by
    a local SQLite file or by Turso over HTTP. Every call site uses this rather
    than aiosqlite directly, so the storage swap stays in one place.
    """
    if turso_configured():
        return _TursoConnection()
    return aiosqlite.connect(DB_PATH)


# Both backends satisfy the same small interface, so anything that receives an
# open connection is annotated with this rather than with a concrete class.
Connection = Union[aiosqlite.Connection, "_TursoConnection"]


def turso_http_url(url: str) -> str:
    """Turn the URL Turso gives you into the one its HTTP API lives on.

    `turso db show --url` prints a `libsql://` URL. The Hrana-over-HTTP endpoint
    is the same host over https, so normalise the scheme rather than making
    every deployment remember to rewrite it. Whitespace is stripped because a
    newline pasted into a dashboard silently corrupts the host.
    """
    url = (url or "").strip().rstrip("/")
    for scheme in ("libsql://", "wss://", "ws://"):
        if url.startswith(scheme):
            return "https://" + url[len(scheme):]
    return url


def split_sql(script: str) -> list[str]:
    """Split a multi-statement script into individual statements.

    Line comments are removed *before* splitting: a `--` comment may itself
    contain a semicolon, and splitting on that would tear one statement into
    two invalid fragments. (SCHEMA below has exactly such a comment.)
    """
    without_comments = re.sub(r"--[^\n]*", "", script)
    return [s.strip() for s in without_comments.split(";") if s.strip()]


def _to_arg(value):
    """Encode a Python value as a Hrana typed argument."""
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "integer", "value": str(int(value))}
    if isinstance(value, int):
        # Hrana carries 64-bit integers as strings to survive JSON.
        return {"type": "integer", "value": str(value)}
    if isinstance(value, float):
        return {"type": "float", "value": value}
    if isinstance(value, (bytes, bytearray)):
        return {"type": "blob", "value": base64.b64encode(bytes(value)).decode()}
    return {"type": "text", "value": str(value)}


def _from_value(value):
    """Decode a Hrana typed value back into Python."""
    kind = value.get("type")
    if kind == "null":
        return None
    if kind == "integer":
        return int(value["value"])
    if kind == "float":
        return float(value["value"])
    if kind == "blob":
        return base64.b64decode(value["value"])
    return value.get("value")


class _TursoCursor:
    """Mimics the slice of aiosqlite.Cursor this codebase touches."""

    def __init__(self, rows, lastrowid, columns=None):
        self._rows = rows
        self.lastrowid = lastrowid
        # aiosqlite exposes DB-API cursor.description. get_patient_full() uses
        # it to turn SELECT * into a named record, so the Turso adapter must do
        # the same rather than returning an anonymous tuple list.
        self.description = [
            (column.get("name", ""), None, None, None, None, None, None)
            for column in (columns or [])
        ]

    async def fetchone(self):
        return self._rows[0] if self._rows else None

    async def fetchall(self):
        return self._rows


class _TursoConnection:
    """aiosqlite-shaped adapter over Turso's Hrana-over-HTTP API.

    Talks to /v2/pipeline directly instead of using libsql-client, whose HTTP
    transport still posts to the retired `v1/execute` endpoint and fails against
    current Turso with a bare KeyError. Plain HTTP also suits a serverless host
    better than the alternative WebSocket transport: no connection to hold open
    across an invocation that may be frozen at any moment.

    Turso speaks SQLite dialect, so every query in this app is unchanged.
    Statements autocommit, which is why commit() is a no-op.
    """

    def __init__(self):
        self._client = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=turso_http_url(os.getenv("TURSO_DATABASE_URL")),
            headers={"Authorization": f"Bearer {(os.getenv('TURSO_AUTH_TOKEN') or '').strip()}"},
            timeout=30,
        )
        return self

    async def __aexit__(self, *exc):
        if self._client is not None:
            await self._client.aclose()
        return False

    async def _pipeline(self, statements: list[dict]) -> list[dict]:
        """Send statements as one pipeline and return their results in order."""
        requests = [{"type": "execute", "stmt": s} for s in statements]
        requests.append({"type": "close"})

        response = await self._client.post("/v2/pipeline", json={"requests": requests})
        if response.status_code != 200:
            # Turso reports a rejected credential as 400/401 with a JSON body;
            # surfacing it verbatim is what makes a misconfiguration diagnosable.
            raise RuntimeError(
                f"Turso HTTP {response.status_code}: {response.text[:200]}"
            )

        results = []
        for item in response.json().get("results", []):
            if item.get("type") == "error":
                message = (item.get("error") or {}).get("message", "unknown error")
                raise RuntimeError(f"Turso: {message}")
            inner = item.get("response") or {}
            if inner.get("type") == "execute":
                results.append(inner.get("result", {}))
        return results

    async def execute(self, sql: str, params=()):
        stmt = {"sql": sql, "args": [_to_arg(p) for p in params]}
        result = (await self._pipeline([stmt]))[0]
        rows = [
            tuple(_from_value(cell) for cell in row)
            for row in result.get("rows", [])
        ]
        rowid = result.get("last_insert_rowid")
        return _TursoCursor(
            rows,
            int(rowid) if rowid is not None else None,
            result.get("cols", []),
        )

    async def executescript(self, script: str):
        statements = [{"sql": s, "args": []} for s in split_sql(script)]
        if statements:
            await self._pipeline(statements)

    async def commit(self):
        """No-op — each statement autocommits."""
        return None

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT UNIQUE NOT NULL,
    age INTEGER,
    condition TEXT NOT NULL,
    drug_name TEXT NOT NULL,
    drug_dosage TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'chronic',
    service_type TEXT DEFAULT '',
    care_instructions TEXT DEFAULT '',
    next_follow_up TEXT DEFAULT '',
    recall_date TEXT DEFAULT '',
    reminder_time TEXT NOT NULL DEFAULT '08:00',
    enrolled_at TEXT NOT NULL,
    doctor_name TEXT DEFAULT 'Dr. Mensah',
    status TEXT DEFAULT 'active',
    risk_level TEXT DEFAULT 'green'
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    direction TEXT NOT NULL,
    body TEXT NOT NULL,
    reason TEXT,
    created_at TEXT NOT NULL,
    -- Which transport this message arrived on / went out over.
    -- 'simulator' is the built-in WhatsApp pane; real channels are named directly.
    channel TEXT DEFAULT 'simulator',
    -- Voice notes: body holds the transcript, these record how we got it.
    -- On an outbound message audio_file is the spoken reply instead, and the
    -- tts_* columns say which voice said it. One column either way: audio_file
    -- is always "the audio for this message", whichever direction it travelled.
    audio_file TEXT DEFAULT '',
    stt_provider TEXT DEFAULT '',
    stt_language TEXT DEFAULT '',
    stt_latency_ms INTEGER DEFAULT 0,
    tts_provider TEXT DEFAULT '',
    tts_voice TEXT DEFAULT '',
    tts_latency_ms INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS adherence_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    log_date TEXT NOT NULL,
    response TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS checkin_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    reading_type TEXT NOT NULL,
    reading_value TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    ai_note TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversation_state (
    patient_id INTEGER PRIMARY KEY REFERENCES patients(id),
    current_flow TEXT DEFAULT 'idle',
    context TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS escalations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    reason TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    details TEXT NOT NULL,
    resolved INTEGER DEFAULT 0,
    resolution_code TEXT DEFAULT '',
    resolution_note TEXT DEFAULT '',
    resolved_by TEXT DEFAULT '',
    resolved_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS care_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    log_date TEXT NOT NULL,
    activity TEXT NOT NULL,
    response TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    appointment_date TEXT NOT NULL,
    appointment_time TEXT NOT NULL,
    clinician_name TEXT NOT NULL,
    visit_type TEXT NOT NULL DEFAULT 'Clinic consultation',
    status TEXT NOT NULL DEFAULT 'confirmed',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_appointments_confirmed_slot
ON appointments(clinician_name, appointment_date, appointment_time)
WHERE status='confirmed';

CREATE INDEX IF NOT EXISTS idx_appointments_patient_date
ON appointments(patient_id, appointment_date, appointment_time);
"""

SEED_PATIENTS = [
    {
        "name": "Abena Owusu",
        "phone": "+233241000001",
        "age": 52,
        "condition": "hypertension",
        "drug_name": "Amlodipine",
        "drug_dosage": "5mg once daily",
        "doctor_name": "Dr. Ama Boateng",
        "risk_level": "green",
    },
    {
        "name": "Kofi Mensah",
        "phone": "+233241000002",
        "age": 61,
        "condition": "hypertension",
        "drug_name": "Lisinopril",
        "drug_dosage": "10mg once daily",
        "doctor_name": "Dr. Ama Boateng",
        "risk_level": "red",
    },
    {
        "name": "Akosua Darko",
        "phone": "+233241000003",
        "age": 48,
        "condition": "hypertension",
        "drug_name": "Amlodipine + Hydrochlorothiazide",
        "drug_dosage": "5mg + 25mg once daily",
        "doctor_name": "Dr. Kwesi Asante",
        "risk_level": "amber",
    },
    {
        "name": "Kwame Asante",
        "phone": "+233241000004",
        "age": 55,
        "condition": "hypertension",
        "drug_name": "Lisinopril",
        "drug_dosage": "5mg once daily",
        "doctor_name": "Dr. Kwesi Asante",
        "risk_level": "red",
    },
    {
        "name": "Ama Boateng",
        "phone": "+233241000005",
        "age": 44,
        "condition": "hypertension",
        "drug_name": "Amlodipine",
        "drug_dosage": "10mg once daily",
        "doctor_name": "Dr. Ama Boateng",
        "risk_level": "amber",
    },
    {
        "name": "Kwesi Acheampong",
        "phone": "+233241000006",
        "age": 67,
        "condition": "hypertension",
        "drug_name": "Lisinopril + Amlodipine",
        "drug_dosage": "10mg + 5mg once daily",
        "doctor_name": "Dr. Kwesi Asante",
        "risk_level": "green",
    },
]

# Adherence patterns: list of responses for last 14 days (index 0 = 14 days ago)
ADHERENCE_PATTERNS = {
    "+233241000001": ["yes","yes","yes","yes","yes","no","yes","yes","yes","yes","yes","yes","yes","yes"],
    "+233241000002": ["yes","no","no","cost","no","no","cost","no","yes","no","no","cost","no","no"],
    "+233241000003": ["yes","yes","no","yes","no","yes","yes","no","no","yes","yes","no","yes","no"],
    "+233241000004": ["yes","yes","yes","yes","yes","yes","yes","yes","yes","yes","yes","yes","yes","yes"],
    "+233241000005": ["yes","yes","no","yes","yes"],
    "+233241000006": ["yes","yes","yes","yes","yes","yes","yes","no","yes","yes","yes","yes","yes","yes"],
}

SEED_MESSAGES = {
    "+233241000001": [
        (-13, "outbound", "Good morning Abena! ☀️ Time for your Amlodipine 5mg. Reply YES when done, NO if you missed it.", None),
        (-13, "inbound", "Yes done!", None),
        (-13, "outbound", "Great job! ✅ Staying consistent keeps your blood pressure stable. Keep it up!", None),
        (-12, "outbound", "Good morning Abena! ☀️ Time for your Amlodipine 5mg. Reply YES when done.", None),
        (-12, "inbound", "Yes", None),
        (-12, "outbound", "✅ Logged! You're on a 2-day streak.", None),
        (-7, "outbound", "Weekly check-in time, Abena. 📋 What was your blood pressure reading this week? (e.g. 128/82)", None),
        (-7, "inbound", "128/82", None),
        (-7, "outbound", "Excellent! 128/82 is right in your target range. Your doctor will be happy to see this. 🎉", None),
        (-6, "outbound", "Good morning Abena! ☀️ Time for your Amlodipine 5mg.", None),
        (-6, "inbound", "Took it, thank you!", None),
        (-6, "outbound", "✅ Perfect! 8-day streak — your consistency is making a real difference.", None),
        (-1, "outbound", "Good morning Abena! ☀️ Time for your Amlodipine 5mg.", None),
        (-1, "inbound", "YES", None),
        (-1, "outbound", "✅ Logged! You have an appointment with Dr. Ama Boateng in 3 days. She'll be proud of your progress!", None),
    ],
    "+233241000002": [
        (-13, "outbound", "Good morning Kofi! ☀️ Time for your Lisinopril 10mg. Reply YES when done.", None),
        (-13, "inbound", "Yes", None),
        (-13, "outbound", "✅ Logged! Keep it up, Kofi.", None),
        (-11, "outbound", "Good morning Kofi! ☀️ Time for your Lisinopril 10mg.", None),
        (-11, "inbound", "I haven't been able to buy it. The pharmacy said it's out of stock and the other one is too expensive.", "cost"),
        (-11, "outbound", "I understand, Kofi. 🏥 I've flagged this for your nurse immediately — they will call you today about an NHIS-covered alternative that works just as well. Please don't stop your treatment.", None),
        (-8, "outbound", "Good morning Kofi! ☀️ Time for your Lisinopril 10mg.", None),
        (-8, "inbound", "Still can't afford it this week", "cost"),
        (-8, "outbound", "Cost barrier flagged again, Kofi. 🚨 Your nurse has been alerted. We are working on a solution for you. Please hang in there — your health matters.", None),
        (-5, "outbound", "Good morning Kofi! ☀️ Time for your Lisinopril 10mg.", None),
        (-5, "inbound", "No", "cost"),
        (-5, "outbound", "⚠️ Kofi, missing your medication is putting your heart at risk. I've escalated this to Dr. Ama Boateng. Someone will reach out to you today.", None),
        (-2, "outbound", "Good morning Kofi! ☀️ Time for your Lisinopril 10mg.", None),
        (-2, "inbound", "No still no money", "cost"),
        (-2, "outbound", "Flagged to your care team. 🏥 Please visit the clinic if you feel dizzy or have a headache.", None),
    ],
    "+233241000003": [
        (-13, "outbound", "Good morning Akosua! ☀️ Time for your Amlodipine + Hydrochlorothiazide. Reply YES when done.", None),
        (-13, "inbound", "Yes taken", None),
        (-13, "outbound", "✅ Great! Both medications working together keep your pressure balanced.", None),
        (-10, "outbound", "Good morning Akosua! ☀️ Time for your medications.", None),
        (-10, "inbound", "I forgot yesterday", "forgot"),
        (-10, "outbound", "No worries! Take today's dose now. Try leaving your pills next to your morning tea so you don't forget again. 😊", None),
        (-7, "outbound", "Weekly check-in, Akosua. 📋 What was your blood pressure reading this week?", None),
        (-7, "inbound", "148/95", None),
        (-7, "outbound", "⚠️ 148/95 is a bit above your target (below 140/90). This may be linked to the missed doses. Let's get back on track — I've noted this for Dr. Kwesi.", None),
        (-4, "outbound", "Good morning Akosua! ☀️ Time for your medications.", None),
        (-4, "inbound", "Yes done both", None),
        (-4, "outbound", "✅ Both medications logged. Excellent — consistency over the next week will bring that reading down.", None),
        (-1, "outbound", "Good morning Akosua! ☀️ Time for your medications.", None),
        (-1, "inbound", "Yes", None),
        (-1, "outbound", "✅ Logged! Keep going — you're getting back on track 💪", None),
    ],
    "+233241000004": [
        (-13, "outbound", "Good morning Kwame! ☀️ Time for your Lisinopril 5mg.", None),
        (-13, "inbound", "Done", None),
        (-13, "outbound", "✅ Excellent consistency, Kwame!", None),
        (-7, "outbound", "Weekly check-in, Kwame. 📋 What was your blood pressure this week?", None),
        (-7, "inbound", "It was high. 168/102", None),
        (-7, "outbound", "⚠️ 168/102 is significantly above your target. I'm alerting Dr. Kwesi Asante now. 🚨 Please avoid salty food, rest, and come to the clinic if you have a headache or chest tightness.", None),
        (-5, "outbound", "Good morning Kwame! ☀️ Time for your Lisinopril 5mg.", None),
        (-5, "inbound", "Yes done", None),
        (-5, "outbound", "✅ Good. Dr. Kwesi will want to see you this week because of that reading. Please book an appointment.", None),
        (-2, "outbound", "Good morning Kwame! ☀️ Time for your Lisinopril 5mg.", None),
        (-2, "inbound", "Yes", None),
        (-2, "outbound", "✅ Logged. Your appointment is important — please don't miss it.", None),
    ],
    "+233241000005": [
        (-5, "outbound", "Welcome to VeloxaCare, Ama! 👋 I'm your health assistant. I'll remind you to take your Amlodipine 10mg daily and check in on how you're doing. Reply START to begin.", None),
        (-5, "inbound", "Start", None),
        (-5, "outbound", "Welcome! ✅ Your first reminder will come tomorrow morning at 8am. You're in good hands.", None),
        (-4, "outbound", "Good morning Ama! ☀️ Time for your Amlodipine 10mg. Reply YES when done.", None),
        (-4, "inbound", "Yes thank you", None),
        (-4, "outbound", "✅ Day 1 done! Great start.", None),
        (-3, "outbound", "Good morning Ama! ☀️ Time for your Amlodipine 10mg.", None),
        (-3, "inbound", "Yes", None),
        (-3, "outbound", "✅ Day 2! You're building a great habit.", None),
        (-2, "outbound", "Good morning Ama! ☀️ Time for your Amlodipine 10mg.", None),
        (-2, "inbound", "I was at work and forgot", "forgot"),
        (-2, "outbound", "No worries — this happens! Try setting an 8am alarm on your phone as backup. Take it now if it's been less than 6 hours. See you tomorrow! 😊", None),
        (-1, "outbound", "Good morning Ama! ☀️ Time for your Amlodipine 10mg.", None),
        (-1, "inbound", "Yes done!", None),
        (-1, "outbound", "✅ Back on track! You're doing well for a new patient.", None),
    ],
    "+233241000006": [
        (-13, "outbound", "Good morning Kwesi! ☀️ Time for your Lisinopril 10mg + Amlodipine 5mg.", None),
        (-13, "inbound", "Yes, taken both", None),
        (-13, "outbound", "✅ Perfect! Both medications logged.", None),
        (-7, "outbound", "Weekly check-in, Kwesi. 📋 Blood pressure reading this week?", None),
        (-7, "inbound", "126/80", None),
        (-7, "outbound", "🎉 126/80 — that's excellent! Right in the ideal range. Your dedication to your medications is clearly working.", None),
        (-5, "outbound", "Good morning Kwesi! ☀️ Time for your medications.", None),
        (-5, "inbound", "Done! Also feeling much better lately", None),
        (-5, "outbound", "Wonderful to hear! ✅ Logged. Your appointment with Dr. Kwesi Asante is in 2 days — keep it up!", None),
        (-2, "outbound", "Reminder: Your appointment with Dr. Kwesi Asante is tomorrow at 10:00 AM at Accra Family Clinic. Reply CONFIRM or RESCHEDULE.", None),
        (-2, "inbound", "Confirmed, I'll be there", None),
        (-2, "outbound", "✅ See you tomorrow, Kwesi! Come with your medication list.", None),
        (-1, "outbound", "Good morning Kwesi! ☀️ Time for your medications.", None),
        (-1, "inbound", "Yes", None),
        (-1, "outbound", "✅ 13-day streak! Your consistency is outstanding, Kwesi. 🏆", None),
    ],
}

SEED_ESCALATIONS = [
    {
        "phone": "+233241000002",
        "reason": "Cost barrier — unable to afford medication for 9+ days",
        "risk_level": "red",
        "details": json.dumps({
            "missed_days": 9,
            "reason": "cost",
            "last_message": "No still no money",
            "action": "Nurse and doctor alerted. NHIS-covered alternative to be arranged."
        }),
        "days_ago": 2,
        "resolved": 0,
    },
    {
        "phone": "+233241000004",
        "reason": "Dangerously high BP reading: 168/102",
        "risk_level": "red",
        "details": json.dumps({
            "reading": "168/102",
            "target": "below 140/90",
            "action": "Doctor alerted. Urgent appointment recommended.",
            "last_message": "It was high. 168/102"
        }),
        "days_ago": 7,
        "resolved": 0,
    },
    {
        "phone": "+233241000003",
        "reason": "Elevated BP reading: 148/95 — above target",
        "risk_level": "amber",
        "details": json.dumps({
            "reading": "148/95",
            "target": "below 140/90",
            "action": "Noted for doctor review at next appointment.",
            "context": "Linked to missed doses."
        }),
        "days_ago": 7,
        "resolved": 0,
    },
]


async def get_db():
    return await connect()


async def init_db():
    async with connect() as db:
        await db.executescript(SCHEMA)

        # Keep existing demo databases usable when the category-aware schema is
        # introduced after the original hypertension-only version was run.
        existing_columns = {
            row[1] for row in await (await db.execute("PRAGMA table_info(patients)")).fetchall()
        }
        new_columns = {
            "category": "TEXT NOT NULL DEFAULT 'chronic'",
            "service_type": "TEXT DEFAULT ''",
            "care_instructions": "TEXT DEFAULT ''",
            "next_follow_up": "TEXT DEFAULT ''",
            "recall_date": "TEXT DEFAULT ''",
        }
        for column, definition in new_columns.items():
            if column not in existing_columns:
                await db.execute(f"ALTER TABLE patients ADD COLUMN {column} {definition}")
        await db.execute("UPDATE patients SET category='chronic' WHERE category IS NULL OR category='' ")

        # Same treatment for voice-note columns on messages, so a demo DB
        # created before the voice pipeline keeps working.
        existing_message_columns = {
            row[1] for row in await (await db.execute("PRAGMA table_info(messages)")).fetchall()
        }
        new_message_columns = {
            "channel": "TEXT DEFAULT 'simulator'",
            "audio_file": "TEXT DEFAULT ''",
            "stt_provider": "TEXT DEFAULT ''",
            "stt_language": "TEXT DEFAULT ''",
            "stt_latency_ms": "INTEGER DEFAULT 0",
            "tts_provider": "TEXT DEFAULT ''",
            "tts_voice": "TEXT DEFAULT ''",
            "tts_latency_ms": "INTEGER DEFAULT 0",
        }
        for column, definition in new_message_columns.items():
            if column not in existing_message_columns:
                await db.execute(f"ALTER TABLE messages ADD COLUMN {column} {definition}")

        # An escalation is only useful when the care team can record what was
        # done. These fields close the audit loop while keeping old demo and
        # production databases intact through additive migrations.
        existing_escalation_columns = {
            row[1] for row in await (await db.execute("PRAGMA table_info(escalations)")).fetchall()
        }
        new_escalation_columns = {
            "resolution_code": "TEXT DEFAULT ''",
            "resolution_note": "TEXT DEFAULT ''",
            "resolved_by": "TEXT DEFAULT ''",
            "resolved_at": "TEXT",
        }
        for column, definition in new_escalation_columns.items():
            if column not in existing_escalation_columns:
                await db.execute(f"ALTER TABLE escalations ADD COLUMN {column} {definition}")
        await db.commit()

        cursor = await db.execute("SELECT COUNT(*) FROM patients")
        row = await cursor.fetchone()
        if row[0] > 0:
            return

        today = date.today()

        for p in SEED_PATIENTS:
            enrolled = today - timedelta(days=14)
            if p["phone"] == "+233241000005":
                enrolled = today - timedelta(days=5)
            await db.execute(
                """INSERT INTO patients (name, phone, age, condition, drug_name, drug_dosage,
                   category, service_type, care_instructions, next_follow_up, recall_date,
                   enrolled_at, doctor_name, risk_level) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (p["name"], p["phone"], p["age"], p["condition"],
                 p["drug_name"], p["drug_dosage"], p.get("category", "chronic"),
                 p.get("service_type", "Hypertension follow-up"), p.get("care_instructions", ""),
                 p.get("next_follow_up", ""), p.get("recall_date", ""), enrolled.isoformat(),
                 p["doctor_name"], p["risk_level"]),
            )

        await db.commit()

        cursor = await db.execute("SELECT id, phone FROM patients")
        patients = await cursor.fetchall()
        phone_to_id = {row[1]: row[0] for row in patients}

        for phone, pattern in ADHERENCE_PATTERNS.items():
            pid = phone_to_id.get(phone)
            if not pid:
                continue
            days_back = len(pattern)
            for i, resp in enumerate(pattern):
                log_date = today - timedelta(days=days_back - i)
                await db.execute(
                    "INSERT INTO adherence_logs (patient_id, log_date, response, created_at) VALUES (?,?,?,?)",
                    (pid, log_date.isoformat(), resp, log_date.isoformat()),
                )

        for phone, msgs in SEED_MESSAGES.items():
            pid = phone_to_id.get(phone)
            if not pid:
                continue
            for (days_offset, direction, body, reason) in msgs:
                ts = (today + timedelta(days=days_offset)).isoformat() + " 08:0" + str(random.randint(0, 9)) + ":00"
                await db.execute(
                    "INSERT INTO messages (patient_id, direction, body, reason, created_at) VALUES (?,?,?,?,?)",
                    (pid, direction, body, reason, ts),
                )

        for esc in SEED_ESCALATIONS:
            pid = phone_to_id.get(esc["phone"])
            if not pid:
                continue
            created = (today - timedelta(days=esc["days_ago"])).isoformat()
            await db.execute(
                "INSERT INTO escalations (patient_id, reason, risk_level, details, resolved, created_at) VALUES (?,?,?,?,?,?)",
                (pid, esc["reason"], esc["risk_level"], esc["details"], esc["resolved"], created),
            )

        for pid in phone_to_id.values():
            await db.execute(
                "INSERT OR IGNORE INTO conversation_state (patient_id, current_flow, context) VALUES (?, 'idle', '{}')",
                (pid,),
            )

        await db.commit()
