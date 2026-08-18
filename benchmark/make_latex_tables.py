#!/usr/bin/env python3
"""Emit LaTeX table bodies and headline figures for the benchmark report.

Reads results/summary.csv and results/transcripts.csv and prints everything the
report needs, so the paper's numbers are copied from the scorer rather than
retyped by hand.
"""
import csv
import sys
from collections import Counter, defaultdict

RESULTS = sys.argv[1] if len(sys.argv) > 1 else "results"

LABEL = {
    "sahara": r"Sahara \texttt{(tw/pcm)}",
    "sahara_en": r"Sahara \texttt{(en)}",
    "cartesia": "Cartesia Ink",
    "local_whisper_base": "faster-whisper",
}
ORDER = ["sahara", "sahara_en", "cartesia", "local_whisper_base"]


def pct(x):
    return f"{100 * float(x):.0f}\\%"


def main():
    summ = list(csv.DictReader(open(f"{RESULTS}/summary.csv")))
    rows = list(csv.DictReader(open(f"{RESULTS}/transcripts.csv")))

    # Older summary.csv had no `slice`/`noise_condition` columns; treat every
    # row as a language slice in that case so both schemas render.
    has_slice = "slice" in (summ[0].keys() if summ else {})
    by = {(r["provider"], r["language_pair"]): r
          for r in summ if not has_slice or r["slice"] == "lang"}
    noise = {(r["provider"], r["noise_condition"]): r
             for r in summ if has_slice and r["slice"] == "noise"}

    # ---- error audit: never report a failed call as model performance -------
    errs = Counter(r["provider"] for r in rows if (r.get("error") or "").strip())
    print("%% ERROR AUDIT (must be zero, or stated in the paper)")
    for p in ORDER:
        print(f"%%   {p}: {errs.get(p, 0)} failed calls")
    print()

    # ---- Table 1: overall ---------------------------------------------------
    print("%% ---- TABLE: overall ----")
    for p in ORDER:
        r = by.get((p, "ALL"))
        if not r:
            continue
        print(f"{LABEL[p]} & {r['n']} & {float(r['mean_wer']):.3f} & "
              f"{pct(r['bp_accuracy'])} & {pct(r['escalation_accuracy'])} & "
              f"{pct(r['intent_accuracy'])} & "
              f"{int(r['median_latency_ms'])/1000:.1f}s \\\\")
    print()

    # ---- Table 2: by language set ------------------------------------------
    print("%% ---- TABLE: by language set (en / tw-en / pcm-en) ----")
    for p in ORDER:
        cells = [LABEL[p]]
        for lang in ("en", "tw-en", "pcm-en"):
            r = by.get((p, lang))
            cells.append(f"{float(r['mean_wer']):.3f}" if r else "--")
            cells.append(pct(r["escalation_accuracy"]) if r else "--")
        print(" & ".join(cells) + r" \\")
    print()

    # ---- Code-switch penalty ------------------------------------------------
    print("%% ---- code-switch penalty (WER on code-switched minus WER on en) ----")
    for p in ORDER:
        en = by.get((p, "en"))
        tw = by.get((p, "tw-en"))
        pc = by.get((p, "pcm-en"))
        if not (en and tw and pc):
            continue
        cs = (float(tw["mean_wer"]) * int(tw["n"]) +
              float(pc["mean_wer"]) * int(pc["n"])) / (int(tw["n"]) + int(pc["n"]))
        print(f"%%   {p}: {cs - float(en['mean_wer']):+.3f}")
    print()

    # ---- Noise --------------------------------------------------------------
    print("%% ---- quiet vs noisy (WER) ----")
    for p in ORDER:
        q, n = noise.get((p, "quiet")), noise.get((p, "noisy"))
        if q and n:
            print(f"%%   {p}: quiet {float(q['mean_wer']):.3f} (n={q['n']}) "
                  f"-> noisy {float(n['mean_wer']):.3f} (n={n['n']})")
    print()

    # ---- Escalation flips: the clinically material failures ------------------
    print("%% ---- escalation flips (transcript changed the clinical decision) ----")
    flips = defaultdict(list)
    for r in rows:
        if (r.get("error") or "").strip():
            continue
        if r.get("escalation_correct") in ("0", "False", "false"):
            if r.get("escalation_ref") or r.get("escalation_pred"):
                flips[r["provider"]].append(
                    (r["audio_file"], r.get("escalation_ref"),
                     r.get("escalation_pred")))
    for p in ORDER:
        f = flips.get(p, [])
        print(f"%%   {p}: {len(f)} flips")
        for a, ref, pred in f[:6]:
            print(f"%%       {a}: {ref} -> {pred}")
    print()

    # ---- Dangerous direction: red downgraded to green/amber -----------------
    print("%% ---- MISSED escalations (ref red, predicted not red) ----")
    for p in ORDER:
        missed = [x for x in flips.get(p, []) if x[1] == "red" and x[2] != "red"]
        overs = [x for x in flips.get(p, []) if x[1] != "red" and x[2] == "red"]
        print(f"%%   {p}: missed={len(missed)} false_alarm={len(overs)}")
    print()

    # ---- Speaker coverage ---------------------------------------------------
    spk = Counter(r["speaker_id"] for r in rows if r["provider"] == "cartesia")
    print(f"%% speakers: {dict(spk)}  total recordings={sum(spk.values())}")


if __name__ == "__main__":
    main()
