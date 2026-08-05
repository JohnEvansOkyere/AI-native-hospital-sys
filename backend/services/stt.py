"""
Speech-to-text providers for VeloxaCare.

One interface, four providers:
  - SaharaSTT:        Intron Sahara sync endpoint (African-built, code-switch aware)
  - OpenAIWhisperSTT: OpenAI's hosted whisper-1 (frontier commercial default)
  - CartesiaSTT:      Cartesia Ink (commercial, latency-optimised)
  - LocalWhisperSTT:  faster-whisper open weights, fully local (zero API dependency)

This module is the single source of truth for STT: the live agent transcribes
patient voice notes with it, and benchmark/stt_providers.py imports the same
classes. So the models we benchmark are literally the models driving the agent.

Graceful degradation, same contract as ai.py: nothing here raises on a missing
key or a dead network. `transcribe()` always returns a TranscriptionResult, and
an unconfigured or failing provider produces `text=""` plus an `error` the
caller can surface to the patient in plain language.

`language` is the benchmark's language_pair value ("en" | "tw-en" | "pcm-en");
each provider maps it to what its own API expects.
"""

import asyncio
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

SAHARA_SYNC_URL = "https://infer.voice.intron.io/file/v1/upload/sync"
# Sahara rate limit: 30 requests/minute
SAHARA_MIN_INTERVAL_S = 2.1

# language_pair -> Sahara use_language_asr_input code.
# Confirmed against docs.voice.intron.io/docs/stt/supported-languages: the table
# includes ak (Akan), tw (Twi), pcm (Pidgin) and gaa (Ga) — Ghana is well covered.
# The table lists single languages only, no explicit "xx-en" pair codes, so a
# code-switched utterance is sent under its non-English code and Sahara's
# code-switching handling does the rest. Still worth confirming live with
# benchmark/probe_sahara.py, since "documented" and "enabled on your key" differ.
SAHARA_LANG = {"en": "en", "tw-en": "tw", "pcm-en": "pcm", "gaa-en": "gaa"}
SAHARA_LANG_FALLBACK = "en"

# ── Cartesia Ink ──────────────────────────────────────────────────────────────
CARTESIA_STT_URL = "https://api.cartesia.ai/stt"
CARTESIA_VERSION = "2026-03-01"
# ink-2 is current but English-only; ink-whisper is the multilingual batch model.
CARTESIA_MODEL = "ink-whisper"

# Cartesia's batch endpoint takes an ISO-639-1 hint and DEFAULTS TO "en" when
# omitted — there is no auto-detect here. ink-whisper inherits Whisper's ~99
# languages, which contain no Twi, Akan, Ga or Pidgin, so for our code-switched
# sets there is no correct code to send. We hint only on the English control and
# let the rest fall back to English mode.
#
# That is the finding, not a bug in this client: the fastest commercial speech
# model on the market cannot name the language our patients are speaking. Same
# is true of both Whisper entries. Sahara is the only one of the four with tw /
# ak / pcm / gaa. That contrast is the benchmark's headline.
CARTESIA_LANG = {"en": "en"}

LANGUAGE_LABELS = {
    "en": "English",
    "tw-en": "Twi–English",
    "pcm-en": "Pidgin–English",
    "gaa-en": "Ga–English",
}


@dataclass
class TranscriptionResult:
    """What every provider returns. `text` is empty iff transcription failed."""
    text: str
    provider: str
    language: str = "en"
    latency_ms: int = 0
    error: str = ""
    meta: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return bool(self.text.strip())


# ── Providers ─────────────────────────────────────────────────────────────────

