# Deploying to Vercel

Both halves of this repo deploy as one Vercel project using **Vercel Services**,
which runs multiple frameworks in a single project on a shared domain. The Vite
dashboard and the FastAPI backend build separately, deploy together, and roll
back together.

The result is one URL — `https://<project>.vercel.app` — serving the dashboard at
`/` and the API, webhook and WebSockets under their existing paths. That URL is
what you give Meta, and it does not change between deploys.

## Routing

[`vercel.json`](../vercel.json) at the repo root defines both services and the
public route table:

| Path | Service |
|---|---|
| `/api/*` | backend |
| `/webhook/*` | backend |
| `/ws/*` | backend |
| `/health` | backend |
| everything else | frontend |

A service receives the **original path** — `/api/patients` arrives at FastAPI as
`/api/patients`, not `/patients` — so every route in `main.py` is unchanged, and
`BASE = '/api'` in the frontend client keeps working exactly as it does locally.

Services are internal by default; the top-level rewrites are what expose them.
Routing into a service is final: if nothing inside matches, FastAPI's own 404 is
returned rather than falling through to the frontend.

## 1. Supabase PostgreSQL — required

**Do this before the first deploy.** SQLite does not survive serverless. The
production source of truth is Supabase PostgreSQL; SQLite remains the local,
zero-configuration development store.

Create a Supabase project in the closest suitable region. In the project,
click **Connect** and copy both pooler strings:

- **Session pooler, port 5432:** use locally to apply migrations.
- **Transaction pooler, port 6543:** use as `DATABASE_URL` on Vercel.

The transaction pooler is designed for temporary serverless connections. The
backend disables asyncpg's prepared-statement cache for this mode. These are
PostgreSQL URLs, not the `https://...supabase.co` project URL and not an anon or
service-role key. See Supabase's [connection
guide](https://supabase.com/docs/guides/database/connecting-to-postgres).

Put both pooler strings in the repository-root `.env` (the project's only local
environment file), then apply the checked-in
schema from the repository root. Use the string copied by Supabase; if you
manually substitute a password containing reserved URL characters, URL-encode
it first.

```dotenv
MIGRATION_DATABASE_URL=postgresql://postgres.<project-ref>:<password>@<pooler-host>:5432/postgres?sslmode=require
```

```bash
backend/.venv/bin/python backend/migrate.py
backend/.venv/bin/python backend/verify_database.py
```

Migration `001_initial.sql` enables Row Level Security on every application
table and deliberately creates no browser policies. Clinical data therefore
stays behind FastAPI; the frontend never receives a database password or
service-role key. Supabase recommends RLS for every table in an exposed schema:
[RLS guidance](https://supabase.com/docs/guides/database/postgres/row-level-security).

With `APP_ENV=production`, demo patients are never seeded. Locally, with
`DATABASE_URL` unset, `db.connect()` opens SQLite directly. Turso remains a
temporary compatibility path only and no longer satisfies production checks.

This tranche moves the clinical database, not every Supabase product at once.
Staff login still uses VeloxaCare's database-backed sessions, and voice audio is
still best-effort on `/tmp`. Supabase Auth and Storage are separate, reviewable
cutovers after the database is live; neither is being represented as complete.

## 2. Environment variables

Vercel dashboard → your project → **Settings → Environment Variables**. One set
is shared across both services.

| Variable | Needed for |
|---|---|
| `APP_ENV=production` | disables demo data/tools and enforces production configuration |
| `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` | first production staff account |
| `DATABASE_URL` | Supabase transaction-pooler PostgreSQL URL — **required** |
| `GROQ_API_KEY` | AI reason detection + weekly report |
| `META_ACCESS_TOKEN` | sending WhatsApp replies |
| `META_PHONE_NUMBER_ID` | sending WhatsApp replies |
| `META_VERIFY_TOKEN` | webhook handshake |
| `META_APP_SECRET` | **signature verification — set this in production** |
| `META_MEDICATION_REMINDER_TEMPLATE` | approved daily reminder template — **required** |
| `CRON_SECRET` | authenticates scheduled reminder calls — **required** |
| `INTRON_API_KEY` / `CARTESIA_API_KEY` / `OPENAI_API_KEY` | voice notes |
| `WHATSAPP_STT_LANGUAGE` | voice-note language hint (default `en`) |

Local development degrades gracefully. Production mode instead reports missing
launch-critical values in `/health` and refuses protected clinical API traffic;
that prevents a public deployment from quietly behaving like a demo.

`META_APP_SECRET` deserves emphasis: unset, `verify_signature()` returns `True`
and the webhook accepts unsigned requests from anyone who finds the URL. That is
the local-dev path, and it is not acceptable on a public domain.

## 3. Deploy

```bash
npm i -g vercel
vercel            # preview
vercel --prod     # production
```

Or connect the repo in the Vercel dashboard and push. Confirm afterwards:

```bash
curl https://<project>.vercel.app/health
```

You want `"status": "ok"`, `"database": "supabase-postgres"`,
`"whatsapp_configured": true`, and an empty
`"missing_production_config"`. Then open the dashboard and sign in.

The first production boot creates the bootstrap admin only when the staff table
is empty. After verifying sign-in, rotate or remove
`BOOTSTRAP_ADMIN_PASSWORD`. Follow the full [production pilot
runbook](PRODUCTION-PILOT.md) before enrolling patients.

## 4. Point WhatsApp at it

See [WHATSAPP-SETUP.md](WHATSAPP-SETUP.md). The short version: the callback URL
is `https://<project>.vercel.app/webhook/whatsapp`, and unlike a tunnel it stays
valid, so this is a one-time step.

## Speech-to-text on Vercel

`faster-whisper` — the local, offline, no-key provider — is **not** installed on
Vercel. It pulls 200MB+ of native dependencies and downloads model weights to
disk at first use, which exceeds the function size limit and has nowhere to
write.

It remains in the `stt.py` provider chain and is installed by
`backend/requirements-local.txt` for local runs and the benchmark, so the offline
claim is unchanged off-Vercel. **The benchmark's offline result must be produced
locally, not from the deployed instance.**

Deployed, voice notes need a hosted provider: `INTRON_API_KEY`,
`CARTESIA_API_KEY` or `OPENAI_API_KEY`. With none set, voice degrades to
"I couldn't hear that, please type it" — the text path is unaffected.

## Realtime behaviour

WebSockets work on Vercel (native support, public beta), with caveats the
frontend now handles:

- **Connections are capped** — 5 minutes on Hobby, up to 30 on Pro. A drop is
  normal operation, so `useLiveSocket` in `App.tsx` reconnects with backoff.
- **A socket is pinned to one function instance.** A WhatsApp message handled by
  instance B cannot push to a dashboard socket held by instance A. There is no
  fan-out. The dashboard therefore also polls every 10s, which guarantees
  convergence — an escalation raised on another instance still surfaces.

If the demo ever needs true instant cross-instance updates, the fix is a pub/sub
relay (Upstash Redis) behind `ConnectionManager`, not more polling.

## Known limits of a deployed demo

- **Voice playback is best-effort.** Audio is written to `/tmp` and is
  per-instance, so an older voice note may 404 on replay. The transcript and its
  STT provenance live in the database, which is what the record depends on.
- **Cold starts.** First request after idle pays model and dependency import
  cost. Hit `/health` before a live demo to warm it.
- **The 24-hour window still applies.** Deploying changes nothing about Meta's
  rule that free-text replies outside 24h of a patient's last message require an
  approved template.
