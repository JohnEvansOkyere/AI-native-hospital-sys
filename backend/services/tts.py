"""
Text-to-speech providers for VeloxaCare.

The mirror image of stt.py: one interface, two providers.
  - IntronTTS:   Intron's synchronous /tts/v1/generate (African accents, Pidgin)
  - CartesiaTTS: Cartesia Sonic (latency-optimised, broad commercial default)

Why this exists: a patient who sends a voice note is often a patient who reads
with difficulty. Answering them in text alone throws away the accessibility the
voice channel just bought us. So when a message arrives as speech, the reply
goes back as speech.

Same invariants as stt.py — and for the same reason. This module knows nothing
about patients, messages, adherence or WhatsApp. It takes text and returns audio
plus provenance, so the same layer can later voice clinician callbacks, IVR and
outbound reminders without being untangled from the chat path first.

Callers say which containers they can play via `accept`, in preference order,
the way an HTTP client sends Accept. That is how the browser pane and WhatsApp
get different formats out of the same function without this module ever learning
what a channel is.

Graceful degradation, same contract as ai.py and stt.py: nothing here raises on
a missing key or a dead network. `synthesize()` always returns a SynthesisResult,
and an unconfigured or failing provider produces `audio=b""` plus an `error`.
A silent failure here costs the patient nothing — they still get the text.
"""

import asyncio
import logging
import os
import re
import time
from dataclasses import dataclass, field

import requests

logger = logging.getLogger(__name__)

# ── Intron TTS ────────────────────────────────────────────────────────────────
# docs.voice.intron.io/docs/tts/tts-generate — synchronous, ≤4096 characters,
# 30 requests/minute, and it can answer 503 with a text_id instead of audio when
# generation runs past 120s. We treat that as a failure and fall through: a reply
# that arrives after the patient has closed WhatsApp is not a reply.
#
# The streaming WebSocket endpoint (/tts/v1/stream) exists and is the right tool
# for a live voice call, where you want the first syllable before the last word
# is generated. It is the wrong tool here: a WhatsApp voice note is a file, and
# we cannot send it until it is complete anyway. Use the sync endpoint until
# there is a call to stream into.
INTRON_TTS_URL = "https://infer.voice.intron.io/tts/v1/generate"
INTRON_MIN_INTERVAL_S = 2.1      # 30 req/min, same limiter as Sahara STT
INTRON_MAX_CHARS = 4096

# Give up on Intron well before its own 120s deadline.
#
# Matching their deadline is the worst possible value, and we shipped it that
# way: on 5 Aug 2026 Intron's queue backed up, every request ran the full 120s
# to a 503, and patients waited 2m02s for a reply Cartesia then synthesised in
# 0.7s. Healthy Intron responses that day were 8.9s and 17-25s, so 20s keeps the
# African accent whenever the service is actually up and caps the loss when it
# isn't. Raise it if you would rather wait than switch voices.
INTRON_TIMEOUT_S = float(os.getenv("INTRON_TTS_TIMEOUT_S", "20"))
# The generated file is a plain CDN download once synthesis is done, so it gets
# its own smaller budget rather than eating the synthesis one.
INTRON_DOWNLOAD_TIMEOUT_S = 30.0

# Intron's TTS accent list has no Twi, Akan or Ga, and no Ghanaian English —
# docs.voice.intron.io/docs/tts/supported-languages-and-accents. English accents
# are afrikaans, hausa, igbo, luganda, sepedi, swahili, setswana, xhosa, yoruba,
# zulu; Pidgin (pcm) ships as its own language.
#
# So for Ghana the honest position is: Pidgin is genuinely covered, and Twi/Ga
# are not covered at all. Note the asymmetry with STT, where Sahara *does* have
# tw/ak/gaa — recognition of Ghanaian languages is ahead of synthesis of them.
# Say that plainly in any write-up rather than implying a Twi voice exists.
#
# Default accent is hausa: of the ten English accents offered it is the only one
# also spoken in Ghana (Zongo communities), which makes it the least wrong
# stand-in for a Ghanaian voice. Override per deployment.
INTRON_TTS_ACCENT = os.getenv("INTRON_TTS_ACCENT", "hausa")
INTRON_TTS_GENDER = os.getenv("INTRON_TTS_GENDER", "female")

# language_pair (the benchmark's codes, shared with stt.py) -> Intron TTS
# (voice_language, voice_accent). Twi and Ga fall back to accented English
# because the alternative is no audio at all.
INTRON_VOICE = {
    "en":     ("en", INTRON_TTS_ACCENT),
    "pcm-en": ("pcm", "pidgin"),
    "tw-en":  ("en", INTRON_TTS_ACCENT),
    "gaa-en": ("en", INTRON_TTS_ACCENT),
}