class SaharaSTT:
    name = "sahara"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("INTRON_API_KEY")
        if not self.api_key:
            raise ValueError("INTRON_API_KEY not set")
        self._last_call = 0.0

    def transcribe(self, audio_path: str, language: str = "en") -> str:
        # Space calls to respect the 30 req/min limit
        wait = SAHARA_MIN_INTERVAL_S - (time.time() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.time()

        with open(audio_path, "rb") as f:
            resp = requests.post(
                SAHARA_SYNC_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                data={
                    "audio_file_name": Path(audio_path).name,
                    "use_language_asr_input": SAHARA_LANG.get(language, SAHARA_LANG_FALLBACK),
                },
                files={"audio_file_blob": f},
                timeout=120,
            )
        resp.raise_for_status()
        return resp.json()["data"]["audio_transcript"]


class OpenAIWhisperSTT:
    name = "openai_whisper"

    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError("OPENAI_API_KEY not set")
        from openai import OpenAI

        self.client = OpenAI(api_key=key)

    def transcribe(self, audio_path: str, language: str = "en") -> str:
        # Deliberately no language hint: forcing language=en on code-switched
        # audio biases the model; auto-detect is its realistic deployment mode.
        with open(audio_path, "rb") as f:
            resp = self.client.audio.transcriptions.create(model="whisper-1", file=f)
        return resp.text


class SaharaEnglishSTT(SaharaSTT):
    """Sahara pinned to the English model regardless of the set's language.

    Exists because of a real, dated finding. Intron's monolingual `tw` model
    returns an empty transcript on Twi–English code-switched speech — the English
    half (numerals, drug names) is not something it emits — while the same audio
    under the `en` hint yields usable text and correct BP extraction. The
    Akan–English *code-switch* pair, which is what these utterances actually need,
    had not shipped at time of testing (Intron: rolling out the week of 10 Aug 2026).

    Benchmarking both configurations is the point: the choice of language hint
    moves the result more than the choice of model does, and a report that showed
    only one configuration would be misleading either way.
    """

    name = "sahara_en"

    def transcribe(self, audio_path: str, language: str = "en") -> str:
        return super().transcribe(audio_path, language="en")


class CartesiaSTT:
    """Cartesia Ink batch STT — https://docs.cartesia.ai/api-reference/stt/transcribe

    Included as a second commercial datapoint and, more usefully, as the
    latency-optimised end of the market: Cartesia sells speed. Pairing its
    accuracy against Sahara's gives the report a quality-vs-latency axis rather
    than a single ranking.

    Honest caveat for the write-up: ink-whisper is Whisper-derived, so it is not
    architecturally independent of the two Whisper entries. It is a distinct
    commercial product with its own tuning and serving, which is why it earns a
    column — but do not present it as a fourth independent architecture.
    """

    name = "cartesia"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("CARTESIA_API_KEY")
        if not self.api_key:
            raise ValueError("CARTESIA_API_KEY not set")
        self.model = os.getenv("CARTESIA_STT_MODEL", CARTESIA_MODEL)

    def transcribe(self, audio_path: str, language: str = "en") -> str:
        data = {"model": self.model}
        # Only send a hint we have reason to believe the model knows (see
        # CARTESIA_LANG). Omitting it means Cartesia defaults to English, which
        # is exactly the English-mode fallback we want to measure.
        hint = CARTESIA_LANG.get(language)
        if hint:
            data["language"] = hint

        with open(audio_path, "rb") as f:
            resp = requests.post(
                CARTESIA_STT_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Cartesia-Version": CARTESIA_VERSION,
                },
                data=data,
                files={"file": (Path(audio_path).name, f)},
                timeout=120,
            )
        resp.raise_for_status()
        return resp.json()["text"]


class LocalWhisperSTT:
    name = "local_whisper"

    def __init__(self, model_size: str | None = None):
        from faster_whisper import WhisperModel

        size = model_size or os.getenv("WHISPER_LOCAL_MODEL", "base")
        self.model_size = size
        self.model = WhisperModel(size, device="cpu", compute_type="int8")
        self.name = f"local_whisper_{size}"

    def transcribe(self, audio_path: str, language: str = "en") -> str:
        # Auto-detect, same rationale as OpenAIWhisperSTT.
        segments, _info = self.model.transcribe(audio_path)
        return " ".join(seg.text.strip() for seg in segments)


