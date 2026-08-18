# Connecting a real WhatsApp number

The built-in simulator needs none of this. Follow it when you want patients on a
real number — the agent logic is identical either way.

This assumes the app is **deployed** (see [DEPLOY.md](DEPLOY.md)). The callback
URL is then a stable `https://<project>.vercel.app`, so registering the webhook
is a one-time step rather than something you redo every session.

## What actually binds a number to this project

A phone number belongs to **one WhatsApp Business Account (WABA)** at a time, but
a WABA isn't tied to a project. What binds a number to an application is the
**webhook URL**, which is a text field you edit:

```
phone number → WABA (your verified business) → Meta app → webhook URL → this deployment
               ↑ unchanged                     ↑ unchanged   ↑ change only this
```

So moving a number between your own projects means repointing the webhook. It
does **not** require a new SIM, a second business, or re-verification.

Moving a number to a *different business* is what costs you re-verification —
avoid that.

## 1. Credentials

Meta for Developers → your app → **WhatsApp → API Setup**:

| Copy this | Into |
|---|---|
| Access Token | `META_ACCESS_TOKEN` |
| Phone Number ID (**not** the phone number) | `META_PHONE_NUMBER_ID` |
| any random string you invent | `META_VERIFY_TOKEN` |
| Settings → Basic → App Secret | `META_APP_SECRET` |

Locally these go in `.env` (git-ignored — never put a real key in
`.env.example`). Deployed, they go in **Vercel → Settings → Environment
Variables**; a value in `.env` is not uploaded and will not reach the deployment.

