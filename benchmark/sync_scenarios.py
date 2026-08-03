"""
Regenerate recording/scenarios.csv from recording/scenarios.md.

scenarios.md is what humans edit and what speakers read; scenarios.csv is what
run_benchmark.py scores against. If the two drift, every WER number in the report
is measured against text nobody actually said. Generating one from the other
removes that failure mode entirely.

Usage:
    python sync_scenarios.py            # write the CSV
    python sync_scenarios.py --check    # exit 1 if the CSV is stale (no write)
"""

import argparse
import csv
import re
import sys
from pathlib import Path

RECORDING = Path(__file__).parent / "recording"
SCENARIOS_MD = RECORDING / "scenarios.md"
SCENARIOS_CSV = RECORDING / "scenarios.csv"

# "## Set T — Twi–English code-switched" -> language_pair for every row beneath it
SET_LANGUAGE = {"E": "en", "T": "tw-en", "P": "pcm-en", "S": "tw-en"}

FIELDS = ["scenario_id", "language_pair", "intent_ref", "bp_ref", "script"]

# | T06 | bp_report (116/78) | "Me BP yɛ one-sixteen over seventy-eight." |
ROW_RE = re.compile(r"^\|\s*([ETPS]\d{2})\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*$")
# "bp_report (116/78)" -> intent "bp_report", bp "116/78"
INTENT_RE = re.compile(r"^(\w+)\s*(?:\((\d{2,3}/\d{2,3})\))?$")


def parse(md_text: str) -> list[dict]:
    rows, seen = [], set()

    for line in md_text.splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        scenario_id, intent_cell, script_cell = m.groups()

        # Skip the review-notes table at the bottom, which reuses the IDs in a
        # different column layout. Only the first occurrence of an ID is the script.
        if scenario_id in seen:
            continue

        im = INTENT_RE.match(intent_cell)
        if not im:
            # Set S rows carry a prose prompt rather than an intent — the CSV keeps
            # them with an empty script, and transcripts come from the manifest.
            continue
        intent, bp = im.group(1), im.group(2) or ""

        script = script_cell.strip().strip('"')
        seen.add(scenario_id)
        rows.append({
            "scenario_id": scenario_id,
            "language_pair": SET_LANGUAGE[scenario_id[0]],
            "intent_ref": intent,
            "bp_ref": bp,
            "script": script,
        })

    return rows


def existing_rows() -> list[dict]:
    if not SCENARIOS_CSV.is_file():
        return []
    with open(SCENARIOS_CSV, newline="", encoding="utf-8") as f:
        return [{k: (r.get(k) or "") for k in FIELDS} for r in csv.DictReader(f)]


def write(rows: list[dict]) -> None:
    with open(SCENARIOS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="Exit 1 if the CSV is out of date; don't write.")
    args = ap.parse_args()

    if not SCENARIOS_MD.is_file():
        sys.exit(f"Missing {SCENARIOS_MD}")

    rows = parse(SCENARIOS_MD.read_text(encoding="utf-8"))
    if not rows:
        sys.exit("Parsed no scenarios — has the table format in scenarios.md changed?")

    # The spontaneous set has prompts, not scripts; make sure they still get a row
    # so the manifest can reference S01/S02 with a transcript_override.
    for sid in ("S01", "S02"):
        if not any(r["scenario_id"] == sid for r in rows):
            rows.append({
                "scenario_id": sid,
                "language_pair": SET_LANGUAGE["S"],
                "intent_ref": "cost" if sid == "S01" else "reschedule",
                "bp_ref": "",
                "script": "",
            })

    if args.check:
        if rows != existing_rows():
            sys.exit("scenarios.csv is out of date — run: python sync_scenarios.py")
        print("scenarios.csv is up to date.")
        return

    write(rows)
    by_set = {}
    for r in rows:
        by_set[r["language_pair"]] = by_set.get(r["language_pair"], 0) + 1
    print(f"Wrote {SCENARIOS_CSV} — {len(rows)} scenarios "
          + ", ".join(f"{k}:{v}" for k, v in sorted(by_set.items())))


if __name__ == "__main__":
    main()
