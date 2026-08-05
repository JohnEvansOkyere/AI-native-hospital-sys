# MLC (Africa) × Intron Agentic Voice AI Challenge

VeloxaCare's entry. This file is the single source of truth for what the
challenge wants, what we've built, and what's left.

**Deadline: 6 August 2026.** Finalists announced 7 August at the workshop
(Main Plenary Hall). Submissions then carry into Intron's full Sahara
CodeSwitch Africa Challenge — deadline mid-September, winners 1 October.
So this is a 3-day sprint into a 6-week race.

- Challenge page: https://ml-collective-africa.github.io/dl-indaba-2026/workshop-challenge
- Team registration: https://forms.gle/RV43DXHAJCTYr98U7
- Intron docs: https://docs.voice.intron.io/docs
- API keys: https://voice.intron.io/v2/developers

## What they're asking for

Not a reminder bot, and not a transcription demo. Two halves:

1. **A voice-driven agent that takes a downstream action** — booking, triage,
   form-filling. Voice in, real action out.
2. **A benchmark across ≥3 speech models**, one of which must be an Intron
   Sahara API, on *code-switched* audio.

We run four: **Intron Sahara** (African-built), **Cartesia Ink** and **OpenAI
Whisper** (commercial), **local faster-whisper** (open weights, offline).

Most entries will nail half 1 and hand-wave half 2. The rubric weights
"code-switching performance" and "benchmark quality" heavily, so half 2 is
where this is won.

**Track:** Health.

### Deliverables

| # | Item | Status |
|---|------|--------|
| 1 | Solution description | ✍️ to write |
| 2 | Demo video (unlisted YouTube) | ✍️ day 3 |
| 3 | Code / technical docs | ✅ this repo |
| 4 | Benchmark report (3+ models) | ⏳ blocked on audio |
| 5 | Ethics & inclusion statement | 🟡 `benchmark/recording/consent_form.md` covers the practice; needs writing up |
| 6 | Benchmark audios *(optional, bonus)* | ⏳ blocked on recording day |

### Judged on

Real-world impact · code-switching performance · product quality · technical
execution · ethics, safety & inclusion.
Bonus for: strong benchmark design, low-resource language coverage,
offline/low-bandwidth capability.

Note the bonus criteria map onto things we already have: `local_whisper` runs
with no network at all (offline capability), and Ghanaian languages are as
low-resource as this challenge gets.

## Our angle

The differentiator is that we do **not** score on WER alone. VeloxaCare already
routes a patient by *why* they stopped taking medication (cost / forgot /
side-effect / ran out) and escalates on BP thresholds. So a transcription error
isn't an abstract WER delta — it's a patient who does or doesn't get escalated.

The benchmark therefore measures **downstream task success**:

| Metric | Why it matters |
|---|---|
| WER | Baseline, comparable to other work |
| BP extraction accuracy | Did the digits survive? |
| **Escalation correctness** | Does the heard BP produce the same red/amber/green decision? **Headline metric.** |
| Intent accuracy | Does the agent do the right thing from this transcript? |
| Code-switch penalty | Degradation on Twi/Pidgin vs the English control |
| Median latency | A clinic on a rural connection cares about speed too |

Latency matters because Cartesia sells speed and Sahara sells African language
coverage. Report both axes rather than a single ranking — the interesting result
is the tradeoff, not a winner.

`scenarios.md` T06 vs T07 is the argument in one slide: *"one-sixteen"* (116/78,
green) against *"one-sixty"* (160/100, red). One vowel decides an escalation.

A real result already observed in smoke-testing: local Whisper transcribed
"medicine" as **"men's son"** — badly wrong — yet the cost intent still routed
correctly to the NHIS escalation. Transcription failed; the task succeeded.
That's precisely why task-success metrics beat WER, and it belongs in the report.

## What exists now

