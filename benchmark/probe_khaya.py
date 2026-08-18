"""
Probe what a GhanaNLP Khaya key can actually do — before citing any of it.

Same lesson as probe_languages.py, learned the hard way with Sahara: documented
≠ shipped, and shipped ≠ enabled on *your* key. This script asks Khaya's own
discovery endpoints what they serve today, runs one sample translation per
Ghanaian language, and (optionally) one transcription and one synthesis, so
every claim about Khaya in a report or demo traces to a measurement with a date
on it.

Usage:
    export KHAYA_API_KEY=...        # https://translation.ghananlp.org
    python probe_khaya.py                       # discovery + sample translations
    python probe_khaya.py --audio clip.ogg --language tw-en   # + one transcription
    python probe_khaya.py --tts                 # + synthesize the Twi sample to a wav

The transcription path goes through the app's own client (stt_providers →
backend/services/stt.py), same as the benchmark and the live agent — so what
this measures is the product, not a lookalike.
"""

import argparse
import json
import os
import sys
import time
from datetime import date

import requests

from stt_providers import KHAYA_ASR_BASE, KhayaSTT

KHAYA_TTS_BASE = os.getenv("KHAYA_TTS_BASE_URL", "https://translation-api.ghananlp.org/tts/v2")
KHAYA_MT_BASE = os.getenv("KHAYA_MT_BASE_URL", "https://translation-api.ghananlp.org/v2")

# One clinically loaded sentence: digits that decide an escalation, and a drug
# name — the two things general ASR/MT get wrong first.
SAMPLE = "Your blood pressure is 142 over 95. Please take your amlodipine today."
MT_TARGETS = ["twi", "gaa", "ewe", "dag"]


def _get(url: str, key: str):
    resp = requests.get(url, headers={"Ocp-Apim-Subscription-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.json()


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    p.add_argument("--audio", help="Audio clip to transcribe (mp3/wav/flac/ogg; others need ffmpeg)")
    p.add_argument("--language", default="tw-en",
                   help="language_pair for the transcription (default tw-en)")
    p.add_argument("--tts", action="store_true",
                   help="Synthesize the translated Twi sample to khaya_tts_sample.wav")
    args = p.parse_args()

    key = os.getenv("KHAYA_API_KEY")
    if not key:
        sys.exit("KHAYA_API_KEY not set. Get one at https://translation.ghananlp.org")

    print(f"# Khaya probe — {date.today().isoformat()}")
    print("# Every claim below is a measurement against this key, today.\n")

    # ── What the key serves ──────────────────────────────────────────────────
    try:
        asr = _get(f"{KHAYA_ASR_BASE}/languages", key)
        print("ASR languages:")
        for lang in sorted(asr.get("languages", []), key=lambda l: l.get("name", "")):
            print(f"  {lang.get('code', '?'):6} {lang.get('name', '')}")
    except Exception as e:
        print(f"ASR /languages FAILED: {e}")

    try:
        tts_langs = _get(f"{KHAYA_TTS_BASE}/languages", key).get("languages", {})
        speakers = _get(f"{KHAYA_TTS_BASE}/speakers", key).get("speakers", {})
        print("\nTTS languages:")
        for name in sorted(tts_langs):
            print(f"  {name}: {tts_langs[name]}")
        print("TTS speakers:")
        for group, ids in speakers.items():
            print(f"  {group}: {', '.join(ids)}")
    except Exception as e:
        print(f"\nTTS discovery FAILED: {e}")

    # ── Sample translations ──────────────────────────────────────────────────
    print(f"\nTranslation samples (eng → x):\n  in: {SAMPLE}")
    twi_text = ""
    for target in MT_TARGETS:
        started = time.time()
        try:
            resp = requests.post(
                f"{KHAYA_MT_BASE}/translate",
                headers={"Ocp-Apim-Subscription-Key": key,
                         "Content-Type": "application/json"},
                json={"in": SAMPLE, "lang": f"eng-{target}"},
                timeout=60,
            )
            resp.raise_for_status()
            out = resp.json()
            ms = int((time.time() - started) * 1000)
            print(f"  eng-{target} ({ms}ms): {out}")
            if target == "twi" and isinstance(out, str):
                twi_text = out
        except Exception as e:
            print(f"  eng-{target} FAILED: {e}")

    # Judge the round trip, not just fluency: did 142/95 and "amlodipine"
    # survive? A native speaker should read these back before any demo.
    print("\n  ⚠ Check by eye: are the digits intact? Is the drug name intact?")

    # ── Optional: one transcription through the app's own client ─────────────
    if args.audio:
        print(f"\nTranscribing {args.audio} as {args.language} via KhayaSTT:")
        started = time.time()
        try:
            text = KhayaSTT().transcribe(args.audio, language=args.language)
            ms = int((time.time() - started) * 1000)
            print(f"  ({ms}ms) {json.dumps(text, ensure_ascii=False)}")
        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}")

    # ── Optional: one synthesis ──────────────────────────────────────────────
    if args.tts:
        text = twi_text or "Me ma wo akye. Wo ho te sɛn?"
        print(f"\nSynthesizing Twi sample: {text}")
        started = time.time()
        try:
            resp = requests.post(
                f"{KHAYA_TTS_BASE}/synthesize",
                headers={"Ocp-Apim-Subscription-Key": key,
                         "Content-Type": "application/json"},
                json={"text": text, "language": "twi", "format": "wav",
                      "speaker_id": "female"},
                timeout=120,
            )
            resp.raise_for_status()
            ms = int((time.time() - started) * 1000)
            out_path = "khaya_tts_sample.wav"
            with open(out_path, "wb") as f:
                f.write(resp.content)
            print(f"  ({ms}ms) {len(resp.content)} bytes → {out_path} — listen to it.")
        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
