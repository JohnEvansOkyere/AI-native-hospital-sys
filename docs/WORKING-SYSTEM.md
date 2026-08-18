# From demo to working system

What has to change before a real clinic runs VeloxaCare day to day — with the
dashboard gaps called out specifically, because that is where "demo" shows most.

Scope guard: everything here stays inside the slice this repo owns (patient
access + care coordination). Nothing below builds toward the other OS agents.
Items are ranked **P0** (no real patient before this), **P1** (a pilot limps
without it), **P2** (matters at scale, not at 20 patients).

> **Implementation update — 14 August 2026:** secure staff sessions and roles,
> CSRF, authenticated WebSockets, production/demo separation, consent and
> opt-out, per-patient language, the Today worklist, owned/acknowledged cases,
> staff alert delivery records, durable webhook idempotency, hourly template
> reminders, clinic/staff settings, audit events, and first-party boundary tests
> are now implemented. See [PRODUCTION-PILOT.md](PRODUCTION-PILOT.md). Remaining
> items below are still valuable; the launch-critical external gaps are error
> monitoring, tested backups/restore, operational policies, and a real clinic
> pilot—not another product-surface expansion.

## P0 — before any real patient data touches this system

### 1. Authentication and access control — the biggest hole
**Implemented for the single-clinic pilot.** Every clinical API and WebSocket
requires a revocable database session; writes require CSRF; day-to-day and admin
roles are enforced; and staff identity drives acknowledgements, resolutions and
the audit trail.

- Login for clinic staff (simplest honest option: email + password via a
  battle-tested library, sessions in the DB — no need for an identity provider
  at pilot size).
- Every `/api/*` route and `/ws/*` connection requires a session. The WhatsApp
  webhook keeps its existing signature check (`META_APP_SECRET`) instead.
- Record *who* did clinical actions: `resolved_by` on escalations is currently
  free text the client sends; it should come from the logged-in user.
- Two roles are enough for a pilot: care team (day-to-day) and admin
  (enrolment, exports, settings). Don't build a permissions engine — that
  belongs to the OS later.

### 2. Consent and lifecycle, not just enrolment
**Implemented for the pilot.** Enrolment captures consent, preferred language
and reminder time; pending consent sends nothing; staff can pause outreach; and
patient `STOP` / `START` messages append consent events and immediately change
delivery eligibility.
`EnrollModal` creates a patient; a real clinic needs the surrounding facts:

- Consent recorded per patient (what they agreed to, when, how) — the same
  discipline the benchmark recording kit already practices.
- **Preferred language on the patient record.** Today the language hint is one
  global env var (`WHATSAPP_STT_LANGUAGE`) — wrong the moment two patients
  speak differently. One column, set at enrolment ("Twi anaa English?"),
  drives STT hints and the translate-then-speak reply path per patient. This
  is the single highest-leverage language feature and it's additive
  (implemented in the SQLite compatibility schema and versioned PostgreSQL migration).
- Pause / opt-out that actually stops reminders, and is visible in the UI.
- Duplicate-phone guard on enrolment.

### 3. Ops floor: know when it breaks
**Partially implemented.** The DB-aware health check and durable webhook
idempotency are shipped. Error tracking plus a tested Supabase backup/restore
routine remain go-live work.
- Error tracking (Sentry free tier) on backend and frontend — today a failed
  reply dies in a server log nobody reads.
- A `/health` endpoint checking DB + provider config, and an uptime ping on it.
- Supabase backup exports and a restore rehearsal (a live pilot database that has never been restored
  from backup is a demo database with real patients in it).
- Webhook idempotency: Meta retries deliveries; an inbound message processed
  twice sends the patient two replies and double-counts adherence.

## P1 — the dashboard, from demo pane to care-team tool

The current UI ([App.tsx](../frontend/src/App.tsx), deliberately one file) is a
*viewer*: list, detail, alerts, simulator. A nurse's shift needs a *worklist*.
In rough order of value:

### 4. "Who needs me today" as the home screen
**Implemented for the pilot.** Today now combines unacknowledged cases,
appointments, due reminders and delivery failures, with urgent cases one click
from the owned care workflow.
The stats bar counts red/amber patients but the list is static and unordered.
The opening view should be a triage queue: escalations and reds first, sorted
by severity then age, each row answering *why* it's here (reason badge, latest
BP, days since last contact) with one-tap actions (open chat, resolve, book).
The data all exists; this is presentation.

