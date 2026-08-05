"""
Build manifest.csv by scanning audio/ — the filenames already encode everything.

Naming convention (from recording/RECORDING_GUIDE.md):

    {speaker}_{scenario}_{noise}.{ext}      e.g. S01_T06_quiet.m4a

So there's no reason to type the manifest by hand. This scans the audio folder,
validates every filename against scenarios.csv, and writes the manifest.

Existing `transcript_override` values are preserved when you re-run it, so the
hand-transcriptions you did for the spontaneous Set S recordings are never lost.

Common renaming slips are tolerated and reported rather than rejected: a doubled
extension (`x.m4a.m4a`), an unpadded scenario id (`E1`), and a misspelt noise
condition (`quit`). Pass --fix to correct the names on disk.

Usage:
    python make_manifest.py                  # write manifest.csv
    python make_manifest.py --dry-run        # just validate the filenames
    python make_manifest.py --fix            # tidy filenames, then write
"""

import argparse
import csv
import difflib
import sys
from collections import Counter
from pathlib import Path

BENCH = Path(__file__).parent
AUDIO_DIR = BENCH / "audio"
MANIFEST = BENCH / "manifest.csv"
SCENARIOS_CSV = BENCH / "recording" / "scenarios.csv"

AUDIO_EXT = {".m4a", ".wav", ".mp3", ".ogg", ".oga", ".webm", ".flac", ".mp4"}
NOISE = {"quiet", "noisy"}
FIELDS = ["audio_file", "scenario_id", "speaker_id", "noise_condition",
          "transcript_override", "bp_override"]


def canonical_stem(path: Path, scenarios: dict) -> tuple[str | None, list[str]]:
    """Map a possibly-sloppy filename to '{speaker}_{scenario}_{noise}'.

    Fixes the three slips that actually happen when renaming a pile of phone
    recordings by hand: a doubled extension (`x.m4a.m4a`), an unpadded scenario
    id (`E1`), and a misspelt noise condition (`quit`). Everything else is a real
    error and gets reported rather than guessed at.

    Returns (canonical_stem or None, notes).
    """
    notes = []
    stem = path.stem

    # "S01_E01_quiet.m4a" (from S01_E01_quiet.m4a.m4a) -> strip trailing ext
    while True:
        trailing = Path(stem).suffix.lower()
        if trailing in AUDIO_EXT:
            stem = Path(stem).stem
            notes.append("doubled file extension")
        else:
            break

    parts = stem.split("_")
    if len(parts) != 3:
        return None, notes
    speaker, scenario, noise = parts

    # E1 -> E01
    if scenario not in scenarios:
        padded = f"{scenario[0].upper()}{scenario[1:].zfill(2)}"
        if padded in scenarios:
            notes.append(f"scenario {scenario} -> {padded}")
            scenario = padded

    # quit/quite/nosiy -> quiet/noisy
    if noise.lower() not in NOISE:
        close = difflib.get_close_matches(noise.lower(), NOISE, n=1, cutoff=0.6)
        if close:
            notes.append(f"noise '{noise}' -> '{close[0]}'")
            noise = close[0]
    noise = noise.lower()

    return f"{speaker}_{scenario}_{noise}", notes


# Upper bound on plausible speaking rate, used to spot clipped recordings.
#
# Calibrated against real sessions: an English control set read at 1.5-1.9
# words/sec, while the same speaker delivered Twi and Pidgin at 2.5-2.9 w/s —
# people read their own languages faster, and code-switched lines pack more
# syllables into fewer whitespace-delimited "words". A threshold tuned on English
# alone produces false positives on exactly the sets that matter most.
#
# 3.5 w/s is faster than natural conversational delivery, so anything below the
# implied duration is worth a listen. This is ADVISORY, not a verdict: confirm by
# playing the file or checking that a transcript reaches the final word.
MAX_WORDS_PER_SEC = 3.5


def duration_seconds(path: Path) -> float | None:
    """Audio duration via ffprobe, or None if ffprobe isn't available."""
    import subprocess
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=20,
        )
        return float(out.stdout.strip())
    except Exception:
        return None


def load_scenarios() -> dict:
    if not SCENARIOS_CSV.is_file():
        sys.exit(f"Missing {SCENARIOS_CSV} — run: python sync_scenarios.py")
    with open(SCENARIOS_CSV, newline="", encoding="utf-8") as f:
        return {r["scenario_id"]: r for r in csv.DictReader(f)}


