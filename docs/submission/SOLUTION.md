# VeloxaCare — Solution Description

**MLC (Africa) × Intron Agentic Voice AI Challenge · Deep Learning Indaba 2026**
**Track:** Health
**Team:** Veloxa Technology Limited (Ghana)

> Fill the marked `‹›` spots after the Twi/Pidgin benchmark run. Everything else
> is final.

---

## 1. The problem

In Ghana, the number one reason patients stop taking chronic medication is
**cost — 96% in one study — not forgetting.** Almost every digital adherence tool
built for this market is a reminder bot, which solves the smallest part of the
problem. Reminding someone to take a medicine they cannot afford does nothing.

Hypertension makes this expensive. It is asymptomatic until it isn't; a patient
who quietly stops treatment because a month's supply costs more than they have
looks identical, in any adherence dashboard, to one who simply forgot. The clinic
finds out at the next crisis.

The second problem is how patients actually talk. A Ghanaian patient describing a
blood-pressure reading to their clinic says something like:

> *"Me BP yɛ one-sixteen over seventy-eight."*

Twi grammar, English numbers, in one sentence. Speech systems trained on clean
monolingual English degrade exactly here — and in this product a misheard digit is
not a word-error statistic, it is a clinical decision:

| Heard | Reading | Decision |
|---|---|---|
| "one-**sixteen** over seventy-eight" | 116/78 | **green** — no action |
| "one-**sixty** over seventy-eight" | 160/78 | **red** — escalate to the care team |

One vowel. Two different clinical outcomes.

## 2. Who it is for

**Patients** on chronic medication — currently hypertension — who own a phone with
WhatsApp, may not read fluently in English, and speak a mix of Twi, Ghanaian
Pidgin, Ga and English depending on who they're talking to.

**Clinic staff** at small and mid-sized primary-care facilities: a nurse or care
coordinator who needs to know, at a glance, which of several hundred patients
needs them today and why.

The paying customer is the facility, not the patient. Patients reach the service
by voice note on a number they already have, at no cost to them.

## 3. What it does

Voice in, clinical action out:

```
patient voice note (WhatsApp, any language mix)
   → speech-to-text
   → intent + reason detection (cost / forgot / side-effect / ran out)
   → blood-pressure extraction
   → deterministic escalation rules
   → task routed to the right human, tracked to outcome
   → clinic dashboard updates live
```

The differentiator is that the agent detects **why** a patient slipped and routes
each reason differently:

| Reason | Action |
|---|---|
| **Cost** | Escalate to care team, trigger the NHIS-covered-alternative workflow |
| **Side effect** | Clinical review |
| **Ran out** | Arrange refill |
| **Forgot** | Adjust reminder timing — the only case a reminder actually helps |

Cost and side-effect escalate to `red` after 2+ occurrences in 14 days. A single
blood-pressure reading at or above 160/100 escalates immediately.

## 4. Technical overview

**Stack.** FastAPI + SQLite backend, React + Vite clinical dashboard, WhatsApp
Cloud API transport, native WebSockets so the dashboard reacts as messages arrive.

**Speech layer.** A single provider abstraction
([`backend/services/stt.py`](../../backend/services/stt.py)) fronts four models:

| Model | Kind | Ghanaian language support |
|---|---|---|
| **Intron Sahara** | African-built, code-switch aware | ✅ `tw` `ak` `pcm` `gaa` |
| **Cartesia Ink** (`ink-whisper`) | commercial, latency-optimised | ❌ `HTTP 400: invalid language: tw` |
| **OpenAI Whisper** (`whisper-1`) | frontier commercial | ❌ |
| **faster-whisper** | open weights, **fully offline** | ❌ |

**One inbound path.** WhatsApp messages and the built-in simulator both call the
same `ingest_patient_message()`. Text and transcribed voice run identical logic,
including escalation. New channels (SMS, USSD, voice call) plug into that one
function rather than duplicating it.

**The benchmark imports the application's speech code** rather than
reimplementing it, so the models measured are literally the models serving
patients — not a detached test harness.

