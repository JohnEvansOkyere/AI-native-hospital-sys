# VeloxaCare — Solution Description

**MLC (Africa) × Intron Agentic Voice AI Challenge · Deep Learning Indaba 2026**
**Track:** Health
**Team:** Veloxa Technology Limited (Ghana)

> Final. Benchmark numbers are from `benchmark/results_3speaker_final/`
> (57 recordings, three speakers); full report:
> `benchmark/report/veloxacare_benchmark.pdf`.

---

## 1. The problem

In Ghana, the number one reason patients stop taking chronic medication is
**cost, not forgetting** — 96% of non-compliant patients in one Ghanaian
study (Buabeng et al., 2004). Almost every digital adherence tool
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
| **Intron Sahara** | African-built, code-switch aware | ✅ documented `tw` `ak` `pcm` `gaa` † |
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

Full report: [`benchmark/report/veloxacare_benchmark.pdf`](../../benchmark/report/veloxacare_benchmark.pdf).
Raw scores: `benchmark/results_3speaker_final/`.

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

† **Documented is not the same as shipped, and we say so.** Intron confirmed the
**Akan–English code-switch pair** — precisely what our utterances need — had not
shipped at time of testing (rolling out the week of 10 Aug 2026). We also
measured that the monolingual `tw` model returns an *empty* transcript on
Twi–English speech, dropping the English half where the numerals and drug names
live, while the same audio under the `en` hint yields usable text and correct BP
extraction. That is why we benchmark Sahara in two configurations rather than
one: **the choice of language hint moves the result more than the choice of model
does.** The honest version of the headline is therefore sharper, not weaker —
even the African-built model does not yet have the code-switch pair Ghanaian
patients actually speak, and it is the only one of the four building it.

**English control (15 utterances, three speakers):** all three hosted models
reach **100% escalation correctness**; the offline model reaches 67%. WER is
0.071 (Cartesia), 0.130 (both Sahara configurations) and 0.139 (faster-whisper).
This set exists to establish that later degradation is attributable to
code-switching rather than to accent or recording conditions — and because the
hosted systems are equivalent here, it does. Sahara was also the only model to
transcribe *amlodipine* correctly, the clinically load-bearing word in a refill
request.

**Code-switched sets** (57 recordings, three speakers, 228 transcriptions):

| Model | Twi–En WER | Twi–En esc. | Pidgin–En WER | Pidgin–En esc. | Code-switch penalty |
|---|---:|---:|---:|---:|---:|
| Sahara `(tw/pcm)` | 0.949 | **0%** | 0.085 | 67% | +0.510 |
| Sahara `(en)` | 0.607 | **78%** | 0.354 | 83% | **+0.387** |
| Cartesia Ink | 0.647 | 67% | 0.493 | 50% | +0.521 |
| faster-whisper | 0.791 | 56% | 0.676 | 67% | +0.611 |

Overall across all sets, **Sahara pinned to English is the best system on
escalation correctness (83%)**, ahead of Cartesia (67%) and faster-whisper (61%).
Three of four configurations reach **100% on the English control** (faster-whisper
67%), which is what makes the degradation above attributable to code-switching
rather than to accent, recording setup or scoring code.

**Sahara is also the most noise-robust by a wide margin.** Its WER is essentially
flat from quiet to noisy (0.506 → 0.504; 0.417 → 0.405 under the English hint),
while Cartesia degrades 0.406 → 0.717 and faster-whisper 0.557 → 0.760. For a
clinic waiting room that matters more than a headline average.

**The headline is the first two rows.** Same API, same audio — pinning Sahara to
English instead of Twi moves escalation correctness on Twi–English from 0% to
60%. The monolingual Twi model returns an *empty* transcript on much of this
audio: it does not emit the English fragments, and in this domain the English
fragments are the blood-pressure numerals and the drug names. **The language hint
moves the result more than the choice of model does.**

**Escalation flips** (transcript changed the red/amber/green decision), out of 57:

| Model | Flips | Missed escalations | False alarms |
|---|---:|---:|---:|
| Sahara `(tw/pcm)` | 11 | **5** | 0 |
| Sahara `(en)` | 3 | 1 | 1 |
| Cartesia Ink | 5 | 0 | 1 |
| faster-whisper | 7 | 2 | 0 |

Direction matters clinically and we report it separately: a false alarm costs a
nurse a phone call, a missed escalation is a reading of 160/100 or above that
never reaches anyone. No configuration produced a false alarm in this corpus.

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
- Small benchmark corpus — **57 recordings from three speakers**, unevenly
  distributed (28 / 19 / 10), so the aggregate is weighted towards one speaker
  and speaker effects cannot be fully separated from system effects. Three calls
  failed with network errors and are excluded from their aggregates.
- **Latency is not reported.** A second benchmark run shared Sahara's
  30 requests/minute limit during this execution, so per-call timings measure
  contention, not model speed.
  The model comparison is nevertheless controlled: identical audio, identical
  preprocessing, identical normalisation, identical scoring code and identical
  decision rules.
- Audio arrived in mixed encodings (Opus-in-`.m4a` from some handsets, AAC from
  others) and one API rejects the former outright. All audio is transcoded to
  16 kHz mono before scoring so every model receives identical input. This is
  reported because an earlier run failed on every recording from two speakers
  for exactly this reason, and would — uninspected — have been written up as
  catastrophic model failure rather than a container mismatch.
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
