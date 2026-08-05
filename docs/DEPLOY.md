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

## 1. Database — required

**Do this before the first deploy.** SQLite does not survive serverless: the
bundle is read-only apart from `/tmp`, and `/tmp` is per-instance and wiped on
cold start. Without Turso, patient replies, escalations and adherence logs vanish
after a few minutes of idle, and two concurrent instances disagree about state.

[Turso](https://turso.tech) is libSQL — SQLite over HTTP — so the schema, the
seed data and every query in `db.py` are unchanged.

```bash
curl -sSfL https://get.tur.so/install.sh | bash
turso auth signup
turso db create veloxacare
turso db show --url veloxacare        # → TURSO_DATABASE_URL
turso db tokens create veloxacare     # → TURSO_AUTH_TOKEN
```

`init_db()` creates the schema and seeds on first boot, exactly as it does
locally. To reset a deployed demo, `turso db shell veloxacare` and drop the
tables, then redeploy.

Locally nothing changes: with `TURSO_DATABASE_URL` unset, `db.connect()` opens
the SQLite file directly.

## 2. Environment variables

Vercel dashboard → your project → **Settings → Environment Variables**. One set
is shared across both services.

| Variable | Needed for |
|---|---|
| `TURSO_DATABASE_URL` | persistence — **required** |
| `TURSO_AUTH_TOKEN` | persistence — **required** |
| `GROQ_API_KEY` | AI reason detection + weekly report |
| `META_ACCESS_TOKEN` | sending WhatsApp replies |
| `META_PHONE_NUMBER_ID` | sending WhatsApp replies |
| `META_VERIFY_TOKEN` | webhook handshake |
| `META_APP_SECRET` | **signature verification — set this in production** |
| `INTRON_API_KEY` / `CARTESIA_API_KEY` / `OPENAI_API_KEY` | voice notes |
| `WHATSAPP_STT_LANGUAGE` | voice-note language hint (default `en`) |

Everything except the Turso pair degrades gracefully — the app still boots and
serves without them. Turso is the one that genuinely changes behaviour.

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

You want `"whatsapp_configured": true`. Then open the dashboard at `/`.

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
