# Pan-African AI & Innovation Summit — VeloxaCare Application Answers

Drafted 14 August 2026. Every number below is traceable to something in this
repo or a cited study — no invented metrics, no claimed pilot that hasn't run.

**Before submitting:** confirm the form's real limits (Execute Africa displayed
"300 words" and enforced 300 *characters* — see
[EXECUTE-AFRICA-VELOXACARE-APPLICATION-ANSWERS.md](EXECUTE-AFRICA-VELOXACARE-APPLICATION-ANSWERS.md)).
Paste into the field and check the counter before trusting these lengths.

---

## Track Selection

**Selected: Health.**

Right call — and the same track VeloxaCare entered for the MLC Africa × Intron
challenge, so the positioning stays consistent. The strength here is a deployed
product with clinical safety rails and a real speech benchmark, not a novel
model: against research entries that reads as thin, against health entries it
reads as unusually far along.

---

## Project Idea (max 200 words)

VeloxaCare is a WhatsApp-based patient engagement system for chronic disease
management in Ghana, currently focused on hypertension.

About 55% of chronic patients in Ghana don't take medication as prescribed —
and in one Ghanaian study, 96% of non-adherent patients gave **cost**, not
forgetfulness, as the reason (Buabeng et al., 2004). Reminder apps therefore
solve the wrong problem.

VeloxaCare checks in with patients on WhatsApp — no app to install. Patients
reply by text or voice note in English, Twi or Pidgin, and a Twi voice note
gets a spoken Twi reply back. The system doesn't just log yes/no adherence: it
classifies *why* a patient slipped — cost, forgot, side effect, ran out — and
routes each reason differently. Cost barriers escalate to the care team and
trigger an NHIS-covered-alternative workflow.

Clinical decisions stay rule-based, never delegated to the model: a reading of
160/100 or above escalates immediately; cost and side-effect patterns escalate
on repeat. The LLM only structures, classifies and summarises. Nurses get a
live dashboard and a weekly risk-ranked report.

The system runs today, including a voice pipeline benchmarked across four
speech models on 57 code-switched Ghanaian recordings.

*(~200 words)*

### Shorter fallback (~100 words, if the field is tighter than advertised)

VeloxaCare is a WhatsApp platform for chronic disease care in Ghana. Patients
reply by text or voice note in English, Twi or Pidgin — no app to install. Most
adherence tools assume patients forget; in Ghana, 96% of non-adherent patients
say the reason is cost. So VeloxaCare detects *why* a patient stopped — cost,
forgot, side effect, ran out — and routes each reason to a different action,
escalating cost barriers to the care team with an NHIS-covered alternative.
Blood-pressure escalation is rule-based, never AI-decided. It is built,
running, and benchmarked on 57 code-switched Ghanaian voice recordings.

---

## Local Relevance

VeloxaCare is built for how Ghanaians actually communicate. WhatsApp is where
patients already are — no app to install, no data plan, no literacy assumed.
They reply "YES" or send a voice note in English, Twi or Pidgin, and a Twi
voice note gets a spoken Twi reply back.

We measured what imported systems get wrong here rather than assuming it.
Across 57 code-switched Ghanaian recordings from 3 speakers, four speech models
scored as low as 7% word error rate on English but degraded to 61–95% on
Twi–English — a collapse invisible to any benchmark run on Western English. And
we score clinical consequence, not transcription: "one-sixteen" (safe) versus
"one-sixty" (emergency) is one vowel.

The problem is local too. Cost-driven non-adherence, with the NHIS formulary as
the way out of it, is not what an imported adherence app is shaped to solve.

It also runs on a bad connection — speech recognition works offline on open
weights when the network doesn't.

*(~160 words)*

---

## Tech Stack & Tools

Plain text, no markdown — paste directly into the form.

Backend: Python, FastAPI, SQLite locally and Supabase PostgreSQL in production,
native WebSockets for live dashboard updates.

Frontend: React, Vite, TypeScript, Tailwind CSS.

LLM: Groq — Llama 3.1 8B Instant for per-message classification, Llama 3.3 70B
Versatile for weekly clinical reports. Used only to structure, classify and
summarise; never to make a clinical decision.

Speech-to-text: Intron Sahara (African-built), GhanaNLP Khaya (Twi, Ga, Ewe),
Cartesia Ink, OpenAI Whisper, and local faster-whisper for fully offline
operation.

Text-to-speech: GhanaNLP Khaya (real Twi and Ewe voices), Intron TTS, Cartesia
Sonic.

Translation: GhanaNLP Khaya MT (English to and from Twi, Ga, Ewe), so replies
are translated before they are spoken.

Messaging: Meta WhatsApp Cloud API — webhook signature verification, media
download, delivery status.

Deployment: Vercel serverless, with no assumption of a writable disk or a warm
process.

Evaluation: a purpose-built benchmark harness that imports the production
speech code rather than copying it, so the models measured are the models
serving patients. It scores word error rate, blood-pressure extraction,
escalation correctness, intent accuracy, code-switch penalty and latency.

Engineering practice: the system works with or without API keys — rule-based
fallbacks for reason detection and reports, plus offline speech recognition —
so a missing key degrades quality, never availability.

---

## Previous Experience (optional)

**Domain.** Seven years in pharmacy in Ghana, the most recent as team lead. I
have watched patients walk in with a prescription and leave without their
medicine because they could not afford it. VeloxaCare's central design
decision — that non-adherence here is an economic problem, not a memory
problem — comes from standing behind that counter, not from reading a paper.

**Building AI products.** My team previously built and shipped VeloxaRecruit,
an AI-powered HR platform helping Ghanaian recruiters hire faster and more
effectively. We have taken an AI product from idea to working system before.

**This project.** VeloxaCare was built and submitted to the ML Collective
Africa × Intron Agentic Voice AI Challenge (Deep Learning Indaba 2026, Health
track), which required a voice-driven agent taking a real downstream action
plus a benchmark across three or more speech models on code-switched audio. For
it we recorded and de-identified a 57-clip Ghanaian code-switch corpus with
written consent per speaker, benchmarked four speech models, and published the
results — including findings unflattering to individual providers, reported as
measured. The work continues into Intron's Sahara CodeSwitch Africa Challenge.

VeloxaCare is functional end to end today — enrolment, WhatsApp conversation,
voice in and out, reason classification, rule-based escalation, appointment
booking, a live care-team dashboard and AI-generated weekly reports — with a
60-day, 30-patient clinic pilot ready to run.

*Optional, if the form invites personal motivation:* a family member nearly
died after missing diabetes medication they couldn't consistently afford.

---

## Social Impact Statement (max 100 words)

Uncontrolled hypertension kills quietly in Ghana — patients stop treatment,
nobody notices until the stroke. VeloxaCare closes that gap between visits
using the phone patients already have, in the language they already speak,
including by voice for those who cannot comfortably read.

Crucially, it treats non-adherence as an economic problem, not a memory
problem: when a patient can't afford medication, the care team is told and an
NHIS-covered alternative is offered — instead of losing the patient silently.

Clinical judgement stays human. The AI handles language, patterns and
paperwork, so scarce nurses can spend their time on patients.

*(~100 words)*
