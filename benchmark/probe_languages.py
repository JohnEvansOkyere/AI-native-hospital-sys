"""
Probe which language codes each STT API actually accepts, before we spend a day
recording 100+ files.

Why this exists: Intron's docs list ak/tw/pcm/gaa as supported codes, but
"documented" and "enabled on your key" are different claims, and a recording day
is expensive to redo. Ten minutes here de-risks it. It also tells you whether Ga
('gaa') is worth adding as a fourth recording set.

For Cartesia the expected answer is that no Ghanaian code works — ink-whisper
inherits Whisper's ~99 languages, which have no Twi, Akan, Ga or Pidgin. Confirm
it rather than assume it: "we tested and the endpoint rejects tw" is a citable
benchmark result, while "we assumed it wouldn't work" is not.

Usage:
    export INTRON_API_KEY=...
    export CARTESIA_API_KEY=...
    python probe_languages.py --audio some_clip.m4a
    python probe_languages.py --audio clip.m4a --apis sahara --codes tw,ak,pcm

Any short clip works — even ten seconds of you saying "testing" on your phone.
We are testing whether the API *accepts the code*, not transcription quality.
"""

import argparse
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# Read keys from the repo-root .env, same file the app uses — no exports needed.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from services.stt import (  # noqa: E402
    CARTESIA_MODEL,
    CARTESIA_STT_URL,
    CARTESIA_VERSION,
    SAHARA_MIN_INTERVAL_S,
    SAHARA_SYNC_URL,
)

# The four Ghanaian codes in Intron's docs table (tw=Twi, ak=Akan, pcm=Pidgin,
# gaa=Ga), plus en as a known-good control and sw as the language Intron has
# publicly shipped code-switching for — a useful "is this key fully enabled" signal.
DEFAULT_CODES = ["en", "tw", "ak", "pcm", "gaa", "sw"]

GHANAIAN = [("tw", "Twi"), ("ak", "Akan"), ("pcm", "Pidgin"), ("gaa", "Ga")]


def probe_sahara(api_key: str, audio_path: str, code: str) -> tuple[str, str]:
    try:
        with open(audio_path, "rb") as f:
            resp = requests.post(
                SAHARA_SYNC_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                data={
                    "audio_file_name": Path(audio_path).name,
                    "use_language_asr_input": code,
                },
                files={"audio_file_blob": f},
                timeout=120,
            )
    except Exception as e:
        return "ERROR", f"{type(e).__name__}: {e}"

    if resp.status_code != 200:
        return "REJECTED", f"HTTP {resp.status_code}: {resp.text[:160]}"
    try:
        return "OK", resp.json()["data"]["audio_transcript"][:100]
    except Exception:
        return "ODD", f"200 but unexpected body: {resp.text[:160]}"


def probe_cartesia(api_key: str, audio_path: str, code: str) -> tuple[str, str]:
    try:
        with open(audio_path, "rb") as f:
            resp = requests.post(
                CARTESIA_STT_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Cartesia-Version": CARTESIA_VERSION,
                },
                data={"model": CARTESIA_MODEL, "language": code},
                files={"file": (Path(audio_path).name, f)},
                timeout=120,
            )
    except Exception as e:
        return "ERROR", f"{type(e).__name__}: {e}"

    if resp.status_code != 200:
        return "REJECTED", f"HTTP {resp.status_code}: {resp.text[:160]}"
    try:
        body = resp.json()
        return "OK", f"[detected={body.get('language')}] {body.get('text', '')[:80]}"
    except Exception:
        return "ODD", f"200 but unexpected body: {resp.text[:160]}"


APIS = {
    "sahara": ("INTRON_API_KEY", probe_sahara, SAHARA_MIN_INTERVAL_S),
    "cartesia": ("CARTESIA_API_KEY", probe_cartesia, 0.3),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True, help="Any short audio clip")
    ap.add_argument("--codes", default=",".join(DEFAULT_CODES))
    ap.add_argument("--apis", default="sahara,cartesia")
    args = ap.parse_args()

    if not Path(args.audio).is_file():
        sys.exit(f"No such audio file: {args.audio}")

    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    wanted = [a.strip() for a in args.apis.split(",") if a.strip()]
    accepted: dict[str, list[str]] = {}

    for api in wanted:
        if api not in APIS:
            print(f"Unknown api '{api}', skipping. Choose from: {list(APIS)}\n")
            continue
        env_var, probe, interval = APIS[api]
        key = os.getenv(env_var)
        if not key:
            print(f"── {api}: {env_var} not set, skipping\n")
            continue

        print(f"── {api}: probing {len(codes)} codes with {args.audio}")
        ok = []
        for i, code in enumerate(codes):
            if i:
                time.sleep(interval)   # respect rate limits
            status, detail = probe(key, args.audio, code)
            if status == "OK":
                ok.append(code)
            print(f"   {code:<6} {status:<9} {detail}")
        accepted[api] = ok
        print(f"   accepted: {', '.join(ok) if ok else '(none)'}\n")

    if not accepted:
        sys.exit("No API keys set — nothing probed.")

    # ── What this means for the recording plan ──
    print("=" * 70)
    sahara_ok = accepted.get("sahara")
    if sahara_ok is not None:
        for code, label in GHANAIAN:
            mark = "✓" if code in sahara_ok else "✗"
            print(f"  {mark} Sahara {label} ('{code}')")
        if not any(c in sahara_ok for c, _ in GHANAIAN):
            print(
                "\n  No Ghanaian code accepted despite being in the docs table. That\n"
                "  most likely means the key isn't fully enabled, not that the models\n"
                "  are missing. Ask Intron — Busayo Awobade is both an Intron person\n"
                "  and a challenge organiser (workshops@mlcollective.org). Meanwhile,\n"
                "  run Sahara under 'en' and report that honestly.\n"
                "  Update SAHARA_LANG in backend/services/stt.py to match what you learn."
            )
        elif "gaa" in sahara_ok:
            print(
                "\n  Ga ('gaa') is live — worth a fourth recording set if you can find a\n"
                "  Ga speaker. Low-resource coverage is an explicit bonus criterion."
            )

    cart_ok = accepted.get("cartesia")
    if cart_ok is not None:
        gh = [c for c, _ in GHANAIAN if c in cart_ok]
        if gh:
            print(f"\n  Cartesia unexpectedly accepts: {', '.join(gh)} — add these to\n"
                  "  CARTESIA_LANG in backend/services/stt.py and re-run the benchmark.")
        else:
            print(
                "\n  Cartesia accepts no Ghanaian code, as expected. Keep CARTESIA_LANG\n"
                "  as-is (English control only) and state in the report that the\n"
                "  endpoint was tested and rejects them — a measured result, not an\n"
                "  assumption."
            )

    if sahara_ok and cart_ok is not None:
        only_sahara = [c for c, _ in GHANAIAN if c in sahara_ok and c not in cart_ok]
        if only_sahara:
            print(
                f"\n  HEADLINE: {', '.join(only_sahara)} are addressable on the\n"
                "  African-built model and on none of the others. That contrast is\n"
                "  the benchmark report's opening paragraph."
            )


if __name__ == "__main__":
    main()