```
backend/services/stt.py  Shared STT layer: Sahara / Cartesia / OpenAI / local faster-whisper
backend/main.py          POST /api/patients/{id}/voice, GET /api/stt/status, GET /api/voice/{file}
frontend/src/App.tsx     Mic button, language selector, voice bubbles w/ model + latency
benchmark/stt_providers.py   Thin re-export of backend/services/stt.py
benchmark/run_benchmark.py   Transcribe + score, writes results/{transcripts,summary}.csv
benchmark/probe_languages.py Verifies which language codes each key actually accepts
benchmark/recording/     Consent form, metadata sheet, 21 scenarios, recording guide
```

**The benchmark imports the app's STT code rather than reimplementing it.** That
is deliberate and worth a line in the report: the models we benchmark are
literally the models serving patients, same request parameters and all.

Verified end to end: a spoken *"one sixty over one hundred"* → transcript →
BP extraction → escalation fired → patient flipped green to red → clinical reply
sent. Round trip ~4s on local Whisper `base`, CPU only.

### Language support — this is the headline

Confirmed in Intron's docs table: **`tw`** (Twi), **`ak`** (Akan), **`pcm`**
(Pidgin) and **`gaa`** (Ga) are all supported input languages. The table lists
single languages only — no explicit `xx-en` pair codes — so a code-switched
utterance goes under its non-English code and Sahara's code-switching handling
does the rest.

Whisper's ~99 languages contain **none** of those four, and Cartesia's
`ink-whisper` inherits that gap. So:

> Of the four models, **only the African-built one can be told what language the
> patient is speaking.** The other three run in English mode on Twi and Pidgin
> audio out of necessity, not by our choice.

That sentence is the benchmark report's opening paragraph, and it's the literal
thesis of the workshop this challenge sits inside ("Whose Intelligence?").

Run `probe_languages.py` once you have keys and cite the measurement rather than
the assumption — documented ≠ enabled on your key, and "we tested and the
endpoint rejects `tw`" is a result while "we assumed" is not.

## Measured findings so far

Run: `probe_languages.py`, 3 Aug 2026, synthetic espeak clip saying
*"Me BP no yɛ one sixteen over seventy eight."*

**⚠️ Caveat to carry into the report:** this clip is machine-synthesised English
TTS, not a human Ghanaian speaker. It is adequate for testing *which language
codes an API accepts* and nothing else. Every accuracy claim below must be
re-measured on the human recordings before it goes in the report.

### 1. Cartesia rejects every Ghanaian language — measured, not assumed

| Code | Result |
|---|---|
| `en` | ✅ accepted |
| `sw` (Swahili) | ✅ accepted |
| `tw` (Twi) | ❌ `HTTP 400: invalid language: tw` |
| `ak` (Akan) | ❌ `HTTP 400: invalid language: ak` |
| `pcm` (Pidgin) | ❌ `HTTP 400: invalid language: pcm` |
| `gaa` (Ga) | ❌ `HTTP 400: invalid language: gaa` |

Explicit 400s with the language named — the cleanest possible citation. Note the
shape of it: **the only African language Cartesia accepts is Swahili.** Intron's
docs table lists all four Ghanaian codes. That contrast is the report's opening.

### 2. The 116 → 160 digit flip, caught on a live commercial API

Cartesia transcribed *"one sixteen over seventy eight"* as **"160 Nova 78"**.

116/78 is **green**. 160/78 is **red**. The exact minimal pair `scenarios.md`
T06/T07 was designed around, failing on the first real API call of the project —
and it fails in the dangerous direction, manufacturing an escalation that the
patient's actual reading doesn't warrant.

Do not overclaim this: it's synthetic audio and one sample. Treat it as the
hypothesis the recording day is designed to test, not as a result.

### 3. English control baseline established (real human audio) ✅

Speaker S01, 5 scripted English utterances, quiet condition, 3 Aug 2026:

| provider | n | WER | BP acc | escalation acc | intent acc | median latency |
|---|---|---|---|---|---|---|
| **Intron Sahara** | 5 | **0.054** | 1.0 | 1.0 | 1.0 | ~4.8s† |
| Cartesia (`ink-whisper`) | 5 | 0.068 | 1.0 | 1.0 | 1.0 | 2.2s |
| local faster-whisper `base` | 5 | 0.068 | 1.0 | 1.0 | 1.0 | 2.4s |

