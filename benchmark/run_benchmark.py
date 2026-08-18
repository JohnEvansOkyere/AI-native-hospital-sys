"""
Run the code-switch STT benchmark: transcribe every manifest row with every
provider, then score on transcription (WER) AND downstream task success
(BP digit extraction, escalation correctness, intent detection).

Usage:
    python run_benchmark.py --manifest manifest.csv --audio-dir audio --out results \
        --providers sahara,openai,local
"""

import argparse
import csv
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from jiwer import wer as jiwer_wer

# Read keys from the repo-root .env, same file the app uses — no exports needed.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from stt_providers import LanguageNotSupported, build_providers  # noqa: E402

BENCH_DIR = Path(__file__).parent
SCENARIOS_CSV = BENCH_DIR / "recording" / "scenarios.csv"


# ---------------------------------------------------------------- normalization

_NUM_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}


def _words_to_digits(text: str) -> str:
    """Collapse spoken numbers to digits: 'one forty-two' -> '142',
    'one hundred and forty two' -> '142', 'ninety five' -> '95',
    'one-sixteen' -> '116'."""
    tokens = text.replace("-", " ").split()
    out, cur = [], None

    def flush():
        nonlocal cur
        if cur is not None:
            out.append(str(cur))
            cur = None

    for tok in tokens:
        if tok == "hundred":
            cur = (cur or 1) * 100
        elif tok == "and" and cur is not None:
            continue
        elif tok in _NUM_WORDS:
            v = _NUM_WORDS[tok]
            if cur is None:
                cur = v
            elif cur < 10 and 10 <= v <= 99:
                cur = cur * 100 + v          # "one forty" -> 140, "one sixteen" -> 116
            elif cur % 100 == 0 and v < 100:
                cur += v                     # "one hundred forty" -> 140
            elif cur >= 20 and cur % 10 == 0 and v < 10:
                cur += v                     # "forty two" -> 42
            else:
                flush()
                cur = v
        elif tok.isdigit():
            flush()
            out.append(tok)
        else:
            flush()
            out.append(tok)
    flush()
    return " ".join(out)


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s/ɛɔ]", " ", text)   # keep '/', Twi vowels
    text = _words_to_digits(text)
    # Canonicalise blood-pressure notation before scoring. A model that hears
    # "one forty-two over ninety-five" and writes "142/95" has understood it as
    # a BP — arguably better than a literal transcript — and must not be charged
    # a WER penalty for the notation. Both forms collapse to "142 over 95".
    text = re.sub(r"\b(\d{2,3})\s*/\s*(\d{2,3})\b", r"\1 over \2", text)
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------- task scoring

BP_RE = re.compile(r"(\d{2,3})\s*(?:/|over)\s*(\d{2,3})")


def extract_bp(norm_text: str) -> str | None:
    m = BP_RE.search(norm_text)
    return f"{m.group(1)}/{m.group(2)}" if m else None


def escalation_level(bp: str | None) -> str | None:
    """Mirror backend/services/ai.py:assess_bp_risk thresholds."""
    if not bp:
        return None
    sys_, dia = (int(x) for x in bp.split("/"))
    if sys_ >= 160 or dia >= 100:
        return "red"
    if sys_ >= 140 or dia >= 90:
        return "amber"
    return "green"


# Ordered rules — first match wins. Rule-based and identical for every provider,
# so the model comparison stays fair even where the rules are imperfect.
INTENT_RULES = [
    ("side_effect", ["headache", "dizzy", "ti pae", "side effect"]),
    ("forgot", ["forgot", "forget", "werɛ afi", "were afi"]),
    ("reschedule", ["reschedule", "move my appointment", "change my appointment"]),
    ("book_appointment", ["book", "appointment"]),
    ("refill_request", ["refill", "almost finished", "need more"]),
    ("ran_out", ["ran out", "run out", "don finish", "finished", "asa"]),
    ("cost", ["afford", "expensive", "cost too much", "no fit buy", "sika", "money"]),
    ("adherence_yes", ["took my medicine", "take my medicine", "anom aduro", "aane"]),
]