def load_existing_overrides() -> dict:
    """Keep hand-corrections across re-runs, keyed by audio filename.

    Both overrides exist for the same reason: the script is what we asked for,
    the audio is what was said. When a speaker deviates — and they do, especially
    on numbers — the recording must be scored against what is actually on it, or
    every model is charged for our transcription error.
    """
    if not MANIFEST.is_file():
        return {}
    out = {}
    with open(MANIFEST, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            kept = {k: (r.get(k) or "").strip()
                    for k in ("transcript_override", "bp_override")
                    if (r.get(k) or "").strip()}
            if kept:
                out[r["audio_file"]] = kept
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Validate only, don't write.")
    ap.add_argument("--fix", action="store_true",
                    help="Rename sloppy filenames to the canonical form on disk.")
    args = ap.parse_args()

    scenarios = load_scenarios()
    overrides = load_existing_overrides()

    if not AUDIO_DIR.is_dir():
        sys.exit(f"No {AUDIO_DIR} — create it and drop the recordings in.")

    files = sorted(p for p in AUDIO_DIR.iterdir()
                   if p.is_file() and p.suffix.lower() in AUDIO_EXT)
    if not files:
        sys.exit(f"No audio files in {AUDIO_DIR}.\n"
                 "Expected names like S01_T06_quiet.m4a "
                 "({speaker}_{scenario}_{noise}.{ext}).")

    rows, problems, renames, clipped = [], [], [], []
    for p in files:
        stem, notes = canonical_stem(p, scenarios)
        if stem is None:
            problems.append(f"{p.name}: expected 3 parts "
                            "({speaker}_{scenario}_{noise})")
            continue
        speaker, scenario, noise = stem.split("_")

        if scenario not in scenarios:
            problems.append(f"{p.name}: unknown scenario '{scenario}' "
                            f"(known: {', '.join(sorted(scenarios))})")
            continue
        if noise not in NOISE:
            problems.append(f"{p.name}: noise must be one of {sorted(NOISE)}, got '{noise}'")
            continue
        if not scenarios[scenario]["script"] and not overrides.get(p.name, {}).get("transcript_override"):
            problems.append(f"{p.name}: scenario {scenario} has no script "
                            "(spontaneous set) — needs a transcript_override "
                            "before it can be scored")

        # Clipped-recording check. Two different STT models truncating at the
        # same word means the audio is short, not that the models failed.
        script = scenarios[scenario]["script"]
        if script:
            secs = duration_seconds(p)
            if secs is not None:
                words = len(script.split())
                floor = words / MAX_WORDS_PER_SEC
                if secs < floor:
                    clipped.append(
                        f"{p.name}: {secs:.1f}s for a {words}-word line "
                        f"({words/secs:.1f} words/sec) — verify it isn't cut off"
                    )

        canonical_name = stem + p.suffix.lower()
        if canonical_name != p.name:
            renames.append((p, canonical_name, notes))

        rows.append({
            # Record the name we'd use after --fix, so the manifest and the
            # files agree once renamed.
            "audio_file": canonical_name,
            "scenario_id": scenario,
            "speaker_id": speaker,
            "noise_condition": noise,
            "transcript_override": overrides.get(p.name, {}).get("transcript_override", ""),
            "bp_override": overrides.get(p.name, {}).get("bp_override", ""),
        })

    if renames:
        verb = "Renaming" if args.fix else "Would rename (pass --fix to apply)"
        print(f"{verb} {len(renames)} file(s):")
        for src, dst, notes in renames:
            print(f"  {src.name}  →  {dst}" + (f"   [{'; '.join(notes)}]" if notes else ""))
            if args.fix:
                target = src.with_name(dst)
                if target.exists():
                    problems.append(f"{src.name}: cannot rename, {dst} already exists")
                else:
                    src.rename(target)
        print()

    # ── Report coverage so gaps show up before the recording session ends ──
    speakers = Counter(r["speaker_id"] for r in rows)
    langs = Counter(scenarios[r["scenario_id"]]["language_pair"] for r in rows)
    noises = Counter(r["noise_condition"] for r in rows)

    print(f"{len(rows)} usable recordings from {len(speakers)} speaker(s)")
    print(f"  speakers : {dict(sorted(speakers.items()))}")
    print(f"  languages: {dict(sorted(langs.items()))}")
    print(f"  noise    : {dict(sorted(noises.items()))}")

    if not langs.get("en"):
        print("\n  ⚠️  No English control recordings. Without Set E you cannot compute\n"
              "      the code-switch penalty — it's the baseline everything is measured against.")

    if clipped:
        print(f"\n  ⚠️  {len(clipped)} recording(s) are unusually short for their script:")
        for c in clipped:
            print(f"      - {c}")
        print("      ADVISORY, not a verdict. Play each one, or check that a")
        print("      transcript reaches the final word of the script. Code-switched")
        print("      lines are read faster than English, so this check is noisier")
        print("      on the T and P sets than on the E control.")

    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")

    if args.dry_run:
        return
    if not rows:
        sys.exit("\nNothing valid to write.")

    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {MANIFEST} ({len(rows)} rows)")
    if overrides:
        print(f"Preserved {len(overrides)} hand-transcription(s).")


if __name__ == "__main__":
    main()
