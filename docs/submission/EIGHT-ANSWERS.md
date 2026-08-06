# MLC (Africa) × Intron — Submission Answers

Deadline extended to **4pm WAT**. Log in with the registered address
`johnevansokyere@gmail.com`, token 254869. One submission per token.

**Form limit: ~50 words per answer.** Paste the boxed answers below. Longer
versions follow for the pitch, the report and any follow-up questions.

---

## The one statistic — cite it correctly

> Buabeng KO, Matowe L, Plange-Rhule J. "Unaffordable drug prices: the major
> cause of non-compliance with hypertension medication in Ghana."
> *J Pharm Pharm Sci* 2004;7(3):350–352.

Komfo Anokye Teaching Hospital; patients interviewed Dec 2001–Apr 2002. **93%**
were non-compliant, and **96% of the non-compliant** cited unaffordable drug
prices as the main reason.

**Quote it as "one Ghanaian study (2004)", never as "in Ghana, 96% of patients."**
The data is from 2001–02, from a single hospital, and predates the NHIS. It is
still the sharpest published statement of the cost mechanism, and it is honest
to say the affordability picture has changed while the mechanism has not.

**Drop the "55%" figure.** It is asserted in our own docs without a source and it
is not from this study, which reports 93%. Do not use a number we cannot cite.

---

## 1. Problem (47 words)

My mother nearly died after missing her diabetes medicine. In Ghana, cost — not
forgetting — drives patients off chronic treatment: in one Ghanaian study, 96% of
non-compliant hypertensives blamed drug prices. Patients never tell the clinic.
Between visits nobody is listening, and blood pressure climbs silently.

## 2. Target users (49 words)

Anyone whose care continues after they leave the building: a hypertension patient
on daily medication, a dental patient due a recall, someone waiting on results.
Many read with difficulty or speak Twi–English rather than formal English, so
they answer by voice. And the clinics that lose sight of them.

## 3. How it solves the problem (46 words)

Daily WhatsApp check-ins; patients reply by text or voice note in their own
language. The agent detects *why* someone stopped — cost, forgot, side effect,
ran out — and routes each differently. Cost opens an NHIS-alternative workflow.
Fixed rules escalate readings ≥160/100 to a human immediately.

## 4. Code-switching support (46 words)

Patients speak Twi or Pidgin with the numerals and drug names in English —
exactly where recognition fails consequentially. Our benchmark spans 21 scenarios
in English, Twi–English and Pidgin–English, including a minimal pair:
"one-sixteen" (green) against "one-sixty" (red). One vowel decides a clinical
escalation.

## 5. Sahara API usage (47 words)

Sahara is our production speech provider, first in the live chain. The benchmark
imports the app's speech layer, so we measure the model actually serving
patients. We test two configurations, `tw`/`pcm` and `en`. Sahara alone accepts
Ghanaian language codes; Cartesia returns HTTP 400 for all four.

## 6. Agentic behaviour (48 words)

Voice in, action out. A voice note is transcribed, intent detected, blood
pressure extracted, a fixed clinical rule applied, escalation raised, care team
alerted and the outcome tracked — round trip about four seconds. It also books
appointments, handles refills, and answers by voice when addressed by voice.

## 7. Technical overview (247 words — field allows ~250)

FastAPI + SQLite/Turso backend, React dashboard live over WebSockets, Meta
WhatsApp Cloud API transport, Groq models for classification and summarisation.
Four architecture decisions carried real tradeoffs.

**Rule-based escalation, not LLM judgement.** Blood-pressure thresholds and the
cost/side-effect rules are fixed code; the LLM never decides. We traded recall —
a model would catch phrasings our rules miss — for determinism, auditability and
a defensible clinical boundary. In health that trade is not close: better to miss
an unusual wording than let a model silently withhold an escalation.

**One inbound choke point.** WhatsApp, the simulator, text and voice all call
`ingest_patient_message()`. Per-channel handlers would have been quicker
and would have drifted; instead channel quirks are normalised at the
boundary and one function carries the complexity. The payoff: a demo provably
exercises the production path, and a new transport (SMS, USSD, IVR) inherits
escalation for free.

**A channel-blind speech layer.** `stt.py` takes audio and returns text plus
provenance, knowing nothing about patients, messages or channels. That costs us
context we could exploit — a patient's known language must be passed in, not
looked up. In exchange the same layer will serve clinician dictation, and our
benchmark imports it rather than reimplementing it, so published numbers describe
the shipping system.