### 5. Make the differentiator visible: reason analytics
The product's whole thesis is *why* patients slip (cost vs forgot vs
side-effect vs ran-out), and the dashboard never aggregates it. One panel:
reason breakdown over time, cost-barrier patients as a named cohort, and what
happened after escalation (NHIS switch, resolved, pending). This is also the
"visible reasoning" lesson from the challenge results — judges and clinic
directors both need to *see* the intelligence, not take it on faith.

### 6. Patient detail that supports a clinical conversation
- **BP trend chart** (readings are already stored; nothing plots them).
- Adherence calendar (taken / missed-with-reason per day), not just a ring.
- Escalation + appointment history inline, so the nurse sees one timeline.

### 7. Alerts panel → escalation workflow
**Implemented at pilot depth.** Cases can be assigned/acknowledged, have due
times and durable staff-notification status, and require a named outcome before
closure. Accumulating multi-note threads and richer filters remain later work.
Resolution exists; a workflow needs: assignment ("Ama is on this"), notes
that accumulate, filters (open/mine/resolved), and time-open shown — a red
that's been open three days should look different from one opened an hour ago.

### 8. Honest system status, extended
The chat pane already shows which STT model is live — good pattern, extend it:
show when a reply was translated (the API now returns `spoken_body` — render
it under the bubble: "spoken in Twi"), when TTS fell back to an English voice,
and when WhatsApp delivery failed (`delivery_status` is stored and returned,
the UI ignores it).

### 9. Frontend structure and hygiene
- Split App.tsx into `components/` (the dir exists; past ~1,300 lines the
  single file is now costing more than it saves).
- Loading/error/empty states and failure toasts — today most `api.*` failures
  are silent, which in a clinic reads as "the system ate it".
- Mobile layout: nurses will open this on phones; the three-pane layout
  doesn't survive a small screen.

## P1 — conversation quality

### 10. Language support follow-through (started 2026-08-07)
Khaya is wired (STT for Twi/Ga/Ewe, translate-then-speak with real Twi/Ewe
voices). What remains:
- Get a key, run `benchmark/probe_khaya.py`, and record what it measures —
  every Khaya capability is unverified until then (documented ≠ shipped).
- Benchmark Khaya on the existing 57-clip corpus (`--providers khaya,...`) so
  its code-switch behaviour is a number, not a hope.
- Per-language intent keywords: the rule-based fallback detector is tuned to
  English keywords; a Twi transcript from Khaya may express "cost" without any
  of them. Extend the keyword sets per language, or route non-English
  transcripts through the LLM path with translation.
- Re-run Sahara when the Akan–English pair ships (was due w/o 10 Aug 2026).

### 11. Reminders need a real scheduler
**Implemented for daily hypertension medication reminders.** The authenticated
hourly cron uses approved, optionally localized templates, consent/pause gates,
unique daily dispatch keys and up to three durable retries. Weekly BP and
appointment reminder schedules remain future extensions.
`trigger_care_reminder` / `trigger_checkin` are demo buttons. A working system
sends them on schedule (Vercel Cron hitting an authenticated endpoint is
enough — nothing may assume a warm process), respects quiet hours and the
patient's timezone, and uses approved templates outside WhatsApp's 24-hour
window.

## P2 — scale and polish

- Patient search / filter / pagination (the list is fine at 12, not at 400).
- Outbound retry queue for failed WhatsApp sends (currently fire-and-forget).
- Rate limiting on public endpoints.
- Per-clinic settings (BP thresholds stay rule-based and reviewed — but a
  clinic may legitimately set its own escalation contacts and quiet hours).
- Data export (CSV of patients/adherence/escalations) for clinic reporting.
- Multi-clinic tenancy — **only when a second clinic actually signs.**

## Explicitly not now
Triage/claims/documentation agents, LHIMS/NHIS adapters, permissions engine,
FHIR — the OS can have them later. Anything above labeled "demo scaffolding"
(the demo action bar, the simulator pane) stays, because the simulator doubles
as the training and support tool, but it should move behind the login too.
