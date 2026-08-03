# VeloxaCare

**A WhatsApp voice agent for chronic-disease care in Ghana — that hears how Ghanaians actually speak.**

In Ghana, the number one reason patients stop taking chronic medication is
**cost, not forgetting** — 96% in one study. So VeloxaCare doesn't just track
yes/no adherence. It detects *why* a patient slipped — cost, forgot,
side-effect, ran out — and routes each reason to a different action. Cost
barriers escalate to the care team and trigger an NHIS-covered-alternative
workflow.

Patients talk to it by **voice note, in the language they actually use** —
Twi–English and Pidgin–English code-switching included.

```
voice note → transcribe → detect intent → extract BP
          → decide escalation → alert the care team → track outcome
```

## Quickstart

```bash
cp .env.example .env      # keys are optional — see below
./start.sh                # dashboard :5173 · API :8000
```

Open http://localhost:5173, pick a patient, choose a voice language, and hold
the mic. **No API keys required** — it falls back to local speech recognition
that runs entirely offline.

## Layout

| Path | What's in it |
|---|---|
| [`backend/`](backend/) | FastAPI service — routes, SQLite, bot logic, speech-to-text |
| [`frontend/`](frontend/) | React + Vite dashboard and WhatsApp simulator |
| [`benchmark/`](benchmark/) | Code-switch speech benchmark ([README](benchmark/README.md)) |
| [`docs/`](docs/) | [Architecture](docs/ARCHITECTURE.md) · [Demo script](docs/DEMO.md) · [Challenge entry](docs/CHALLENGE.md) |
| [`docs/business/`](docs/business/) | Pitch, GTM, long-term product concept |

Agent guidance lives in [CLAUDE.md](CLAUDE.md) / [AGENTS.md](AGENTS.md).

## The speech benchmark

Ghanaian patients code-switch mid-sentence. Speech models trained on clean
monolingual English break exactly where they're needed most — and a misheard
digit isn't a WER statistic, it's a clinical decision:

> *"Me BP yɛ **one-sixteen** over seventy-eight"* → 116/78, **green**
> *"Me BP yɛ **one-sixty** over seventy-eight"* → 160/78, **red**

So we score four speech models on **downstream task success**, not just word
error rate: BP extraction, **escalation correctness**, intent accuracy, and the
degradation from English to code-switched speech.

| Model | Kind | Ghanaian language support |
|---|---|---|
| Intron Sahara | African-built | ✅ `tw` `ak` `pcm` `gaa` |
| Cartesia Ink | commercial | ❌ measured: `400 invalid language: tw` |
| OpenAI Whisper | commercial | ❌ |
| faster-whisper | open weights, **offline** | ❌ |

Only the African-built model can be told what language the patient is speaking.
The other three run in English mode on Twi and Pidgin audio by necessity, not by
choice. That's the finding.

The benchmark **imports the app's own speech code** rather than reimplementing
it, so the models measured are literally the models serving patients.

See [`benchmark/README.md`](benchmark/README.md) to reproduce.

## Design commitments

- **No LLM clinical decisions.** Language models structure, classify and
  summarise. Every red-flag threshold is deterministic and rule-based. Licensed
  professionals stay in the loop.
- **Graceful degradation.** Missing key, dead network, no models installed — the
  system degrades to something useful and never hard-fails.
- **Offline-capable.** Local speech recognition needs no key and no internet, for
  clinics with unreliable connectivity.
- **Consent by construction.** Recordings are de-identified by speaker ID, never
  committed to git, and shared only with written consent.

## Status

Built for the [MLC (Africa) × Intron Agentic Voice AI Challenge](https://ml-collective-africa.github.io/dl-indaba-2026/workshop-challenge)
at Deep Learning Indaba 2026 — see [docs/CHALLENGE.md](docs/CHALLENGE.md).

This repo is one slice of a larger product: an AI-native healthcare operating
system for African clinics. That vision is in
[docs/business/](docs/business/EXECUTE-AFRICA-VELOXACARE-AI-NATIVE-HEALTH-OS.md);
this codebase deliberately implements only patient access and care coordination.

---

Veloxa Technology Limited · Ghana