REGISTRY = {
    "sahara": SaharaSTT,
    "sahara_en": SaharaEnglishSTT,
    "openai": OpenAIWhisperSTT,
    "cartesia": CartesiaSTT,
    "local": LocalWhisperSTT,
}

# Order the live agent tries when STT_PROVIDER isn't pinned. Sahara first —
# it's the one built for the code-switching this product actually receives.
# Local last: it always works, so anything after it would be unreachable.
DEFAULT_ORDER = ["sahara", "cartesia", "openai", "local"]


def build_providers(names: list[str]) -> list:
    """Instantiate providers by short name. Raises — used by the benchmark,
    where a misconfigured provider should fail loudly rather than silently
    drop a column from the results table."""
    providers = []
    for n in names:
        if n not in REGISTRY:
            raise ValueError(f"Unknown provider '{n}'. Choose from: {list(REGISTRY)}")
        providers.append(REGISTRY[n]())
    return providers


# ── Live-agent path (cached, never raises) ────────────────────────────────────

_cache: dict[str, object] = {}

# Providers that were configured but failed in practice (bad key, wrong account
# tier, network). Recorded so the UI can say which model is *actually* serving
# rather than which one we hoped would — they diverge exactly when it matters.
_degraded: dict[str, str] = {}


def get_provider(name: str):
    """Instantiate and cache a provider, or return None if unavailable.
    Local whisper especially is expensive to construct — load the weights once."""
    if name in _cache:
        return _cache[name] or None
    try:
        _cache[name] = REGISTRY[name]()
    except Exception:
        # Missing key, missing package, or no model weights — all mean
        # "this provider isn't available here", which is not an error.
        _cache[name] = None
    return _cache[name]


def configured_providers() -> list[str]:
    """Which providers could plausibly run, by config alone (no weights loaded).
    Used by /api/stt/status so the UI can tell the user what's live."""
    out = []
    if os.getenv("INTRON_API_KEY"):
        out.append("sahara")
    if os.getenv("OPENAI_API_KEY"):
        out.append("openai")
    if os.getenv("CARTESIA_API_KEY"):
        out.append("cartesia")
    try:
        import faster_whisper  # noqa: F401
        out.append("local")
    except ImportError:
        pass
    return out


def transcribe_sync(audio_path: str, language: str = "en",
                    provider: str | None = None) -> TranscriptionResult:
    """Transcribe with the named provider, or the first one that works.

    Never raises. A total failure comes back as an empty-text result carrying
    the reason, so the demo degrades to "we couldn't hear that, please type it"
    instead of a 500.
    """
    order = [provider] if provider else (
        [os.getenv("STT_PROVIDER")] if os.getenv("STT_PROVIDER") else DEFAULT_ORDER
    )
    order = [n for n in order if n in REGISTRY]
    errors = []

    for name in order:
        p = get_provider(name)
        if p is None:
            errors.append(f"{name}: not configured")
            continue
        started = time.time()
        try:
            text = p.transcribe(audio_path, language=language)
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__}: {e}")
            _degraded[name] = str(e)[:200]
            continue
        latency_ms = int((time.time() - started) * 1000)
        _degraded.pop(name, None)   # recovered
        if not text.strip():
            errors.append(f"{name}: empty transcript")
            continue
        return TranscriptionResult(
            text=text.strip(),
            provider=getattr(p, "name", name),
            language=language,
            latency_ms=latency_ms,
            meta={"fallbacks_tried": errors} if errors else {},
        )

    return TranscriptionResult(
        text="", provider="none", language=language,
        error="; ".join(errors) or "no STT provider configured",
    )


async def transcribe(audio_path: str, language: str = "en",
                     provider: str | None = None) -> TranscriptionResult:
    """Async wrapper — the provider SDKs are blocking, so keep them off the
    event loop or one voice note stalls every open WebSocket."""
    return await asyncio.to_thread(transcribe_sync, audio_path, language, provider)