**An offline floor.** The provider chain ends in faster-whisper on CPU: slower,
least accurate, too large for serverless. Accepted, because it means no key, no
network, no hard failure — a clinic whose connection drops still gets correct
escalations on most messages.

## 8. Ethics and inclusion (47 words)

Scripted utterances, no patient data. Written consent per speaker, de-identified
IDs, separate opt-in for releasing audio. All escalation is rule-based; a
licensed human decides everything clinical. Voice-first Twi–English serves
patients who read with difficulty. We state our limits: small corpus, Twi scripts
await native-speaker sign-off.

---
---

# Long versions — for the pitch, interviews and follow-up questions

## 1. Problem

My mother nearly died after missing her diabetes medicine. That is why this
product detects the *reason* a patient stopped, not just the fact.

In Ghana, more than half of patients with chronic conditions stop taking their
medication within weeks of leaving the clinic, and the reason is usually not
forgetting. In one Ghanaian study (Buabeng et al., 2004), 96% of non-compliant
hypertensive patients cited unaffordable drug prices as the main cause — and
they told nobody. There is no moment in the care pathway where a patient can say
"I cannot afford this month's refill," so it is recorded as non-compliance and
answered with more education, when it was poverty and a cheaper NHIS-covered
alternative existed.

Between visits the clinic has no signal at all. Blood pressure climbs silently
and the patient returns with a preventable complication.

The access barrier compounds it. Patients who most need follow-up are often those
who read with difficulty or do not use formal English. A text-only, English-only
system excludes exactly the people it should reach — and patients who send voice
notes are disproportionately those patients.

## 2. Target users

**Patients whose care continues after the visit.** The defining attribute is not
age, it is an open loop: a hypertension patient on daily medication, a dental
patient due a six-month recall, a post-procedure patient nobody checks on, a
diagnostics patient waiting on results. In Ghana that spans every adult age
group, and WhatsApp reaches all of them.

**What they have in common is how they answer.** Many read with difficulty, or
speak Twi–English and Pidgin–English rather than formal English. A text-only,
English-only service excludes exactly the people who most need follow-up — which
is why the voice channel is the product, not a feature.

**Clinical staff** at small and mid-sized private clinics, specialist practices
and pharmacies: the nurse who has no time to phone everyone, and the doctor who
discovers a three-month drop-off at the consultation with no record of what
happened in between.

**Our beachhead is hypertension** — lifelong, cheap drugs, an unambiguous
clinical threshold, and a result measurable within 60 days. The wider set above
is where the same loop goes next, and our own pipeline confirms the pull: a
dental clinic, a multi-specialty diagnostics centre and an employee-health
provider all approached us before any chronic-care clinic did.

## 3. How it solves the problem

VeloxaCare follows every chronic patient home over WhatsApp — no app to install.
Daily medication check-ins, weekly blood-pressure requests, replies by text or
voice note in the patient's own language.

What matters is what happens after a "no." The agent determines *why* — `cost`,
`forgot`, `side_effect`, `ran_out` — and routes each reason differently:

- **cost** → escalates to the care team, opens an NHIS-covered-alternative
  workflow, so the patient is not lost and the pharmacy does not lose the sale
- **side effect** → straight to a human
- **forgot** → adjusts the reminder
- **ran out** → refill request

Danger signs are detected by fixed clinical rules, never by a model: ≥160/100
escalates immediately; cost or side effect escalates after 2+ occurrences in 14
days. Each morning the doctor receives one page ranking every patient by risk,
with the reason — zero extra work for nurses.

## 4. Code-switching support

Ghanaian patients do not switch language cleanly. They speak a Twi or Pidgin
matrix sentence with the clinically load-bearing tokens — **numerals and drug
names** — in English:

> *"Sika nni hɔ nti — I can't afford the lisinopril this month."*
> *"Me BP yɛ one-sixteen over seventy-eight."*

The benchmark is built around that boundary: 21 scripted scenarios in three sets
— English control (E), Twi–English (T), Pidgin–English (P) — recorded by
consented Ghanaian speakers in quiet and noisy conditions. Numerals and drug
names stay English in every set, because that is what speakers do and it is
exactly where recognition fails consequentially.

The corpus contains a deliberate minimal pair, T06 vs T07: *"one-sixteen"*
(116/78, green) against *"one-sixty"* (160/100, red). A commercial API failed
this pair in pre-testing, in the dangerous direction.

We measure a **code-switch penalty**: degradation on T and P relative to the E
control for the same speakers, isolating code-switching from accent, recording
setup and scoring code.

