# VeloxaCare — Architecture & Production Guide

This document covers the system design as built (demo) and the exact path to a
production deployment on real WhatsApp with a real database.

---

## 1. System overview

VeloxaCare keeps chronic-disease patients on their medication after they leave the
clinic, and surfaces the ones who are slipping — *and why* — to the care team.

```
   Patient (WhatsApp)
        │  message
        ▼
 ┌──────────────────┐      ┌──────────────┐
 │  Transport layer │◄────►│   Meta Cloud │   (prod)
 │  (simulator now, │      │     API      │
 │   Meta later)    │      └──────────────┘
 └────────┬─────────┘
          │ inbound text
          ▼
 ┌──────────────────────────────────────────┐
 │  FastAPI (backend/main.py)                    │
 │   • routes + WebSocket manager            │
 │   • process_message() ── the brain ───────┼──► services/bot.py
 │                                           │      • flow routing
 │                                           │      • adherence / check-in logging
 │                                           │      • escalation rules
 └───────┬───────────────────────┬──────────┘
         │                        │
         ▼                        ▼
 ┌──────────────┐        ┌──────────────────┐
 │  Database    │        │  Claude (ai.py)  │
 │  SQLite now  │        │  • reason detect │
 │  Supabase/PG │        │    (Haiku)       │
 │  in prod     │        │  • weekly report │
 └──────────────┘        │    (Sonnet)      │
         │               │  • BP risk =     │
         ▼               │    RULE-BASED    │
 ┌──────────────┐        └──────────────────┘
 │  Dashboard   │  ◄── WebSocket live updates
 │  (React)     │
 └──────────────┘
```

### Design principles

1. **Transport-agnostic core.** All conversation logic lives in `bot.process_message()`
   and never touches the transport. Swapping the in-app simulator for Meta Cloud API is
   an adapter change, not a rewrite.
2. **Graceful degradation.** Missing API key or no network → rule-based fallbacks.
   The system never hard-fails. (Critical for live demos and for low-connectivity ops.)
3. **Human-in-the-loop safety.** The LLM classifies and summarizes; it never makes
   clinical decisions. All red-flag thresholds are deterministic rules.
4. **Reason-aware, not just adherence.** Every "no" is classified and routed. Cost is
   the dominant failure mode in Ghana and gets its own escalation + NHIS path.

---

## 2. Data model

SQLite tables (see [backend/db.py](../backend/db.py)). Maps 1:1 to Postgres/Supabase for prod.

| Table | Purpose |
|---|---|
| `patients` | Profile, condition, drug, assigned doctor, current `risk_level` |
| `messages` | Full WhatsApp transcript (inbound/outbound, optional `reason` tag) |
| `adherence_logs` | One row per day per patient: `yes` / `cost` / `forgot` / … |
| `checkin_logs` | BP (or other) readings with computed `risk_level` + AI note |
| `conversation_state` | Per-patient flow pointer (`idle` / `awaiting_medication_ack` / `awaiting_bp`) |
| `escalations` | Care-team alerts with reason, risk, JSON details, resolved flag |

**Enums (keep consistent across DB / API / UI):**
- `risk_level`: `green` | `amber` | `red`
- adherence `response` / reason: `yes` | `cost` | `forgot` | `side_effect` | `ran_out` | `no` | `no_response`

---

## 3. Conversation engine (`services/bot.py`)

`process_message(patient_id, message, db)` is the heart. It:

1. Loads patient + `conversation_state` + recent adherence (for streak).
2. Routes on `current_flow`:
   - **enrollment** (`start`/`hi`) → welcome + enroll.
   - **`awaiting_medication_ack`** → if YES, log adherence + reinforce (streak-aware);
     if NO, detect reason → log → reply → escalate if needed.
   - **`awaiting_bp`** → parse `NNN/NN`, assess risk (rule-based), log, escalate.
   - **`idle`** → best-effort: detect BP reading, YES, or NO+reason from free text.
3. Updates `conversation_state` and commits.
4. Returns `(reply, reason, escalation_created)` to the route, which logs the outbound
   message and broadcasts over WebSocket.

**Reminder/check-in triggers** (`trigger_medication_reminder`, `trigger_bp_checkin`)
set the flow to the awaiting state and return the outbound text. In the demo these are
fired by the Bell/Activity buttons; in production they are fired by a scheduler
(see §6).

### Escalation rules (safety-critical — keep deterministic)

- **High BP:** `≥160 systolic or ≥100 diastolic` → `red`, immediate escalation.
  `≥140/90` → `amber`. Else `green`. (`ai.py:assess_bp_risk`)
- **Cost / side-effect:** `amber` on first occurrence; `red` + escalation on the
  **2nd within 14 days**. (`bot.py`)
- **Streak ≥ 7 days** of `yes` pulls risk back toward `green`.

---

## 4. AI layer (`services/ai.py`)

| Function | Model | Job | Fallback |
|---|---|---|---|
| `detect_reason_ai` | `claude-haiku-4-5` | Classify why a dose was missed → one reason code | keyword rules (`detect_reason_rule`) |
| `generate_bot_reply` | `claude-haiku-4-5` | Warm free-text reply for unclear "no" cases | templated responses |
| `generate_weekly_report` | `claude-sonnet-4-6` | Doctor-ready markdown clinic report | templated summary |
| `assess_bp_risk` | **none (rules)** | BP → risk + patient message | n/a — always rules |

**Why these models:** Haiku is cheap/fast for the high-volume classification path;
Sonnet produces the higher-stakes clinician report. BP risk is intentionally *never*
an LLM call. When upgrading models, keep Haiku-class for per-message work to control
cost at scale.