# ── Cartesia TTS ──────────────────────────────────────────────────────────────
# docs.cartesia.ai/api-reference/tts/bytes — returns raw audio bytes, no polling.
CARTESIA_TTS_URL = "https://api.cartesia.ai/tts/bytes"
CARTESIA_VERSION = "2026-03-01"          # keep in step with stt.py
CARTESIA_TTS_MODEL = "sonic-3"
# Cartesia voices are UUIDs, not names. This is their documented sample voice;
# pick a better-suited one from play.cartesia.ai and set CARTESIA_TTS_VOICE_ID.
CARTESIA_DEFAULT_VOICE = "f786b574-daa5-4673-aa0c-cbe3e8534c02"
# Cartesia's language list is the usual ~40 world languages: no Twi, Akan, Ga or
# Pidgin, exactly as with its STT model. Everything we send is spoken as English.
CARTESIA_LANG = {"en": "en", "tw-en": "en", "pcm-en": "en", "gaa-en": "en"}

# Container -> (file suffix, mime type). WhatsApp accepts audio/mpeg and
# audio/ogg (Opus only); browsers accept all three.
FORMATS = {
    "mp3": (".mp3", "audio/mpeg"),
    "ogg": (".ogg", "audio/ogg"),
    "wav": (".wav", "audio/wav"),
}

# What a caller gets if it doesn't care — a browser <audio> element plays any of
# these, so the first provider in the chain decides.
DEFAULT_ACCEPT = ("mp3", "ogg", "wav")


@dataclass
class SynthesisResult:
    """What every provider returns. `audio` is empty iff synthesis failed."""
    audio: bytes = b""
    fmt: str = ""
    mime: str = ""
    suffix: str = ""
    provider: str = "none"
    voice: str = ""
    language: str = "en"
    latency_ms: int = 0
    error: str = ""
    meta: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return bool(self.audio)


# ── Making bot copy speakable ─────────────────────────────────────────────────

# Replies are written for a WhatsApp bubble, not for a voice. Emoji read aloud
# as "warning sign selector" and "128/82" reads as a fraction, so normalise
# before synthesis. The stored message text is untouched — this is a rendering
# concern, and the clinical record keeps the exact words we sent.
_EMOJI = re.compile(
    "[" "\U0001F000-\U0001FAFF" "\U00002600-\U000027BF"
    "\U0000FE00-\U0000FE0F" "\U00002190-\U000021FF" "\U00002B00-\U00002BFF" "]+"
)
_BP = re.compile(r"\b(\d{2,3})\s*/\s*(\d{2,3})\b")


def speakable(text: str) -> str:
    """Turn a chat reply into something a TTS voice can read aloud sensibly."""
    out = _EMOJI.sub(" ", text)
    out = _BP.sub(r"\1 over \2", out)          # "128/82" -> "128 over 82"
    out = out.replace("—", ", ").replace("…", ".")
    out = re.sub(r"\s+([,.!?])", r"\1", out)      # emoji removal leaves " ,"
    out = re.sub(r"([,.!?])\1+", r"\1", out)
    out = re.sub(r"\s+", " ", out).strip()
    return out[:INTRON_MAX_CHARS]


# ── Providers ─────────────────────────────────────────────────────────────────