## 5. Sahara API usage

Intron Sahara is the production speech provider — first in the live agent's
chain, not a benchmark-only column. The benchmark **imports the application's
speech layer** (`benchmark/stt_providers.py` re-exports
`backend/services/stt.py`), so the models measured are literally the models
serving patients, with identical request parameters.

We evaluate Sahara in **two configurations**, which turned out to be the most
important methodological choice in the study:

- `sahara` — sends the set's non-English code (`tw`, `pcm`)
- `sahara_en` — pins the English model regardless of what is spoken

Sahara is the only system tested that can be *told* what language a Ghanaian
patient is speaking. Its documented inputs include `tw`, `ak`, `pcm`, `gaa`.
Cartesia returns an explicit `HTTP 400: invalid language` for all four while
accepting Swahili; Whisper's ~99 languages contain none of them.

**Documented is not shipped, and we say so.** Intron confirmed the
**Akan–English code-switch pair** had not shipped at time of testing (rolling out
the week of 10 August 2026). We measured that the monolingual `tw` model returns
an *empty* transcript on Twi–English speech, dropping the English half where the
numerals and drug names live, while the same audio under `en` yields usable text.
That is why both configurations are benchmarked. The finding is sharper, not
weaker: even the African-built system does not yet expose the code-switch pair
Ghanaian patients speak — and it is the only one building it.

## 6. Agentic behaviour

Voice in, real action out. A voice note triggers a closed loop:

```
voice note → transcribe (provenance recorded) → detect intent
    → extract BP → apply fixed clinical rule → decide escalation
    → alert the care team → update patient risk → track outcome
```

Verified end to end: a spoken *"one sixty over one hundred"* → transcript → BP
extraction → escalation fired → patient flipped green to red on the dashboard →
clinical reply sent, round trip ≈4s.

The agent books and reschedules appointments, handles refill requests, and
answers in **the modality it was addressed in** — a voice note gets a spoken
reply, because patients who send voice are disproportionately those who read with
difficulty.

Provenance is recorded per message (`stt_provider`, `stt_language`,
`stt_latency_ms`), so every AI action is auditable.

## 7. Technical overview

- **Backend** FastAPI + SQLite (Turso/libSQL in production); one inbound choke
  point, `ingest_patient_message()`, that every channel calls
- **Speech-to-text** a channel-blind provider layer: Intron Sahara → Cartesia Ink
  → OpenAI Whisper → local faster-whisper, with automatic fallback
- **Text-to-speech** the mirror of the above; callers declare playable formats
- **LLM** Groq (Llama) for classification and summarisation only
- **Frontend** React + Vite + TypeScript, live over WebSockets
- **Transport** Meta WhatsApp Cloud API
- **Benchmark** scores WER plus BP extraction, escalation correctness, intent,
  code-switch penalty and latency; manifests are generated from filenames and
  flag recordings too short for their script

**Graceful degradation is a design property.** With no keys and no network the
system falls back to local faster-whisper — open weights, CPU, fully offline —
and the escalation logic keeps working.

**No LLM clinical decisions.** All red-flag detection is rule-based in
`ai.py:assess_bp_risk`.

## 8. Ethics and inclusion

**Data.** All utterances are scripted; no real patient data. Written consent per
speaker before recording, with a separate opt-in for releasing audio. Speakers
identified only by code (`S01`), never by name. Production voice notes stored
under generated filenames. Recordings and keys are never committed.

**Safety.** The AI structures, classifies and summarises. Every escalation
threshold is deterministic, and a licensed human decides everything clinical.

**Inclusion.** Voice-first in Twi–English and Pidgin–English serves patients who
read with difficulty or do not use formal English. We state the asymmetry rather
than hiding it: recognition of Ghanaian languages is ahead of synthesis. Intron
TTS has **no Twi, Akan or Ga voice** — only Pidgin plus non-Ghanaian English
accents — while Sahara STT does list `tw`, `ak`, `gaa`.

**Limitations we state rather than bury.**
- Small corpus; absolute figures are indicative. The *comparison* is controlled —
  identical audio, preprocessing, normalisation, scoring code and decision rules.
- The rule-based intent scorer is tuned to these scenarios and flatters every
  provider equally.
- The Twi scripts were drafted and revised by non-native speakers and carry
  outstanding review questions; native-speaker sign-off is required before these
  numbers are cited as a general claim about Twi ASR.
- Latency is network-dominated and is not a model property.