† The runner reports 6.9s for Sahara, but that includes the client's 2.1s-per-call
self-throttle for the 30 req/min limit. Report the corrected figure and say why.

**Sahara wins the drug name — the clinically load-bearing word.** On E05 it is the
only model that transcribes *amlodipine* correctly; Cartesia gives "amlody pain"
and local Whisper "amlodipian". A garbled drug name in a refill request is a real
clinical failure, and the African-built model is the one with the pharmaceutical
vocabulary. Worth a paragraph of its own.

#### Methodology correction — worth reporting, not hiding

The first run scored Sahara **worst** (WER 0.108). It wasn't. Sahara heard
*"one forty-two over ninety-five"* and wrote **`142/95`** — recognising it as a
blood pressure — while the others wrote `142 over 95`. Our normaliser tokenised
`142/95` as one token against three, so WER punished the model that had
understood the content best.

`normalize()` now canonicalises BP notation before scoring, and Sahara moves from
0.108 (worst) to 0.054 (best). Nothing about the audio or the models changed.

This belongs in the report as a finding, not a footnote: **it is the benchmark's
own thesis demonstrated against itself.** WER measures string agreement, not
comprehension, and it can rank the most useful transcript last. Task-success
metrics — BP extraction, escalation correctness — were identical at 1.0 across
all three models throughout, and were never fooled.

**This is the number everything else is measured against.** On clean
Ghanaian-accented English both models are perfect on task success, so any
degradation on the Twi and Pidgin sets is attributable to code-switching rather
than to accent, scoring code, or recording setup. That's what makes the
code-switch penalty a real measurement instead of an artefact.

Secondary finding worth reporting: the only substantive error either model made
was the **drug name** — `amlodipine` → "amlody pain" (Cartesia) / "amlodipian"
(local). General-purpose ASR lacks pharmaceutical vocabulary independent of
language, and a garbled drug name in a refill request is a genuine clinical
failure. The rule-based intent detector still routed it correctly, which is the
WER-isn't-the-metric argument in miniature.

**Latency caveat:** Cartesia measured 1125ms and 3272ms median on two runs of the
same files. That spread is the network from Ghana, not the model. Report latency
as observed-in-context with repeated trials, never as a model property.

**Process finding for the write-up:** the first take of E02/E04/E05 was clipped —
the recording stopped before the sentence ended. Both models truncated at exactly
the same word, which is the tell: independent models don't fail identically.
Uncaught, it would have been written up as a model failure. `make_manifest.py`
now flags files that are too short for their script.

### 4. Offline capability demonstrated, not claimed ✅

`local_whisper` is **faster-whisper** running Whisper's openly-released weights
on the CPU — not OpenAI's hosted API. No account, no key, no network. The `base`
model is a 142MB one-time download; after that it is fully self-contained.

Verified 3 Aug 2026 with every API key unset and `HF_HUB_OFFLINE=1`:

```
provider : local_whisper_base
transcript: checked my blood pressure today. It was 142 over 95.
→ BP 142/95 extracted, escalation amber — correct, entirely offline
```

The challenge lists offline/low-bandwidth capability as an explicit bonus
criterion. This is the deployment argument for a district clinic with
intermittent connectivity: the escalation logic keeps working when the network
doesn't. It's also why the demo can't hard-fail — the provider chain
(Sahara → Cartesia → OpenAI → local) always has a floor that needs no internet.

Note the distinction for the report: **OpenAI `whisper-1` (hosted API, needs
`OPENAI_API_KEY`) and local faster-whisper (open weights, needs nothing) are two
different rows.** Same model family, completely different deployment story.

### 5. Intron Sahara needs an integrator account — BLOCKING

The key authenticates. The endpoints refuse it on account tier:

```
HTTP 403 {"message":"permission denied,you need an integrator account
          to use this endpoint","status":"Error"}
```

Same on `/file/v1/upload/sync` and `/file/v1/upload`, and on every language code
including plain `en` — so this is an **account-tier** issue, not language support
and not a malformed key.

(An earlier `access-key error` 403 was a truncated key — the key begins with a
literal `-` that was lost in copying. Worth remembering if it recurs.)

