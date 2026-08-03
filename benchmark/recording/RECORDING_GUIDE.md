# Recording Guide

Goal: ~20 scripted utterances × 4–6 speakers × 2 noise conditions, on ordinary
phones. One session is ~15 minutes per speaker.

## Before any recording

1. **Naturalize the Twi scripts** in `scenarios.md` with a fluent speaker — see
   the *Review notes* at the bottom of that file for the specific decisions to
   confirm. Then regenerate the scoring reference:

   ```bash
   cd .. && python sync_scenarios.py
   ```

   Never hand-edit `scenarios.csv`; it's generated. `python sync_scenarios.py
   --check` tells you if it's stale.
2. Print `consent_form.md` — **one signed copy per speaker, before recording**.
3. Fill one row per speaker in `metadata_sheet.csv` (speaker ID `S01`, `S02`, …
   — never names).

## Who to recruit

4–6 speakers, aiming for spread: mixed gender, age bands (18–30 / 31–50 / 50+),
and at least two accent regions (e.g. Accra vs Kumasi/Ashanti). One or two
speakers who are strongest in Pidgin should take Set P.

## Recording session (per speaker)

1. Phone voice-recorder app. If the app offers a format choice, prefer WAV or
   M4A. Hold the phone like a normal call or ~20 cm from the mouth.
2. **One file per scenario line** — not one long recording.
3. Speaker reads the line at natural conversational pace — the way they'd
   actually say it to a clinic nurse on the phone. Not news-anchor diction.
4. If the speaker stumbles, just re-record that file.
5. **Start recording before they speak, stop ~1 second after the last word.**
   Clipping the tail is the single most common way to ruin a take, and it's
   invisible until you listen back — the model transcribes what it heard, which
   looks like a model failure rather than a recording failure. `make_manifest.py`
   flags suspiciously short files, so run it before the speaker leaves.
5. If the speaker naturally says it slightly differently and it sounds better,
   keep it — but **write the exact wording** in the manifest's
   `transcript_override` column.

### Noise conditions

- **quiet**: indoor room, everyone records the full set.
- **noisy**: real ambient noise — compound/street/market/taxi with windows down.
  A subset is enough: each speaker re-records ~5 lines (include at least two
  BP lines, e.g. T06, T07) in the noisy condition.

## File naming — strict

```
{speaker}_{scenario}_{noise}.{ext}
S01_T06_quiet.m4a
S03_P02_noisy.wav
```

Drop all files into `benchmark/audio/`.

## After recording

1. Copy `manifest.example.csv` → `manifest.csv`; add one row per file.
2. For Set S (spontaneous) recordings, hand-transcribe exactly what was said
   (including the code-switching, in normal orthography) into
   `transcript_override`.
3. Spot-check: play 2–3 random files — audible, not clipped, right names.
