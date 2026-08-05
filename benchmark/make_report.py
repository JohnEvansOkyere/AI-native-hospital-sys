"""
Turn results/ into a submission-ready benchmark report.

Deliverable #4 of the challenge is a "Benchmark Report: performance comparison
across three+ models with analysis". This assembles it from the CSVs so the
numbers in the report can never drift from the numbers in the run.

It writes results/REPORT.md containing the comparison tables, the code-switch
penalty, the escalation flips (the safety-relevant metric), quotable failure
cases, and the caveats that keep the claims honest.

Usage:
    python make_report.py                    # -> results/REPORT.md
    python make_report.py --out somewhere.md
"""

import argparse
import csv
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import median

BENCH = Path(__file__).parent
RESULTS = BENCH / "results"

PROVIDER_LABEL = {
    "sahara": "Intron Sahara",
    "cartesia": "Cartesia Ink",
    "openai_whisper": "OpenAI Whisper API",
}
LANG_LABEL = {
    "en": "English (control)",
    "tw-en": "Twi–English",
    "pcm-en": "Pidgin–English",
    "gaa-en": "Ga–English",
    "ALL": "All sets",
}

# Sahara's client sleeps 2.1s between calls to respect 30 req/min. That sleep is
# ours, not the model's, so subtract it before reporting latency.
SELF_THROTTLE_MS = {"sahara": 2100}


def label(p: str) -> str:
    if p.startswith("local_whisper"):
        return f"Local faster-whisper (`{p.replace('local_whisper_', '')}`)"
    return PROVIDER_LABEL.get(p, p)


def pct(x) -> str:
    return "—" if x in ("", None) else f"{float(x) * 100:.0f}%"


def num(x, places=3) -> str:
    return "—" if x in ("", None) else f"{float(x):.{places}f}"