**Graceful degradation.** Missing key, dead network, no models installed: the
system degrades to something useful and never hard-fails. With no credentials at
all it falls back to local open-weights speech recognition that runs entirely
offline — which is also the deployment answer for a district clinic with
unreliable connectivity.

**Provenance.** Every message records the channel it arrived on, which speech
model transcribed it, the language hint used, and the latency. That provenance is
visible in the patient's clinical record: a nurse can play back what was actually
said and see what the model heard.

## 5. What we measured

Full results: [`benchmark/results/REPORT.md`](../../benchmark/results/REPORT.md).

We score **downstream task success**, not just word error rate: blood-pressure
extraction, **escalation correctness**, intent accuracy, and the degradation from
English to code-switched speech. The intent and escalation logic is rule-based and
identical for every model, so the comparison stays fair.

**The language-support asymmetry is the headline.** Intron's documented input
languages include `ak`, `tw`, `pcm` and `gaa`. Whisper's ~99 languages contain
none of them, and Cartesia's `ink-whisper` inherits that gap — we tested it, and
the endpoint returns `HTTP 400: invalid language: tw`. Only the African-built
model can be told what language the patient is speaking; the other three run in
English mode on Twi and Pidgin audio by necessity, not by our choice.

**English control (5 utterances, 1 speaker, quiet):** all three tested models
reached 100% on blood-pressure extraction, escalation correctness and intent.
Sahara led on word error rate (0.054 vs 0.068) and was the **only** model to
transcribe *amlodipine* correctly — the clinically load-bearing word in a refill
request. This set exists to establish that any later degradation is attributable
to code-switching rather than to accent or recording conditions.

**Code-switched sets:** ‹Twi and Pidgin results — WER, escalation accuracy,
code-switch penalty per model›

**Escalation flips:** ‹number of cases where a transcription error changed the
red/amber/green decision, and which models›

### A methodology correction worth reporting

Our first run scored Sahara *worst* on word error rate. It wasn't. Sahara heard
"one forty-two over ninety-five" and wrote **`142/95`** — recognising it as a
blood pressure — while others wrote `142 over 95`. Our normaliser tokenised those
differently, so WER punished the model that had understood the content best. After
canonicalising blood-pressure notation, Sahara moved from worst to best. Nothing
about the audio or the models changed.

We report this because it is the benchmark's own thesis demonstrated against
itself: **word error rate measures string agreement, not comprehension, and can
rank the most useful transcript last.** The task-success metrics were identical
across all models throughout and were never fooled.

## 6. Safety boundaries

- **No LLM clinical decisions.** Language models structure, classify and
  summarise. Every red-flag threshold is deterministic and rule-based in
  [`backend/services/ai.py`](../../backend/services/ai.py). An LLM never decides
  whether a patient is escalated.
- **Humans decide care.** The agent creates tasks and routes them. Diagnosis,
  prescription and treatment changes stay with licensed professionals.
- **No auto-enrolment.** An unrecognised number gets a polite "contact your care
  team", never an automatic account. Enrolment is a consented clinical act, not a
  side effect of sending a message.

## 7. Limitations

- One condition (hypertension) and one country's context.
- Small benchmark corpus — ‹n› speakers. The model comparison is fair (identical
  audio, identical scoring); the absolute numbers would move with more speakers.
- Rule-based intent detection is tuned to keywords in our scenarios, so it
  flatters all models equally. Fair comparison, not an absolute measure.
- SQLite on an ephemeral container filesystem: fine for a demo, needs Postgres
  before a pilot.
- Proactive reminders outside WhatsApp's 24-hour service window require
  pre-approved message templates — not yet configured.

## 8. Where this goes

This is one slice of a larger product: an AI-native operating system for African
clinics covering intake, triage, documentation, claims, pharmacy, labs and
referrals. This codebase deliberately implements only patient access and care
coordination — the wedge, not the whole system.

The immediate next steps are more speakers and accents, Ga as a fourth language
set, the noisy-condition comparison, and a clinic pilot with real patients under
ethics approval.
