# VeloxaCare STT Benchmark — MLC (Africa) × Intron Agentic Voice AI Challenge

Benchmarks 4 speech models on code-switched Ghanaian audio (Twi–English, Pidgin–English,
plus an English-only control set), scored on **downstream task success**, not just WER:

| Metric | What it measures | Why it matters |
|---|---|---|
| WER | Transcription accuracy | Standard baseline, comparable to other work |
| BP extraction accuracy | Did the digits survive? (`142/95` vs `one forty-two over ninety-five`) | Misheard digits are the classic ASR failure |
| **Escalation correctness** | Does the extracted BP produce the same red/amber/green decision as the true BP? | A `116` heard as `160` flips a clinical escalation — this is the safety-relevant headline metric |
| Intent accuracy | Does the same rule-based intent detector reach the right intent from each model's transcript? | Ties ASR quality to whether the *agent does the right thing* |
| Code-switch penalty | Metric degradation on code-switched sets vs the English control | Isolates the variable this challenge is about |

## Providers compared

The challenge requires ≥3 models including one Intron Sahara API. We run four:

| Provider | Kind | Endpoint / model |
|---|---|---|
| **Intron Sahara** | African-built, code-switch aware | `POST https://infer.voice.intron.io/file/v1/upload/sync` |
| **OpenAI Whisper API** | frontier commercial default | `whisper-1` |
| **Cartesia Ink** | commercial, latency-optimised | `POST https://api.cartesia.ai/stt`, `ink-whisper` |
| **Local faster-whisper** | open weights, offline, no API | `WHISPER_LOCAL_MODEL` |

One African-built, two commercial, one open-weights/offline. The offline entry
also covers the challenge's low-bandwidth bonus criterion.

**State plainly in the report:** Cartesia's `ink-whisper` is Whisper-derived, so
it is not architecturally independent of the two Whisper rows. It earns a column
as a distinct commercial product with its own tuning, serving and latency
profile — but it is not a fourth independent architecture, and claiming so would
be dishonest.

The provider clients live in [`backend/services/stt.py`](../backend/services/stt.py) and are
re-exported by `stt_providers.py` here. That's deliberate: the live agent transcribes
patient voice notes with the same classes, same language mapping, same request
parameters. The models benchmarked *are* the models serving patients — worth stating
in the report, since it's what separates this from a detached test harness.

## Directory layout

```
benchmark/
  recording/            Everything needed to collect audio from speakers
    RECORDING_GUIDE.md    Step-by-step for the recording sessions
    scenarios.md          Scripts speakers read — THE source of truth, edit here
    scenarios.csv         Generated from scenarios.md by sync_scenarios.py; don't hand-edit
    consent_form.md       Print/sign one per speaker
    metadata_sheet.csv    One row per speaker
  audio/                ← PUT RECORDINGS HERE, named {speaker}_{scenario}_{noise}.{ext}
  sync_scenarios.py     Regenerates scenarios.csv from scenarios.md (--check to verify)
  make_manifest.py      Builds manifest.csv by scanning audio/ filenames
  probe_languages.py    Which language codes each API actually accepts
  stt_providers.py      Re-exports the four provider clients from backend/services/stt.py
  run_benchmark.py      Transcribe everything + score + write results
  manifest.example.csv  Template — copy to manifest.csv and fill per recording
  results/              Output: transcripts.csv + summary.csv
```

## Quickstart

```bash
cd benchmark
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export INTRON_API_KEY=...        # from https://voice.intron.io/v2/developers
export CARTESIA_API_KEY=...      # from https://play.cartesia.ai/keys
export OPENAI_API_KEY=...
export WHISPER_LOCAL_MODEL=medium   # use large-v3 for final runs (slower on CPU)

# 0. Confirm your keys actually accept the Ghanaian language codes BEFORE
#    spending a day recording. Any short clip works.
python probe_languages.py --audio some_clip.m4a

# 1. Record per recording/RECORDING_GUIDE.md, drop the files in benchmark/audio/
#    named {speaker}_{scenario}_{noise}.{ext}, e.g. S01_T06_quiet.m4a
# 2. Build the manifest from those filenames (no hand-typing):
python make_manifest.py --dry-run    # validate names + see coverage
python make_manifest.py              # write manifest.csv

# 3. Run:
python run_benchmark.py --manifest manifest.csv --audio-dir audio --out results \
    --providers sahara,cartesia,openai,local
```

`transcript_override` in the manifest is only needed when a speaker deviated from the
script — otherwise the reference transcript comes from `scenarios.csv` automatically.

Sanity-check the scoring reference any time you edit the scripts:

```bash
python sync_scenarios.py --check    # is scenarios.csv current?
```

All 19 scripted scenarios are verified self-consistent: the scorer recovers the
expected BP and intent from each reference script, with T06 → green and T07 → red.
Re-verify after editing the Twi, since a reworded line can change what the
rule-based intent detector matches.

## Method notes (for the benchmark report)

- **English control set**: E-scenarios isolate the code-switch penalty — report
  each model's degradation from EN → TW-EN / PCM-EN, not just absolute scores.
- **The 116/160 minimal pair is deliberate** (scenarios T06 vs T07): "one-sixteen"
  vs "one-sixty" is the canonical digit confusion, and here it decides whether a
  hypertensive patient gets escalated.
- **The intent scorer is rule-based and identical across providers**, so even
  where it is imperfect, the comparison between models is fair.
- **Language codes — the headline result.** Intron's docs table lists `ak` (Akan),
  `tw` (Twi), `pcm` (Pidgin) and `gaa` (Ga) among supported inputs. Whisper's ~99
  languages contain none of them, and `ink-whisper` inherits that gap. So **Sahara
  is the only one of the four that can be told what language the patient is
  speaking**; the other three run in English mode on Twi and Pidgin audio by
  necessity, not by our choice.
  **Caveat that must survive into the report:** documented ≠ shipped. Intron
  confirmed the **Akan–English code-switch pair** had not shipped at time of
  testing (rolling out the week of 10 Aug 2026), and the monolingual `tw` model
  returns an empty transcript on Twi–English speech while the `en` hint yields
  usable text. Hence two Sahara rows (`sahara`, `sahara_en`) — the language hint
  moves the result more than the model choice does.
  *Measured 3 Aug 2026 via `probe_languages.py`:* Cartesia returns explicit
  `HTTP 400: invalid language: tw` (likewise `ak`, `pcm`, `gaa`) while accepting
  `en` and `sw` — the only African language it takes is Swahili. Cite the
  measurement, not the assumption. Intron's table has no explicit `xx-en` pair
  codes, so a code-switched utterance goes under its non-English code and Sahara's
  code-switching handling does the rest. If `gaa` works on your key, a Ga set is
  worth adding: low-resource coverage is a stated bonus criterion.
- **Latency is a second axis.** Cartesia sells speed, Sahara sells African language
  coverage. `run_benchmark.py` records per-call latency, so report accuracy *and*
  latency rather than a single ranking — a clinic on a rural connection cares about
  both.
- **Language hints**: Sahara gets the per-set language code (`en` / `tw` / `pcm`);
  Whisper variants run in auto-detect (passing `language=en` on code-switched audio
  biases them; auto-detect is their realistic deployment mode). Documented tradeoff.
- **Sahara constraints**: max 120s per file (our utterances are <30s), 30 req/min
  (the runner spaces Sahara calls automatically).

## Ethics

Audio is scripted (no real medical information), collected with written consent
(see `recording/consent_form.md`), stored de-identified (speaker IDs, no names in
filenames or metadata), and only submitted to the challenge if the speaker consented
to that use.