---

## 5. API surface (`backend/main.py`)

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/patients` | All active patients with computed adherence, streak, escalations |
| GET | `/api/patients/{id}` | One patient, full detail |
| POST | `/api/patients` | Enroll (sends welcome message) |
| GET | `/api/patients/{id}/messages` | Transcript |
| POST | `/api/patients/{id}/messages` | **Inbound message → bot reply** (core loop) |
| POST | `/api/patients/{id}/remind` | Fire medication reminder |
| POST | `/api/patients/{id}/checkin` | Fire weekly BP check-in |
| GET | `/api/alerts` | Open escalations across all patients |
| POST | `/api/alerts/{id}/resolve` | Resolve an alert |
| GET | `/api/reports/weekly` | Claude-generated weekly report |
| WS | `/ws/{patient_id}` | Per-patient live message stream |
| WS | `/ws/-1` | Global stream (enrollments, escalations, updates) |

---

## 6. Demo → Production checklist

The demo is real code. To make it a production pilot, work top-to-bottom.

### 6.1 WhatsApp (replace the simulator)

**You already have a Meta account — this is the main lift.**

1. **Meta setup**
   - Create a WhatsApp Business app in the Meta Developer Console.
   - Add + verify a phone number; get the **Phone Number ID** and a permanent
     **System User Access Token**.
   - Set a **webhook verify token** and point the webhook to your public HTTPS URL.
2. **Approve message templates** (required for outbound outside the 24h window):
   `medication_reminder`, `weekly_checkin_hypertension`, `appointment_reminder`,
   `enrollment_welcome`. Approval can take hours–days — start early.
3. **Add a transport adapter** — new module `api/services/whatsapp.py`:
   - `send_text(phone, body)` and `send_template(phone, template, params)` → POST to
     `https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages`.
   - Inbound webhook route `POST /webhook/whatsapp` that verifies the signature,
     extracts `{from, text}`, looks up the patient by phone, and calls the **existing**
     `process_message()` — then sends the reply via `send_text`.
   - A `GET /webhook/whatsapp` route that echoes `hub.challenge` for verification.
4. **Env vars:** `META_ACCESS_TOKEN`, `META_PHONE_NUMBER_ID`, `META_VERIFY_TOKEN`
   (already stubbed in `.env.example`).
5. Keep the simulator behind a `DEMO_MODE` flag so you can still demo offline.

> 24-hour window rule: free-form replies are only allowed within 24h of the patient's
> last message. All clinic-initiated messages (reminders, check-ins) **must** use an
> approved template. The bot's *replies* to a patient message are fine as free text.

### 6.2 Database (SQLite → Supabase/Postgres)

- Schema is portable; recreate the tables in Supabase (change `INTEGER PRIMARY KEY
  AUTOINCREMENT` → `bigint generated always as identity` or `uuid`).
- Swap `aiosqlite` for `asyncpg`/SQLAlchemy or the Supabase client. Centralize DB
  access (currently inline in `main.py`) behind a small repository module first to
  make this a one-place change.
- Enable Row-Level Security and per-clinic tenant isolation (see §6.4).

### 6.3 Scheduling (the cron that makes it autonomous)

The demo fires reminders/check-ins by hand. Production needs a scheduler:
- Add an async scheduler (APScheduler, or a separate worker) that:
  - hourly: send medication reminders to patients whose `reminder_time` matches;
  - mark non-responses after a timeout window → `no_response` + missed-streak check;
  - weekly (Mon AM): send check-ins;
  - 24h pre-appointment: send appointment reminders;
  - nightly: generate the pre-consultation report for next-day appointments.
- **n8n is a strong fit here** (your original plan): keep FastAPI as the brain/API and
  let n8n own the cron triggers, calling the FastAPI endpoints. Best of both.

### 6.4 Multi-tenant, auth & compliance

- **Clinic accounts + auth** for the dashboard (Supabase Auth or similar). Scope every
  query by `clinic_id`.
- **Roles:** nurse / doctor / admin. Escalations route to the on-duty nurse.
- **Patient consent + opt-out** ("STOP") handling — required by WhatsApp policy and
  good ethics.
- **Data protection:** Ghana's Data Protection Act (2012). Encrypt at rest, restrict
  access, keep an audit log of who viewed patient data.
- **Medical disclaimer** on all patient-facing flows; bot never diagnoses.

### 6.5 Deployment

- Containerize (Dockerfile for `api`, static build for `web`). `web` build is already
  served by FastAPI from `web/dist` if present.
- Host on your DigitalOcean droplet behind Caddy/Nginx with TLS (Meta requires HTTPS).
- Set `--workers` > 1 only after moving off SQLite (SQLite + multiple workers = lock
  contention). With Postgres this is safe.
- Add health checks, structured logging, and Sentry-style error tracking.

### 6.6 Observability & success metrics

Instrument the one number that sells the pilot: **% of patients still
refilling / in-care at day 60 vs. the clinic's baseline drop-off.** Also track
adherence rate, escalations raised vs. resolved, and cost-barrier interventions
(the pharmacy-revenue story).

---

## 7. Suggested build order for the pilot

1. Meta webhook + adapter (real WhatsApp on one test number).
2. Move DB access behind a repository module; migrate to Supabase.
3. Add the scheduler (or wire n8n) for autonomous reminders/check-ins.
4. Clinic auth + multi-tenant scoping.
5. Consent/opt-out + audit logging + disclaimers.
6. Deploy with TLS; run a single-clinic, hypertension-only, 60-day pilot.
7. Measure retention vs. baseline → case study → scale.