def load(name: str) -> list[dict]:
    path = RESULTS / name
    if not path.is_file():
        raise SystemExit(f"Missing {path} — run run_benchmark.py first.")
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def adjusted_latency(provider: str, values: list[int]) -> int:
    off = SELF_THROTTLE_MS.get(provider, 0)
    return max(0, int(median(values)) - off)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(RESULTS / "REPORT.md"))
    args = ap.parse_args()

    rows = load("transcripts.csv")
    summary = load("summary.csv")

    providers = sorted({r["provider"] for r in rows})
    langs = [l for l in ("en", "tw-en", "pcm-en", "gaa-en")
             if any(r["language_pair"] == l for r in rows)]
    speakers = sorted({r["speaker_id"] for r in rows})
    files = sorted({r["audio_file"] for r in rows})
    noises = sorted({r["noise_condition"] for r in rows if r["noise_condition"]})

    by = {(s["provider"], s["language_pair"]): s for s in summary}
    lat = defaultdict(list)
    for r in rows:
        if r.get("latency_ms"):
            lat[r["provider"]].append(int(r["latency_ms"]))

    out = []
    A = out.append

    A("# Code-Switch Speech Benchmark — VeloxaCare\n")
    A("**MLC (Africa) × Intron Agentic Voice AI Challenge**  ")
    A(f"Generated {date.today().isoformat()} from `results/transcripts.csv`\n")

    # ── Scope, stated before any numbers ──
    A("## What was measured\n")
    A(f"- **{len(files)} recordings** from **{len(speakers)} speaker(s)**, "
      f"{len(rows)} transcriptions across {len(providers)} models")
    A(f"- Language sets: {', '.join(LANG_LABEL.get(l, l) for l in langs)}")
    if noises:
        A(f"- Noise conditions: {', '.join(noises)}")
    A("- Scripted utterances from a Ghanaian hypertension-care conversation; no real "
      "patient data. Written consent per speaker, de-identified by speaker ID.\n")

    if len(speakers) < 3 or len(files) < 15:
        A("> **Sample-size caveat.** This is a small corpus. Treat every number "
          "below as indicative, not as a general claim about these models. The "
          "comparison between models is fair — identical audio, identical "
          "scoring — but the absolute values would move with more speakers.\n")

    # ── Headline ──
    A("## Why not just word error rate\n")
    A("A misheard digit in this product is not a string-distance statistic, it is a "
      "clinical decision:\n")
    A("> *\"Me BP yɛ **one-sixteen** over seventy-eight\"* → 116/78 → **green**  ")
    A("> *\"Me BP yɛ **one-sixty** over seventy-eight\"* → 160/78 → **red**\n")
    A("So every model is scored on what the agent *does* with the transcript: "
      "whether the blood pressure survives, whether the escalation decision matches, "
      "and whether the right intent is detected. The intent and escalation logic is "
      "rule-based and identical for every model, so the comparison stays fair even "
      "where those rules are imperfect.\n")

    # ── Overall table ──
    A("## Overall\n")
    A("| Model | n | WER | BP extraction | Escalation correct | Intent | Median latency |")
    A("|---|---:|---:|---:|---:|---:|---:|")
    for p in providers:
        s = by.get((p, "ALL"))
        if not s:
            continue
        ms = adjusted_latency(p, lat[p]) if lat[p] else None
        note = "*" if p in SELF_THROTTLE_MS else ""
        A(f"| {label(p)} | {s['n']} | {num(s['mean_wer'])} | {pct(s['bp_accuracy'])} "
          f"| {pct(s['escalation_accuracy'])} | {pct(s['intent_accuracy'])} "
          f"| {ms/1000:.1f}s{note} |" if ms is not None else
          f"| {label(p)} | {s['n']} | {num(s['mean_wer'])} | {pct(s['bp_accuracy'])} "
          f"| {pct(s['escalation_accuracy'])} | {pct(s['intent_accuracy'])} | — |")
    if any(p in SELF_THROTTLE_MS for p in providers):
        A("\n\\* Latency excludes our client's self-imposed rate-limit sleep "
          "(2.1s/call for Sahara's 30 req/min cap), which is our throttle, not the "
          "model's response time. Latency was measured over a consumer connection "
          "in Ghana and is network-dominated — treat it as observational.\n")

    # ── Per language set ──
    if len(langs) > 1:
        A("## By language set\n")
        for lang in langs:
            A(f"### {LANG_LABEL.get(lang, lang)}\n")
            A("| Model | n | WER | BP | Escalation | Intent |")
            A("|---|---:|---:|---:|---:|---:|")
            for p in providers:
                s = by.get((p, lang))
                if not s:
                    continue
                A(f"| {label(p)} | {s['n']} | {num(s['mean_wer'])} | {pct(s['bp_accuracy'])} "
                  f"| {pct(s['escalation_accuracy'])} | {pct(s['intent_accuracy'])} |")
            A("")

        # ── Code-switch penalty — the variable the challenge is about ──
        A("## Code-switch penalty\n")
        A("Degradation from the English control to code-switched speech. This "
          "isolates the variable the challenge exists to measure — the English set "
          "is what makes it attributable to code-switching rather than to accent or "
          "recording conditions.\n")
        A("| Model | English WER | Code-switched WER | Penalty |")
        A("|---|---:|---:|---:|")
        for p in providers:
            en = by.get((p, "en"))
            cs = [float(by[(p, l)]["mean_wer"]) for l in langs
                  if l != "en" and (p, l) in by]
            if not en or not cs:
                continue
            e, c = float(en["mean_wer"]), sum(cs) / len(cs)
            A(f"| {label(p)} | {e:.3f} | {c:.3f} | **{c - e:+.3f}** |")
        A("")

    # ── The safety metric ──
    flips = [r for r in rows
             if r["escalation_ref"] and r["escalation_correct"] == "0"]
    A("## Escalation flips (safety-relevant)\n")
    if not flips:
        A("No escalation flips: every model's transcript produced the same "
          "red/amber/green decision as the true reading, on every recording where "
          "a blood pressure was spoken.\n")
    else:
        A(f"**{len(flips)} case(s)** where a transcription error changed the clinical "
          "decision. These are the failures that matter most.\n")
        A("| File | Model | True BP | Heard | True risk | Decided |")
        A("|---|---|---|---|---|---|")
        for r in flips:
            A(f"| `{r['audio_file']}` | {label(r['provider'])} | {r['bp_ref']} "
              f"| {r['bp_extracted'] or '—'} | **{r['escalation_ref']}** "
              f"| **{r['escalation_pred'] or 'none'}** |")
        A("")

    # ── Quotable failures ──
    worst = sorted((r for r in rows if r["transcript"]),
                   key=lambda r: -float(r["wer"]))[:6]
    if worst:
        A("## Notable transcription errors\n")
        for r in worst:
            if float(r["wer"]) == 0:
                continue
            A(f"**`{r['scenario_id']}` · {label(r['provider'])}** (WER {r['wer']})  ")
            A(f"> {r['transcript']}\n")

    errs = [r for r in rows if r["error"]]
    if errs:
        A("## Failed requests\n")
        for r in errs[:10]:
            A(f"- `{r['audio_file']}` · {label(r['provider'])}: {r['error'][:160]}")
        A("")

    # ── Method + honesty ──
    A("## Method\n")
    A("- Scripts in `recording/scenarios.md`; `scenarios.csv` is generated from it, "
      "so the scoring reference always matches what speakers actually read.")
    A("- Recorded on ordinary phones. `make_manifest.py` flags clips too short for "
      "their script — clipped audio looks exactly like a model failure and produced "
      "one false result during development before the check existed.")
    A("- Spoken numbers are normalised to digits, and blood-pressure notation is "
      "canonicalised (`142/95` ≡ `142 over 95`) before WER. Without that, a model "
      "that recognises a reading *as* a blood pressure is penalised for writing it "
      "correctly — we hit exactly this and it inverted the ranking.")
    A("- Language hints: Sahara receives the per-set code (`en`/`tw`/`pcm`/`gaa`). "
      "Whisper variants and Cartesia have no Ghanaian codes to receive — Cartesia "
      "returns `HTTP 400: invalid language: tw` — so they run in English mode on "
      "code-switched audio by necessity, not by our choice. **That asymmetry is a "
      "finding, not a methodology flaw**, and it is the point of the exercise.")
    A("- The benchmark imports the live application's speech code "
      "(`backend/services/stt.py`) rather than reimplementing it, so the models "
      "measured are the models serving patients.\n")

    A("## Limitations\n")
    A(f"- {len(speakers)} speaker(s) — accent and gender coverage is thin.")
    A("- Scripted speech under-represents real disfluency; the spontaneous set is "
      "the partial mitigation.")
    A("- The rule-based intent detector is tuned to keywords present in these "
      "scenarios, so it flatters all models equally. It is a fair *comparison*, not "
      "an absolute measure of agent quality.")
    A("- Latency was measured from Ghana on a consumer connection and is dominated "
      "by network conditions rather than model speed.\n")

    Path(args.out).write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {args.out}")
    print(f"  {len(files)} recordings · {len(speakers)} speaker(s) · "
          f"{len(providers)} models · {len(langs)} language set(s)")
    if len(langs) == 1:
        print("  NOTE: only the English control is present — record the Twi and "
              "Pidgin sets before submitting.")


if __name__ == "__main__":
    main()
