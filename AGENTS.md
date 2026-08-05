# AGENTS.md

Guidance for coding agents working in this repository.

> **Keep [CLAUDE.md](CLAUDE.md) identical to this file.** Same guidance, two
> filenames, because different tools look for different names. If you change one,
> change the other in the same commit.

## What this is

**VeloxaCare** — a WhatsApp-based patient engagement platform for chronic disease
management in Ghana. Built as a *self-contained, demo-able system* that doubles as
the foundation for a real pilot. The current target condition is **hypertension**.

The core insight driving the product: in Ghana, the #1 reason patients stop taking
chronic medication is **cost (96% in one study), not forgetting**. So the bot does
not just track yes/no adherence — it detects *why* a patient slipped (cost / forgot /
side-effect / ran out) and routes each reason to a different action. Cost barriers
escalate to the care team and trigger an NHIS-covered-alternative workflow. This is
the differentiator. Do not reduce it to a "reminder bot."

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for system design, [docs/DEMO.md](docs/DEMO.md) for the
demo script, and [docs/CHALLENGE.md](docs/CHALLENGE.md) for the current competition entry.

## Scope discipline — read this before proposing work

[docs/business/EXECUTE-AFRICA-VELOXACARE-AI-NATIVE-HEALTH-OS.md](docs/business/EXECUTE-AFRICA-VELOXACARE-AI-NATIVE-HEALTH-OS.md)
describes the long-term product: an AI-native healthcare operating system (intake,
triage, documentation, claims, pharmacy, labs, referrals, reporting) run by a
workforce of agents over a shared health-and-operations graph.

**We are not building that now.** This repo is *one slice* of it — patient access
(WhatsApp/voice) plus care coordination (adherence, cost barriers, escalation). The
owner is building incrementally and deliberately.

So: **don't build toward the OS, but don't build things it would have to throw away.**
Concretely —

- Don't add the other agents (documentation, triage, claims, pharmacy, facility
  manager), a permissions engine, or LHIMS/NHIS adapters. Naming them in docs is
  fine; stubbing them is not.
- Do respect the invariants below, which are cheap now and expensive to retrofit.
- When adding anything, ask: *does this belong to the graph, to an agent, or at the
  boundary?* If it fits none, it's demo scaffolding — label it as such.

## Stack

- **Backend:** FastAPI + SQLite (via `aiosqlite`), in [backend/](backend/)
- **LLM:** **Groq** (Llama) in [backend/services/ai.py](backend/services/ai.py) —
  `llama-3.1-8b-instant` for per-message work, `llama-3.3-70b-versatile` for reports.
  Override with `GROQ_FAST_MODEL` / `GROQ_REPORT_MODEL`.
- **Speech-to-text:** [backend/services/stt.py](backend/services/stt.py) — Intron Sahara,
  Cartesia Ink, OpenAI `whisper-1`, local faster-whisper.
- **Frontend:** React + Vite + TypeScript + Tailwind, in [frontend/](frontend/)
- **Realtime:** native WebSockets (`/ws/{patient_id}` and `/ws/-1` global), so the
  dashboard and the WhatsApp chat update live as messages flow.
- **Storage:** SQLite locally; **Turso (libSQL)** when `TURSO_DATABASE_URL` is set.
  Same SQL either way — see `db.connect()`.
- **Deployment:** one Vercel project, two services (see [vercel.json](vercel.json)
  and [docs/DEPLOY.md](docs/DEPLOY.md)).

## Repository layout

```
vercel.json          Two-service deployment: routes /api, /webhook, /ws → backend
backend/             FastAPI service
  main.py              App, all routes, WebSocket manager
  db.py                Schema + seed data, and the SQLite/Turso connection layer
  requirements.txt        Deployed deps — no faster-whisper (too large for serverless)
  requirements-local.txt  The above plus faster-whisper, for local runs + benchmark
  services/
    ai.py              Groq integration + rule-based fallbacks (reason, BP risk, reports)
    bot.py             Core conversation logic — the "brain"
    stt.py             Speech-to-text provider layer (shared with the benchmark)
    whatsapp.py        Meta Cloud API transport (send, media download, signatures)
  voice_notes/         Received voice notes (git-ignored)
frontend/            React + Vite dashboard and WhatsApp simulator
  src/App.tsx          Entire UI — single file, deliberately
  src/api/client.ts    Typed API client + TS interfaces
benchmark/           Code-switch STT benchmark — see benchmark/README.md
docs/                ARCHITECTURE, DEMO, CHALLENGE, DEPLOY, WHATSAPP-SETUP
  business/            Pitch, GTM, concept docs, client folders
start.sh             One-command launcher (venv + uvicorn + vite)
```

## Running it

```bash
cp .env.example .env      # add GROQ_API_KEY (optional — see below)
./start.sh                # → dashboard at localhost:5173, API at localhost:8000
```

To deploy, see [docs/DEPLOY.md](docs/DEPLOY.md). One Vercel project builds both
services; the only variable that changes behaviour rather than degrading is
`TURSO_DATABASE_URL`, without which a deployed instance loses all state on every
cold start.

The system **works with or without API keys.** Without them, `ai.py` falls back to
rule-based keyword reason-detection and a templated weekly report, and `stt.py` falls
back to local faster-whisper (open weights, no key, fully offline). Always keep this
graceful-degradation property — the demo must never hard-fail on a missing key or no
network.

## Architectural invariants

