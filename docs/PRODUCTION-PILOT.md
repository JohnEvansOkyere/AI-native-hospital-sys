# VeloxaCare production pilot runbook

This release is a production-oriented **single-clinic hypertension pilot**, not
the full health OS. It protects the care workspace, gives nurses an accountable
work queue, records consent, and sends idempotent scheduled reminders.

## What production mode changes

Set `APP_ENV=production`. In this mode:

- demo patients are not seeded;
- the WhatsApp simulator is hidden and its patient-message endpoints return 404;
- webhook requests are rejected unless `META_APP_SECRET` validates the signature;
- staff must sign in for every clinical API and WebSocket;
- all writes require the session's CSRF token;
- a missing PostgreSQL connection blocks the clinical API completely;
- missing Meta, cron or medication-template configuration keeps `/health`
  degraded and messaging or other clinical actions disabled. An administrator
  may still save a patient with consent pending, but cannot activate messaging
  until the launch configuration is complete.

Local development remains self-contained. It seeds relative demo data and a
local-only account (`admin@veloxacare.local` / `VeloxaCare-Local-Only`). Never
reuse that account or run development mode on a public deployment.

## First clinic boot

Configure all values documented in [`.env.example`](../.env.example), including:

```dotenv
APP_ENV=production
ENABLE_DEMO_TOOLS=0
DEMO_SEED=0
BOOTSTRAP_ADMIN_EMAIL=admin@yourclinic.com
BOOTSTRAP_ADMIN_PASSWORD=<unique 12+ character secret>
BOOTSTRAP_ADMIN_NAME=Clinic Administrator
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@<pooler-host>:6543/postgres?sslmode=require
META_ACCESS_TOKEN=...
META_PHONE_NUMBER_ID=...
META_VERIFY_TOKEN=...
META_APP_SECRET=...
META_WELCOME_TEMPLATE=veloxacare_welcome
META_MEDICATION_REMINDER_TEMPLATE=veloxacare_medication_reminder
CRON_SECRET=<long random secret>
```

The bootstrap credentials create the first admin only when `staff_users` is
empty. After the first successful sign-in, rotate or remove
`BOOTSTRAP_ADMIN_PASSWORD` from the deployment environment. Add normal care-team
users through the protected admin API; never share an account between nurses.

## Patient enrolment and consent

At enrolment, staff record the patient's language, reminder time, and whether
WhatsApp consent was obtained. If consent is not checked, the record is saved as
`pending` and no welcome or reminder is sent.

This consent-pending path remains available while Meta templates or other launch
integrations are still being configured. It supports clinic setup without using
fake credentials or accidentally contacting a patient from an incomplete system.

Patients can reply `STOP`, `UNSUBSCRIBE`, or `PAUSE` at any time. These rules are
deterministic and immediately disable outreach. `START` records a new affirmative
opt-in. Staff can also pause and resume messages in the patient record.

The reminder job only selects active chronic-care patients with granted consent,
active opt-in, and no pause.

## Daily care-team workflow

1. Sign in with an individual staff account.
2. Open **Today** and acknowledge an urgent case to assign it to yourself.
3. Review the signal and its evidence; contact the patient.
4. Record the concrete outcome before closing the case.
5. Check delivery failures and confirm a safe alternative contact path when a
   WhatsApp message did not arrive.

New red cases have a four-hour due time; amber cases have 24 hours. If a staff
alert number and approved template are configured, VeloxaCare sends a durable
WhatsApp notification and records whether Meta accepted it. Otherwise the case
is honestly labelled `dashboard_only`.

## Scheduler and retry behaviour

Vercel calls `/api/cron/hourly` at the top of every hour. The endpoint accepts
only `Authorization: Bearer ${CRON_SECRET}`. Each medication reminder has a
unique `(patient, kind, date)` dispatch record, so two cron calls cannot create
two sends. Failed sends retry up to three times and remain visible in Today.

The hourly schedule requires a Vercel plan that supports hourly Cron Jobs. If
the deployment plan only supports daily jobs, use an external hourly scheduler
with the same bearer token or upgrade before enrolling patients.

## Go-live verification

Do not enrol real patients until all checks pass:

- `/health` returns `status: ok`, `database: supabase-postgres`, and no missing production settings;
- an unauthenticated `/api/patients` request returns 401;
- a staff user can sign in and see only the clinic workspace, not Demo;
- an unsigned webhook POST returns 403;
- a consent-pending test patient receives no message;
- a consented test patient receives the approved welcome template;
- a test `STOP` disables outbound care actions and `START` restores them;
- a forced reminder failure appears in Today and retries without duplication;
- a red test signal creates a case, reaches the configured staff alert path,
  can be acknowledged by name, and cannot be closed without an outcome note;
- a Supabase backup export and restore rehearsal has been completed with non-patient test data.

Supabase's automatic daily-backup retention depends on the paid plan; free-tier
projects should be exported regularly with `supabase db dump`. Database backups
do not restore deleted Storage objects, so voice-note storage needs its own
retention and recovery procedure. See the [Supabase backup
guide](https://supabase.com/docs/guides/platform/backups).

## Known pilot boundaries

- This is one clinic, not multi-tenant SaaS. Do not place two clinics in one database.
- Audio replay remains best-effort on serverless `/tmp`; the transcript and model
  provenance are the durable record.
- Realtime uses authenticated sockets plus polling; it is not a cross-instance
  event bus.
- This release adds software controls, not regulatory certification. Complete a
  Ghana-specific privacy, clinical-safety, data-retention and incident-response
  review before handling live patient data.
