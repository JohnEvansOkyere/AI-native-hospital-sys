# Code-Switch Speech Benchmark — VeloxaCare

**MLC (Africa) × Intron Agentic Voice AI Challenge**  
Generated 2026-08-04 from `results/transcripts.csv`

## What was measured

- **19 recordings** from **1 speaker(s)**, 76 transcriptions across 4 models
- Language sets: English (control), Twi–English, Pidgin–English
- Noise conditions: quiet
- Scripted utterances from a Ghanaian hypertension-care conversation; no real patient data. Written consent per speaker, de-identified by speaker ID.

> **Sample-size caveat.** This is a small corpus. Treat every number below as indicative, not as a general claim about these models. The comparison between models is fair — identical audio, identical scoring — but the absolute values would move with more speakers.

## Why not just word error rate

A misheard digit in this product is not a string-distance statistic, it is a clinical decision:

> *"Me BP yɛ **one-sixteen** over seventy-eight"* → 116/78 → **green**  
> *"Me BP yɛ **one-sixty** over seventy-eight"* → 160/78 → **red**

So every model is scored on what the agent *does* with the transcript: whether the blood pressure survives, whether the escalation decision matches, and whether the right intent is detected. The intent and escalation logic is rule-based and identical for every model, so the comparison stays fair even where those rules are imperfect.

## Overall

| Model | n | WER | BP extraction | Escalation correct | Intent | Median latency |
|---|---:|---:|---:|---:|---:|---:|
| Cartesia Ink | 19 | 0.412 | 100% | 100% | 84% | 1.2s |
| Local faster-whisper (`base`) | 19 | 0.527 | 83% | 100% | 68% | 2.0s |
| Intron Sahara | 19 | 0.510 | 33% | 33% | 53% | 3.7s* |
| sahara_en | 19 | 0.407 | 67% | 67% | 74% | 6.0s |

\* Latency excludes our client's self-imposed rate-limit sleep (2.1s/call for Sahara's 30 req/min cap), which is our throttle, not the model's response time. Latency was measured over a consumer connection in Ghana and is network-dominated — treat it as observational.

## By language set

### English (control)

| Model | n | WER | BP | Escalation | Intent |
|---|---:|---:|---:|---:|---:|
| Cartesia Ink | 5 | 0.068 | 100% | 100% | 100% |
| Local faster-whisper (`base`) | 5 | 0.068 | 100% | 100% | 100% |
| Intron Sahara | 5 | 0.054 | 100% | 100% | 100% |
| sahara_en | 5 | 0.054 | 100% | 100% | 100% |

### Twi–English

| Model | n | WER | BP | Escalation | Intent |
|---|---:|---:|---:|---:|---:|
| Cartesia Ink | 9 | 0.704 | 100% | 100% | 89% |
| Local faster-whisper (`base`) | 9 | 0.689 | 100% | 100% | 78% |
| Intron Sahara | 9 | 0.994 | 0% | 0% | 0% |
| sahara_en | 9 | 0.693 | 33% | 33% | 56% |

### Pidgin–English

| Model | n | WER | BP | Escalation | Intent |
|---|---:|---:|---:|---:|---:|
| Cartesia Ink | 5 | 0.229 | 100% | 100% | 60% |
| Local faster-whisper (`base`) | 5 | 0.696 | 50% | 100% | 20% |
| Intron Sahara | 5 | 0.095 | 50% | 50% | 100% |
| sahara_en | 5 | 0.247 | 100% | 100% | 80% |

## Code-switch penalty

Degradation from the English control to code-switched speech. This isolates the variable the challenge exists to measure — the English set is what makes it attributable to code-switching rather than to accent or recording conditions.

| Model | English WER | Code-switched WER | Penalty |
|---|---:|---:|---:|
| Cartesia Ink | 0.068 | 0.466 | **+0.398** |
| Local faster-whisper (`base`) | 0.068 | 0.692 | **+0.624** |
| Intron Sahara | 0.054 | 0.544 | **+0.490** |
| sahara_en | 0.054 | 0.470 | **+0.416** |

## Escalation flips (safety-relevant)

**6 case(s)** where a transcription error changed the clinical decision. These are the failures that matter most.

| File | Model | True BP | Heard | True risk | Decided |
|---|---|---|---|---|---|
| `S01_P05_quiet.m4a` | Intron Sahara | 90/60 | — | **green** | **none** |
| `S01_T06_quiet.m4a` | Intron Sahara | 116/78 | — | **green** | **none** |
| `S01_T06_quiet.m4a` | sahara_en | 116/78 | — | **green** | **none** |
| `S01_T07_quiet.m4a` | Intron Sahara | 160/100 | — | **red** | **none** |
| `S01_T07_quiet.m4a` | sahara_en | 160/100 | — | **red** | **none** |
| `S01_T09_quiet.m4a` | Intron Sahara | 175/110 | — | **red** | **none** |

## Notable transcription errors

**`P04` · Local faster-whisper (`base`)** (WER 1.333)  
> Shed ina kugetan antar a' yun. A' kugetan antar. Shed ina kugetan antar a' kugetan antar.

**`T01` · Cartesia Ink** (WER 1.333)  
> Ane, ma nùm e djúnu inè anope ii.

**`T08` · Cartesia Ink** (WER 1.2)  
> Mepe se mi bu ki appointment ewo Dr. Men Sanchen o chi na anapa.

**`T01` · Intron Sahara** (WER 1.167)  
> Mepa wo kyɛw, me number no yɛ 059.

**`P03` · Local faster-whisper (`base`)** (WER 1.0)  
> Abeg mi ki muv mai apointu mego nes wik, tis dea, a travo goku maasi.

**`T01` · sahara_en** (WER 1.0)  
> Ané Manum Eduonu Enehan


## Method

- Scripts in `recording/scenarios.md`; `scenarios.csv` is generated from it, so the scoring reference always matches what speakers actually read.
- Recorded on ordinary phones. `make_manifest.py` flags clips too short for their script — clipped audio looks exactly like a model failure and produced one false result during development before the check existed.
- Spoken numbers are normalised to digits, and blood-pressure notation is canonicalised (`142/95` ≡ `142 over 95`) before WER. Without that, a model that recognises a reading *as* a blood pressure is penalised for writing it correctly — we hit exactly this and it inverted the ranking.
- Language hints: Sahara receives the per-set code (`en`/`tw`/`pcm`/`gaa`). Whisper variants and Cartesia have no Ghanaian codes to receive — Cartesia returns `HTTP 400: invalid language: tw` — so they run in English mode on code-switched audio by necessity, not by our choice. **That asymmetry is a finding, not a methodology flaw**, and it is the point of the exercise.
- The benchmark imports the live application's speech code (`backend/services/stt.py`) rather than reimplementing it, so the models measured are the models serving patients.

## Limitations

- 1 speaker(s) — accent and gender coverage is thin.
- Scripted speech under-represents real disfluency; the spontaneous set is the partial mitigation.
- The rule-based intent detector is tuned to keywords present in these scenarios, so it flatters all models equally. It is a fair *comparison*, not an absolute measure of agent quality.
- Latency was measured from Ghana on a consumer connection and is dominated by network conditions rather than model speed.