class IntronTTS:
    name = "intron"

    # Intron names its containers wav/opus; opus comes back Ogg-wrapped, which
    # is the one thing WhatsApp will take as a voice note.
    CONTAINERS = {"ogg": "opus", "wav": "wav"}

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("INTRON_API_KEY")
        if not self.api_key:
            raise ValueError("INTRON_API_KEY not set")
        self._last_call = 0.0

    def synthesize(self, text: str, language: str, accept: tuple) -> tuple[bytes, str, str]:
        fmt = next((f for f in accept if f in self.CONTAINERS), None)
        if fmt is None:
            raise ValueError(f"intron cannot produce any of {accept}")

        voice_language, voice_accent = INTRON_VOICE.get(language, INTRON_VOICE["en"])

        wait = INTRON_MIN_INTERVAL_S - (time.time() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.time()

        resp = requests.post(
            INTRON_TTS_URL,
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json"},
            json={
                "text": text,
                "voice_language": voice_language,
                "voice_accent": voice_accent,
                "voice_gender": os.getenv("INTRON_TTS_GENDER", INTRON_TTS_GENDER),
                "output_audio_format": self.CONTAINERS[fmt],
            },
            timeout=INTRON_TIMEOUT_S,
        )
        resp.raise_for_status()

        # The 503-with-a-text_id path is a deferred result, not audio: the job
        # is queued and /tts/v1/status/{text_id} will have it eventually. That
        # is no use to a patient waiting on a reply — one observed job was still
        # PROCESSING six minutes later — so raising here sends us to the next
        # provider instead of stalling the conversation.
        data = resp.json().get("data") or {}
        audio_url = data.get("audio_path")
        if not audio_url:
            raise RuntimeError(f"no audio_path in response: {str(data)[:120]}")

        audio = requests.get(audio_url, timeout=INTRON_DOWNLOAD_TIMEOUT_S)
        audio.raise_for_status()
        return audio.content, fmt, f"{voice_accent}/{voice_language}"


class CartesiaTTS:
    """Cartesia Sonic — https://docs.cartesia.ai/api-reference/tts/bytes

    The latency end of the market, and here the pragmatic one: it returns MP3
    bytes directly, which WhatsApp accepts without any transcoding. Second in
    the chain rather than first because its voices are not African-accented —
    speed does not make up for a patient not recognising the voice as theirs.
    """

    name = "cartesia"

    CONTAINERS = ("mp3", "wav")

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("CARTESIA_API_KEY")
        if not self.api_key:
            raise ValueError("CARTESIA_API_KEY not set")
        self.model = os.getenv("CARTESIA_TTS_MODEL", CARTESIA_TTS_MODEL)
        self.voice_id = os.getenv("CARTESIA_TTS_VOICE_ID", CARTESIA_DEFAULT_VOICE)

    def synthesize(self, text: str, language: str, accept: tuple) -> tuple[bytes, str, str]:
        fmt = next((f for f in accept if f in self.CONTAINERS), None)
        if fmt is None:
            raise ValueError(f"cartesia cannot produce any of {accept}")

        output_format = (
            {"container": "mp3", "sample_rate": 24000, "bit_rate": 128000}
            if fmt == "mp3" else
            {"container": "wav", "encoding": "pcm_s16le", "sample_rate": 24000}
        )

        resp = requests.post(
            CARTESIA_TTS_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Cartesia-Version": CARTESIA_VERSION,
                "Content-Type": "application/json",
            },
            json={
                "model_id": self.model,
                "transcript": text,
                "voice": {"mode": "id", "id": self.voice_id},
                "language": CARTESIA_LANG.get(language, "en"),
                "output_format": output_format,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.content, fmt, self.voice_id


REGISTRY = {
    "intron": IntronTTS,
    "cartesia": CartesiaTTS,
}

# Order tried when TTS_PROVIDER isn't pinned. Intron first: a West African voice
# is the point, and Cartesia is the fallback that guarantees the patient hears
# *something*. Unlike STT there is no offline tier — synthesis needs a network.
#
# The trade-off is real and worth measuring before you accept this default.
# On a one-sentence reply (5 Aug 2026, from Accra): Intron 17–25s, Cartesia 2.8s.
# WhatsApp is asynchronous, so 25s is a delay rather than a failure, and an
# accent the patient recognises is worth more than latency in a channel nobody
# holds to their ear. If your deployment disagrees, set TTS_ORDER=cartesia,intron
# — which keeps the fallback, unlike pinning TTS_PROVIDER.
DEFAULT_ORDER = ["intron", "cartesia"]


def provider_order() -> list[str]:
    configured = os.getenv("TTS_ORDER")
    if not configured:
        return DEFAULT_ORDER
    return [n.strip() for n in configured.split(",") if n.strip() in REGISTRY] or DEFAULT_ORDER


# ── Live-agent path (cached, never raises) ────────────────────────────────────

_cache: dict[str, object] = {}

# Providers configured but failing in practice, so /api/tts/status can report
# which voice is actually serving rather than which one we hoped would.
_degraded: dict[str, str] = {}

# ── Circuit breaker ───────────────────────────────────────────────────────────
#
# A timeout is bounded per request but unbounded across a conversation: during
# the 5 Aug 2026 Intron outage every single message paid the full wait before
# falling through. After TTS_TRIP_AFTER consecutive failures a provider is
# skipped for TTS_COOLDOWN_S, so an outage costs the wait once rather than once
# per reply.
#
# Deliberately in-memory, and deliberately not depended on: serverless instances
# come and go, so a cold one will retry the sick provider and re-trip. That is
# the correct failure mode — a breaker that survived deploys could keep a
# recovered provider benched with no way to notice. This is an optimisation, and
# correctness never rests on it.
_TRIP_AFTER = int(os.getenv("TTS_TRIP_AFTER", "2"))
_COOLDOWN_S = float(os.getenv("TTS_COOLDOWN_S", "600"))

_consecutive_failures: dict[str, int] = {}
_skip_until: dict[str, float] = {}


def _note_failure(name: str) -> None:
    n = _consecutive_failures.get(name, 0) + 1
    _consecutive_failures[name] = n
    if n >= _TRIP_AFTER:
        _skip_until[name] = time.time() + _COOLDOWN_S
        logger.warning(
            "TTS provider %r failed %d times in a row; benching it for %.0fs",
            name, n, _COOLDOWN_S,
        )


def _note_success(name: str) -> None:
    _consecutive_failures.pop(name, None)
    _skip_until.pop(name, None)


def cooling_down(name: str) -> float:
    """Seconds until this provider is worth trying again; 0 if it's live."""
    return max(0.0, _skip_until.get(name, 0.0) - time.time())


def get_provider(name: str):
    if name in _cache:
        return _cache[name] or None
    try:
        _cache[name] = REGISTRY[name]()
    except Exception:
        _cache[name] = None          # missing key — not an error, just absent
    return _cache[name]


def configured_providers() -> list[str]:
    """Which providers could plausibly run, by config alone."""
    out = []
    if os.getenv("INTRON_API_KEY"):
        out.append("intron")
    if os.getenv("CARTESIA_API_KEY"):
        out.append("cartesia")
    return out


def mode() -> str:
    """When the agent speaks: mirror | always | off.

    'mirror' — the default — answers voice with voice and text with text. It
    matches the patient's own channel, which is both the polite behaviour and
    the cheap one: no synthesis credit is spent on patients who type.
    """
    value = (os.getenv("TTS_MODE") or "mirror").strip().lower()
    return value if value in ("mirror", "always", "off") else "mirror"


def should_speak(inbound_was_voice: bool) -> bool:
    m = mode()
    if m == "off" or not configured_providers():
        return False
    return m == "always" or inbound_was_voice


def synthesize_sync(text: str, language: str = "en", provider: str | None = None,
                    accept: tuple = DEFAULT_ACCEPT) -> SynthesisResult:
    """Speak `text` with the named provider, or the first one that works.

    Never raises. Total failure comes back as an empty-audio result carrying the
    reason, and the caller simply sends the text reply on its own — which is
    what a patient gets today, so a dead TTS key can never make the bot worse
    than it was before it had a voice.
    """
    spoken = speakable(text)
    if not spoken:
        return SynthesisResult(language=language, error="nothing to speak")

    order = [provider] if provider else (
        [os.getenv("TTS_PROVIDER")] if os.getenv("TTS_PROVIDER") else provider_order()
    )
    order = [n for n in order if n in REGISTRY]

    # Step over benched providers — but only when choosing for ourselves. An
    # explicit `provider=` is an operator saying "use this one", which must not
    # be silently redirected, and if everything is benched we try anyway:
    # best-effort beats going mute on the strength of a cache.
    if not provider:
        live = [n for n in order if not cooling_down(n)]
        if live:
            order = live

    errors = []

    for name in order:
        p = get_provider(name)
        if p is None:
            # Missing key is a configuration fact, not a fault — never trips.
            errors.append(f"{name}: not configured")
            continue
        started = time.time()
        try:
            audio, fmt, voice = p.synthesize(spoken, language, tuple(accept))
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__}: {e}")
            _degraded[name] = str(e)[:200]
            _note_failure(name)
            continue
        if not audio:
            errors.append(f"{name}: empty audio")
            _note_failure(name)
            continue
        _degraded.pop(name, None)      # recovered
        _note_success(name)
        suffix, mime = FORMATS[fmt]
        return SynthesisResult(
            audio=audio, fmt=fmt, mime=mime, suffix=suffix,
            provider=getattr(p, "name", name), voice=voice, language=language,
            latency_ms=int((time.time() - started) * 1000),
            meta={"fallbacks_tried": errors} if errors else {},
        )

    if errors:
        logger.warning("TTS unavailable, replying in text only: %s", "; ".join(errors))
    return SynthesisResult(
        language=language,
        error="; ".join(errors) or "no TTS provider configured",
    )


async def synthesize(text: str, language: str = "en", provider: str | None = None,
                     accept: tuple = DEFAULT_ACCEPT) -> SynthesisResult:
    """Async wrapper — the provider calls are blocking `requests`, so keep them
    off the event loop or one spoken reply stalls every open WebSocket."""
    return await asyncio.to_thread(synthesize_sync, text, language, provider, accept)
