# Appointment booking — build and demo checklist

This feature proves the challenge's required **downstream action**: a patient can
ask by text or voice, the agent offers real clinic availability, and the chosen
appointment becomes an operational record for the care team.

## Product scope

- [x] Keep booking inside the current patient-access and care-coordination slice.
- [x] Use a small internal clinic schedule; do not introduce a full hospital calendar.
- [x] Keep emergency detection ahead of appointment handling.
- [x] Use deterministic dates, slots and collision rules—not an LLM clinical decision.
- [x] Preserve the same inbound path for the simulator, WhatsApp, text and voice.

## Patient action

- [x] Recognise booking, appointment lookup, rescheduling and cancellation.
- [x] Understand weekday, today/tomorrow and Twi `ɔkyena` date requests.
- [x] Understand morning/afternoon and Twi `anɔpa` period requests.
- [x] Honour a named clinic clinician when one is requested.
- [x] Offer only actual available weekday slots.
- [x] Save the confirmed booking with a `VC-0000` reference.
- [x] Require explicit `CANCEL` confirmation before cancelling.
- [x] Make a cancelled slot available again.

## Care-team operation

- [x] Add an Appointments dashboard separate from the patient conversation.
- [x] Show Today, Upcoming and History without crowding the chat.
- [x] Let staff open the patient record from the appointment.
- [x] Let staff mark a visit complete or cancel it.
- [x] Broadcast appointment changes to the dashboard in real time.
- [x] Expose list, create and update APIs for future staff/calendar integrations.

## Safety and reliability

- [x] Store appointments through `db.connect()` for SQLite and PostgreSQL compatibility.
- [x] Add the schema with `CREATE TABLE/INDEX IF NOT EXISTS` for live demo databases.
- [x] Prevent two confirmed appointments for one clinician/date/time.
- [x] Reject weekends, past dates and unsupported clinic times.
- [x] Work without AI, speech or network keys.

## Verified demo path — 6 August 2026

- [x] Twi/code-switched request offered Friday-morning slots.
- [x] `Dr. Mensah` in the request was preserved in the stored booking.
- [x] Appointment lookup returned the stored date, time, clinician and reference.
- [x] Rescheduling changed the same appointment record.
- [x] Cancellation required confirmation and released the slot.
- [x] A second patient could book the released slot.
- [x] A simultaneous staff-side duplicate returned HTTP `409`.
- [x] Frontend TypeScript check passed.
- [x] Production frontend build passed.

## Stage demo

1. Open **Demo** and select Abena Owusu.
2. Send: `Mepɛ sɛ mebook appointment wɔ Dr. Mensah nkyɛn ɔkyena anɔpa`.
3. Reply `1` to choose the first available time.
4. Open **Appointments** and show the new confirmed record.
5. Mark it **Complete** to show the human-controlled clinical handoff.

The success condition is not “the assistant understood booking.” It is: **a valid,
non-conflicting appointment exists in the database and is visible to the care team.**