def detect_intent(norm_text: str) -> str:
    for intent, keywords in INTENT_RULES:
        if any(k in norm_text for k in keywords):
            return intent
    if extract_bp(norm_text):
        return "bp_report"
    return "unknown"


# ---------------------------------------------------------------- runner

def load_scenarios() -> dict:
    with open(SCENARIOS_CSV, newline="", encoding="utf-8") as f:
        return {row["scenario_id"]: row for row in csv.DictReader(f)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--audio-dir", default="audio")
    ap.add_argument("--out", default="results")
    ap.add_argument("--providers", default="sahara,openai,local")
    args = ap.parse_args()

    scenarios = load_scenarios()
    providers = build_providers(args.providers.split(","))
    out_dir = Path(args.out)
    out_dir.mkdir(exist_ok=True)

    with open(args.manifest, newline="", encoding="utf-8") as f:
        manifest = list(csv.DictReader(f))

    rows = []
    for i, item in enumerate(manifest, 1):
        scen = scenarios.get(item["scenario_id"])
        if scen is None:
            print(f"SKIP {item['audio_file']}: unknown scenario {item['scenario_id']}")
            continue
        ref_text = item.get("transcript_override", "").strip() or scen["script"]
        if not ref_text:
            print(f"SKIP {item['audio_file']}: no script and no transcript_override")
            continue
        audio_path = Path(args.audio_dir) / item["audio_file"]
        if not audio_path.exists():
            print(f"SKIP {item['audio_file']}: file not found")
            continue

        ref_norm = normalize(ref_text)
        # The script is what we asked for; the audio is what was said. When a
        # speaker deviates on a number, score against the recording — otherwise
        # every model is penalised for our reference being wrong. Verified
        # deviations go in the manifest's bp_override column.
        bp_ref = (item.get("bp_override", "").strip()
                  or scen["bp_ref"].strip() or None)
        intent_ref = scen["intent_ref"]
        lang = scen["language_pair"]

        for provider in providers:
            print(f"[{i}/{len(manifest)}] {provider.name}: {item['audio_file']}")
            started = time.time()
            try:
                hyp = provider.transcribe(str(audio_path), language=lang)
                error = ""
            except LanguageNotSupported as e:
                # The provider has no model for this pair, so there is nothing to
                # score. Recording it as WER 1.0 would punish a Ghanaian-language
                # specialist for the 30 English and Pidgin clips it never claimed
                # — the difference between "absent from that slice" and "scored
                # zero on it" is the difference between an honest table and a
                # misleading one.
                print(f"  skipped ({e})")
                continue
            except Exception as e:
                hyp, error = "", f"{type(e).__name__}: {e}"
                print(f"  ERROR {error}")
            # Wall-clock per call. Sahara's client self-throttles to 30 req/min,
            # so its figure includes that sleep — compare latency across providers
            # only as an order-of-magnitude signal, and say so in the report.
            latency_ms = int((time.time() - started) * 1000)

            hyp_norm = normalize(hyp)
            bp_hyp = extract_bp(hyp_norm)
            intent_hyp = detect_intent(hyp_norm)
            rows.append({
                "audio_file": item["audio_file"],
                "scenario_id": item["scenario_id"],
                "speaker_id": item["speaker_id"],
                "language_pair": lang,
                "noise_condition": item.get("noise_condition", ""),
                "provider": provider.name,
                "transcript": hyp,
                "latency_ms": latency_ms,
                "wer": round(jiwer_wer(ref_norm, hyp_norm), 3) if hyp_norm else 1.0,
                "bp_ref": bp_ref or "",
                "bp_extracted": bp_hyp or "",
                "bp_correct": "" if not bp_ref else int(bp_hyp == bp_ref),
                "escalation_ref": escalation_level(bp_ref) or "",
                "escalation_pred": escalation_level(bp_hyp) or "",
                "escalation_correct": "" if not bp_ref else int(
                    escalation_level(bp_hyp) == escalation_level(bp_ref)),
                "intent_ref": intent_ref,
                "intent_pred": intent_hyp,
                "intent_correct": int(intent_hyp == intent_ref),
                "error": error,
            })

    if not rows:
        sys.exit("No rows produced — check manifest and audio dir.")

    with open(out_dir / "transcripts.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    # ---- summary, sliced two ways.
    #
    # Language and noise are separate questions: "which model copes with
    # code-switching" and "which model survives a roadside". Crossing them would
    # split an already small set into cells of two or three recordings, so each
    # dimension is aggregated over the other and marked ALL on the axis it
    # ignores. The `slice` column says which question a row answers.
    groups = defaultdict(list)
    for r in rows:
        groups[("lang", r["provider"], r["language_pair"])].append(r)
        groups[("lang", r["provider"], "ALL")].append(r)
        if r["noise_condition"]:
            groups[("noise", r["provider"], r["noise_condition"])].append(r)

    def rate(rs, key):
        vals = [r[key] for r in rs if r[key] != ""]
        return round(sum(vals) / len(vals), 3) if vals else ""

    summary = []
    for (slice_, provider, value), rs in sorted(groups.items()):
        summary.append({
            "slice": slice_,
            "provider": provider,
            "language_pair": value if slice_ == "lang" else "ALL",
            "noise_condition": value if slice_ == "noise" else "ALL",
            "n": len(rs),
            "mean_wer": round(sum(r["wer"] for r in rs) / len(rs), 3),
            "bp_accuracy": rate(rs, "bp_correct"),
            "escalation_accuracy": rate(rs, "escalation_correct"),
            "intent_accuracy": rate(rs, "intent_correct"),
            "median_latency_ms": sorted(r["latency_ms"] for r in rs)[len(rs) // 2],
        })

    with open(out_dir / "summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=summary[0].keys())
        writer.writeheader()
        writer.writerows(summary)

    def print_table(title, header, slice_, key):
        rs = [s for s in summary if s["slice"] == slice_]
        if not rs:
            return
        print(f"\n{title}")
        print(f"{'provider':<24}{header:<8}{'n':>4}{'WER':>8}{'BP':>8}"
              f"{'escal':>8}{'intent':>8}{'ms':>9}")
        for s in rs:
            print(f"{s['provider']:<24}{s[key]:<8}{s['n']:>4}"
                  f"{s['mean_wer']:>8}{s['bp_accuracy']:>8}{s['escalation_accuracy']:>8}"
                  f"{s['intent_accuracy']:>8}{s['median_latency_ms']:>9}")

    print_table("By language pair:", "lang", "lang", "language_pair")
    print_table("By noise condition:", "noise", "noise", "noise_condition")

    # Noise robustness: how much each model degrades from a quiet room to real
    # ambient noise. The deployed product only ever sees the second condition,
    # so a model that wins on quiet audio and collapses on noisy audio is the
    # wrong choice however good its headline number looks.
    print("\nNoise penalty (mean WER, noisy minus quiet):")
    for provider in sorted({r["provider"] for r in rows}):
        quiet = [r["wer"] for r in rows
                 if r["provider"] == provider and r["noise_condition"] == "quiet"]
        noisy = [r["wer"] for r in rows
                 if r["provider"] == provider and r["noise_condition"] == "noisy"]
        if quiet and noisy:
            delta = sum(noisy) / len(noisy) - sum(quiet) / len(quiet)
            print(f"  {provider}: {delta:+.3f}   (quiet n={len(quiet)}, noisy n={len(noisy)})")

    # code-switch penalty: WER degradation vs English control
    print("\nCode-switch penalty (mean WER, code-switched minus English control):")
    for provider in sorted({r["provider"] for r in rows}):
        en = [r["wer"] for r in rows if r["provider"] == provider and r["language_pair"] == "en"]
        cs = [r["wer"] for r in rows if r["provider"] == provider and r["language_pair"] != "en"]
        if en and cs:
            print(f"  {provider}: {sum(cs)/len(cs) - sum(en)/len(en):+.3f}")

    print(f"\nWrote {out_dir/'transcripts.csv'} and {out_dir/'summary.csv'}")


if __name__ == "__main__":
    main()