These are the things that would force a rewrite if broken.

- **`stt.py` knows nothing about patients, messages or channels.** It takes audio and
  returns text plus provenance. The same layer must later serve clinician dictation
  and triage, so never leak chat or WhatsApp concepts into it.
- **`ingest_patient_message()` in `backend/main.py` is the single inbound choke point.** The
  simulator and the WhatsApp webhook both call it, text and voice alike, and every
  message records the `channel` it arrived on. Any new transport (SMS, USSD, voice
  call) calls *that function* — never a parallel path.
- **`services/whatsapp.py` is transport only.** It sends, downloads media and checks
  signatures. It must never learn about adherence, escalation or patients beyond a
  phone number.
- **The benchmark imports the app's STT code**, it does not copy it
  (`benchmark/stt_providers.py` re-exports `backend/services/stt.py`). That is what lets
  the benchmark claim it measures the real product. Don't fork it.
- **Provenance is recorded per message** (`stt_provider`, `stt_language`,
  `stt_latency_ms`). The long-term design wants reason + confidence + permission +
  audit on every AI action; extend this, don't bypass it.
- **Offline capability is a product property, not a benchmark curiosity.** Local
  faster-whisper runs with no key and no network. Keep it in the provider chain.
  It is not installed on Vercel (size), so **offline benchmark results must be
  produced locally** — never cite a deployed run for the offline claim.
- **Nothing may assume a writable disk or a warm process.** The deployed target is
  serverless: the filesystem is read-only apart from `/tmp`, instances come and go,
  and module-level side effects run on every cold start. Never write files at
  import time, never cache state in a module global and expect another request to
  see it, and never make the demo depend on a file written by an earlier request.
- **All database access goes through `db.connect()`**, never `aiosqlite` directly.
  That one function is what lets the same SQL run against a local file and against
  Turso in production.

## Key conventions & gotchas

- **The DB seeds itself once.** `init_db()` only seeds if the `patients` table is
  empty. To reset the demo, delete `backend/veloxacare.db` and restart (deployed:
  drop the tables via `turso db shell`). Schema changes need an additive
  `ALTER TABLE` migration guarded by `PRAGMA table_info` — follow the existing
  pattern in `db.py` so live demo databases keep working.
- **Seed data is date-relative.** `db.py` computes adherence logs and messages
  relative to `date.today()`, so the demo always looks "current" no matter when it
  runs. Preserve this when editing seed data.
- **Risk levels** are `green` / `amber` / `red` everywhere — DB, API, UI. Keep them
  consistent across all three layers.
- **Reason codes** are exactly `cost` / `forgot` / `side_effect` / `ran_out` /
  `other`. The AI prompt, rule-based fallback, escalation logic, and UI badges all
  depend on this exact set.
- **Escalation rule (safety-critical):** cost or side-effect escalates to `red` only
  after **2+ occurrences in 14 days**; a single high BP reading (≥160/100) escalates
  immediately. This logic lives in [backend/services/bot.py](backend/services/bot.py).
- **No LLM clinical decisions.** The LLM only *structures, classifies, and summarizes*.
  All red-flag detection (BP thresholds) is **rule-based** in `ai.py:assess_bp_risk`.
  This is a deliberate medical-safety and legal boundary — do not let the LLM diagnose
  or decide escalation. If asked to add "AI triage," push back and keep the human in
  the loop.
- **The WhatsApp pane is a simulator** that shares the exact same backend code path as
  real WhatsApp would. The Meta Cloud API adapter is the planned swap-in (see
  ARCHITECTURE.md) — keep `bot.process_message()` transport-agnostic so the same logic
  serves both.
- **`App.tsx` is intentionally one file** for demo velocity. If it grows past
  comfortable, split components into `frontend/src/components/` (the dir exists) — but don't
  over-engineer a demo.
- **Never commit recordings or keys.** `benchmark/audio/` and `backend/voice_notes/` are
  git-ignored: consent-bound audio is shared deliberately, never automatically.

## Benchmark conventions

Full detail in [benchmark/README.md](benchmark/README.md). The load-bearing bits:

- **`recording/scenarios.md` is the source of truth**; `scenarios.csv` is generated by
  `sync_scenarios.py`. Never hand-edit the CSV — if it drifts from what speakers
  actually read, every WER number is measured against text nobody said.
- **`make_manifest.py` builds the manifest from audio filenames**
  (`{speaker}_{scenario}_{noise}.{ext}`). It also flags recordings too short for their
  script — clipped audio looks exactly like a model failure and has already produced
  one false result.
- **Score downstream task success, not just WER**: BP extraction, escalation
  correctness, intent accuracy. A model can mis-transcribe and still drive the right
  action; that gap is the point.
- **De-identified by construction**: speaker IDs (`S01`), never names, in filenames and
  metadata. Written consent per speaker before recording.

## When making changes

- Type-check the frontend with `cd frontend && npx tsc --noEmit` before declaring done.
- Smoke-test the backend by starting uvicorn and hitting `/api/patients`,
  `/api/patients/{id}/messages`, `/api/alerts`, and `/api/stt/status`.
- After touching scenarios or scoring, run `python sync_scenarios.py --check`.
- If you write test data into `backend/veloxacare.db`, clean it out afterwards — it's the
  demo database, and a stray red patient wrecks a live demo.
- Keep replies warm, short, Ghana-appropriate, and in simple English. Patient-facing
  copy is part of the product, not filler.