The temporary access token expires in 24h. For anything beyond a demo, create a
**System User token** in
[Business Settings](https://business.facebook.com/settings/system-users) with
`whatsapp_business_messaging` and `whatsapp_business_management` — it doesn't
expire. Verify which kind you have:

```bash
curl -s "https://graph.facebook.com/v19.0/debug_token?input_token=$TOKEN&access_token=$TOKEN"
```

`"expires_at": 0` means it never expires.

## 2. Register the webhook

WhatsApp → **Configuration** → Webhook → Edit:

- **Callback URL:** `https://<project>.vercel.app/webhook/whatsapp`
- **Verify Token:** the same string you put in `META_VERIFY_TOKEN`
- Click **Verify and Save**, then **subscribe to the `messages` field**

Forgetting the `messages` subscription is the usual reason a correctly-verified
webhook receives nothing.

Verification calls your deployment, so deploy the environment variables *before*
clicking Verify and Save — otherwise `META_VERIFY_TOKEN` is unset server-side and
the handshake fails.

## 3. Recipients

On Meta's **test** number you can only message a handful of verified recipients:
API Setup → **To** → add the phones you'll demo with.

On a **registered business number** that limit doesn't apply — you're governed by
your messaging tier and the 24-hour window instead.

## 4. Enrol those numbers as patients

Inbound numbers are matched against `patients.phone`. An unrecognised number gets
a polite "not registered yet" reply — **enrolment is never automatic**, because
enrolling someone is a consented clinical act, not a side effect of texting.

Store numbers in E.164 (`+233241000001`). Meta sends them without the `+`; the
adapter compares digits only, so both forms work.

### Make the first welcome deliver

Enrollment is clinic-initiated, so a new patient normally has no open 24-hour
customer-service window. Create and approve a WhatsApp template named
`veloxacare_welcome` with one body variable and this exact body:

```text
Welcome to VeloxaCare, {{1}}! 👋 I’ll help you stay on track with your care and follow-up. Reply START to begin.
```

Then set these in the deployed environment:

```bash
META_WELCOME_TEMPLATE=veloxacare_welcome
META_WELCOME_TEMPLATE_LANGUAGE=en_US
```

### Create the medication reminder template

Create and approve a **Utility → Default** template named
`veloxacare_medication_reminder` with three body variables and this body:

```text
Hello {{1}}! 💊 It is time to take your {{2}} ({{3}}). Reply YES when done, or NO if you missed it.
```

Use realistic review samples in this order: patient first name (`Ama`), medicine
(`Amlodipine`), and dosage (`5mg once daily`). After Meta approves the template,
set:

```bash
META_MEDICATION_REMINDER_TEMPLATE=veloxacare_medication_reminder
META_MEDICATION_REMINDER_TEMPLATE_LANGUAGE=en_US
```

The Add Patient result now reports the real outcome. “Meta accepted” means the
API call succeeded; the conversation changes to `sent`, `delivered`, `read` or
`failed` when Meta posts its status receipt. A welcome shown as **Not sent** was
saved to the clinical record but did not reach the patient's phone.

## What the webhook does

```
GET  /webhook/whatsapp    Meta's verification handshake
POST /webhook/whatsapp    inbound message
```

On POST it verifies the `X-Hub-Signature-256` HMAC, records outbound delivery
receipts, drops duplicate inbound deliveries by
message ID (Meta retries aggressively — without this a patient gets two replies),
resolves the sender to a patient, and then:

- **text** → `ingest_patient_message(..., channel="whatsapp")`
- **voice note** → download the media, `stt.transcribe()`, then the same
  `ingest_patient_message()`
- **anything else** → a short "send text or a voice note" reply

The reply goes back over WhatsApp, and the dashboard updates over WebSocket in the
same moment.

`WHATSAPP_STT_LANGUAGE` sets the language hint for voice notes (`en`, `tw-en`,
`pcm-en`, `gaa-en`) — WhatsApp doesn't tell us what language a note is in, so this
is a deployment default rather than per-message detection.

## Spoken replies

A patient who sends a voice note gets one back. `TTS_MODE=mirror` — the default —
speaks only when the patient spoke, so typed conversations cost no synthesis
credit and get no audio. `always` speaks every reply; `off` disables it.

The reply is sent twice, as text and then as audio, because they do different
jobs: the text stays readable, searchable and forwardable to a family member,
while the audio is what a patient who can't read it needs. Set
`TTS_WHATSAPP_SEND_TEXT=0` for voice-only.

Providers reuse the STT keys — `INTRON_API_KEY` and `CARTESIA_API_KEY`, nothing
new to obtain. Intron returns Ogg/Opus, which WhatsApp renders as a true
voice-note bubble with a waveform; Cartesia returns MP3, which arrives as a
playable attachment. Both work, and with neither key set the agent simply replies
in text as it always did.

Two things to know before you promise a Ghanaian voice:

- **Intron TTS has no Twi, Akan or Ga.** It has Pidgin (`pcm-en` uses it) and ten
  English accents, none Ghanaian. `INTRON_TTS_ACCENT` defaults to `hausa`, the
  only one of the ten also spoken in Ghana. Sahara *recognises* tw/ak/gaa; nothing
  yet *speaks* them.
- **Intron is slow, and sometimes very slow.** Measured 5 Aug 2026 on a
  one-sentence reply: Intron 17–25s, Cartesia 2.8s. WhatsApp is asynchronous so
  that is a delay rather than a failure, but if it's too long for your pilot set
  `TTS_ORDER=cartesia,intron`, which reorders the chain without losing fallback.

Its sync endpoint answers **HTTP 503 with a `text_id`** rather than audio when
its queue can't finish inside 120s — documented behaviour, not an error. The
client treats that as a failure and moves to the next provider, because the
queued job is no use to someone waiting on a reply: one observed job was still
`TTS_TEXT_PROCESSING` six minutes later.

Two settings keep that from reaching the patient. `INTRON_TTS_TIMEOUT_S`
(default 20) gives up long before Intron's own deadline, and a circuit breaker
benches a provider for `TTS_COOLDOWN_S` after `TTS_TRIP_AFTER` consecutive
failures. During the 5 Aug backlog this took the cost of a reply from 122s, to
22s, to 1.8s once the breaker tripped. `/api/tts/status` reports `cooling_down`
so an outage looks like an outage instead of a mystery.

Deployed, voice notes need a **hosted** STT provider; the local offline engine
isn't installed on Vercel. See [DEPLOY.md](DEPLOY.md#speech-to-text-on-vercel).

## Testing without Meta

`backend/services/whatsapp.py` degrades gracefully: with no credentials the
webhook still runs and simply declines to send. You can exercise the whole path
against a local server with a signed payload:

```python
import hashlib, hmac, json, requests
raw = json.dumps({"entry":[{"changes":[{"value":{"messages":[
    {"id":"wamid.TEST","from":"233241000002","type":"text",
     "text":{"body":"I can't afford the medicine"}}]}}]}]}).encode()
sig = "sha256=" + hmac.new(b"<META_APP_SECRET>", raw, hashlib.sha256).hexdigest()
requests.post("http://localhost:8000/webhook/whatsapp", data=raw,
              headers={"Content-Type":"application/json","x-hub-signature-256":sig})
```

Point it at your deployment to test the deployed path — but note this writes a
real message and may trigger a real escalation, so use a test patient.

## Gotchas

- **Repointing the webhook takes the previous project offline.** One app, one
  callback URL. If the old project is serving real users, that's a live outage.
- **`META_APP_SECRET` unset skips signature verification** so local dev works.
  On a public URL that leaves the webhook open to anyone who finds it — set it.
- **24-hour customer service window:** outside 24h of a patient's last message you
  can only send pre-approved template messages, not free text. This matters for
  proactive medication reminders — the demo's reminders are replies within the
  window, but a real deployment needs
  [approved templates](https://business.facebook.com/wa/manage/message-templates).
- **Env vars are per-deployment.** Changing one in the Vercel dashboard requires a
  redeploy before the running service sees it.

## If nothing arrives

| Symptom | Cause |
|---|---|
| Verify and Save fails | `META_VERIFY_TOKEN` mismatch, or not yet deployed |
| Verified but silent | `messages` field not subscribed |
| 403 in your logs | `META_APP_SECRET` mismatch — signature check rejecting |
| Reply never sends | Token expired, or recipient not on a test number's allow-list |
| Works, then forgets everything | `DATABASE_URL` unset — see [DEPLOY.md](DEPLOY.md) |
