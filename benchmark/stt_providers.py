"""
STT provider clients for the code-switch benchmark.

These are re-exported from the live application (`backend/services/stt.py`) rather
than reimplemented here — deliberately. The benchmark's headline claim is that
its numbers describe the real product, so the benchmark must call the exact
same client code, with the same language mapping and the same request
parameters, as the agent serving patients.

Four providers, one interface: transcribe(audio_path, language) -> str.
  - SaharaSTT:        Intron Sahara sync endpoint (African-built, code-switch aware)
  - OpenAIWhisperSTT: OpenAI's hosted whisper-1 (frontier commercial default)
  - CartesiaSTT:      Cartesia Ink (commercial, latency-optimised)
  - LocalWhisperSTT:  faster-whisper open weights, fully local (zero API dependency)

The challenge requires ≥3 models including one Intron Sahara API; these four
give one African-built, two commercial and one open-weights/offline.

`language` is the benchmark's language_pair value ("en" | "tw-en" | "pcm-en");
each provider maps it to what its API expects.

Note the error-handling difference: `build_providers` raises on a misconfigured
provider, because a benchmark that silently drops a column is worse than one
that refuses to start. The live agent uses the fallback path in stt.py instead.
"""

import sys
from pathlib import Path

# backend/ has no __init__.py (namespace package), so importing services.stt
# pulls in stt.py alone — no FastAPI, no Groq, nothing the benchmark venv lacks.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from services.stt import (  # noqa: E402
    CARTESIA_LANG,
    CARTESIA_MODEL,
    CARTESIA_STT_URL,
    CARTESIA_VERSION,
    SAHARA_LANG,
    SAHARA_MIN_INTERVAL_S,
    SAHARA_SYNC_URL,
    CartesiaSTT,
    LocalWhisperSTT,
    OpenAIWhisperSTT,
    SaharaEnglishSTT,
    SaharaSTT,
    build_providers,
)

__all__ = [
    "CARTESIA_LANG",
    "CARTESIA_MODEL",
    "CARTESIA_STT_URL",
    "CARTESIA_VERSION",
    "SAHARA_LANG",
    "SAHARA_MIN_INTERVAL_S",
    "SAHARA_SYNC_URL",
    "CartesiaSTT",
    "LocalWhisperSTT",
    "OpenAIWhisperSTT",
    "SaharaEnglishSTT",
    "SaharaSTT",
    "build_providers",
]