Ask Intron to enable an integrator account. Sahara is a *mandatory* model for
this challenge, so this is the highest-priority task. Draft email is in the
session scratchpad.

## The plan

### Day 1 — today ✅ (mostly done)

- [x] Voice pipeline end to end, degrading gracefully with no API key
- [x] Recording kit ready
- [x] Language codes confirmed against docs
- [x] Cartesia key working, language support measured
- [x] `probe_languages.py` run against both APIs
- [ ] **Register the team** → https://forms.gle/RV43DXHAJCTYr98U7
- [ ] **🔴 Unblock the Intron key** (403 on everything — see findings above).
      Escalate on all three channels at once, it's the mandatory model:
      voice@intron.io · workshops@mlcollective.org (Busayo Awobade is Intron +
      an organiser) · the Adaptation Lab credit form on the challenge page
- [ ] **Naturalise the Twi scripts** in `scenarios.md` — a non-native speaker
      drafted them. Mirror every edit into `scenarios.csv` or the reference
      transcripts won't match what was said and every WER number is garbage.
- [ ] **Line up 3–5 speakers** for tomorrow

### Day 2 — recording + benchmark

- [ ] Record per `recording/RECORDING_GUIDE.md`. Signed consent per speaker,
      speaker IDs not names, one file per line.
      **Minimum viable: 2 speakers × 21 lines quiet + 5 noisy.** More is better,
      but a small sample stated honestly beats a large one hand-waved.
- [ ] Drop the files in **`benchmark/audio/`** named `{speaker}_{scenario}_{noise}.{ext}`
      (e.g. `S01_T06_quiet.m4a`), then:
      ```bash
      cd benchmark
      python make_manifest.py --dry-run   # validate names, check coverage
      python make_manifest.py             # writes manifest.csv
      python run_benchmark.py --manifest manifest.csv --audio-dir audio --out results \
          --providers sahara,cartesia,openai,local
      ```
- [ ] Read `summary.csv`, write the analysis

### Day 3 — submit

- [ ] Demo video: speak Twi–English into the WhatsApp pane, watch the escalation
      fire on the dashboard. Show the same utterance through two models.
- [ ] Solution description, benchmark report, ethics statement
- [ ] Submit

## Running the voice demo

```bash
./start.sh                      # dashboard :5173, API :8000
```

Speech provider is chosen automatically: Sahara → Cartesia → OpenAI → local. Pin
one with `STT_PROVIDER=`, which is how you demo the same utterance through two
models back to back. With no keys at all it falls back to local faster-whisper;
with nothing installed the bot says "I couldn't hear that, please type it"
rather than failing. Set `WHISPER_LOCAL_MODEL=medium` (or `large-v3`) for final
benchmark runs — `base` is the fast default for interactive use.

```bash
export INTRON_API_KEY=...       # Sahara
export CARTESIA_API_KEY=...     # Cartesia Ink
export OPENAI_API_KEY=...       # hosted whisper-1
export STT_PROVIDER=sahara      # optional: pin one
```

**Demo idea worth 30 seconds of video:** send the *same* Twi–English voice note
twice, pinned to `sahara` then to `cartesia`, and show the two transcripts and
two escalation outcomes side by side in the chat pane. That's the entire thesis
in one interaction, with no slides.

## Ethics notes (for deliverable 5)

- Scripted utterances, no real patient data.
- Written consent per speaker before recording; separate opt-in for submitting
  audio to the challenge.
- Speaker IDs (`S01`), never names, in filenames and metadata.
- Voice notes stored under generated filenames, never client-supplied ones.
- **No LLM clinical decisions.** BP thresholds and escalation are rule-based in
  `ai.py:assess_bp_risk`. Speech models transcribe; they never decide. This is
  the same boundary the rest of VeloxaCare holds, and it's a defensible answer
  when judges ask about safety.
- Known limitation to state plainly: rule-based intent detection is tuned to
  keywords that appear in our scenarios, so it flatters all providers equally.
  It's a fair *comparison*, not an absolute measure of agent quality.
