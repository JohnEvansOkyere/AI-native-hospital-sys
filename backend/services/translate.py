"""
Text translation for VeloxaCare — GhanaNLP Khaya Translation v2.

Why this exists: the bot writes its replies in simple English, and Khaya gives
us real Twi and Ewe voices (services/tts.py). A Twi voice reading English text
is worse than no Twi voice at all, so before a reply is spoken in the patient's
language it is translated into that language here. The stored message body
stays English — the durable clinical record — and the caller records what was
actually spoken alongside it (messages.spoken_body).

Same invariants as stt.py and tts.py, for the same reasons: this module knows
nothing about patients, messages or channels. Text in, text out, plus
provenance. Weekly reports, clinician summaries and printed leaflets will want
the same function untangled from chat.

Same graceful-degradation contract too: nothing here raises on a missing key
or a dead network. `translate()` always returns a TranslationResult, and a
failure comes back as `text=""` plus an `error` — the caller falls back to the
English reply, which is exactly what the patient got before this existed.

Endpoint verified against GhanaNLP's own client code (Khaya-AI/khaya-claude-skills):
POST {base}/translate with {"in": text, "lang": "eng-twi"} and an
Ocp-Apim-Subscription-Key header; the response body is the translated text as
a JSON string. Requests are capped at 1000 characters, so long text is chunked
on sentence boundaries.
"""

import asyncio
import os
import re
import time
from dataclasses import dataclass, field

import requests

KHAYA_MT_BASE = os.getenv("KHAYA_MT_BASE_URL", "https://translation-api.ghananlp.org/v2")
KHAYA_MT_TIMEOUT_S = float(os.getenv("KHAYA_MT_TIMEOUT_S", "30"))
MAX_CHARS = 1000

# language_pair (the codes shared with stt.py/tts.py) -> Khaya ISO 639-3 code.
# English and Pidgin are absent by design: English needs no translation and
# Khaya has no Pidgin model. Whether MT quality on clinical phrasing is good
# enough to ship is a thing to *measure* (benchmark/probe_khaya.py prints a
# sample) — documented ≠ shipped, and fluent ≠ faithful.
PAIR_TO_ISO = {"tw-en": "twi", "gaa-en": "gaa", "ewe-en": "ewe"}

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+|\n+")


@dataclass
class TranslationResult:
    """What every call returns. `text` is empty iff translation failed."""
    text: str = ""
    provider: str = "none"
    source: str = ""
    target: str = ""
    latency_ms: int = 0
    error: str = ""
    meta: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return bool(self.text.strip())


def available() -> bool:
    return bool(os.getenv("KHAYA_API_KEY"))


def can_render(language_pair: str) -> bool:
    """Can a reply be rendered in this pair's language at all?"""
    return available() and language_pair in PAIR_TO_ISO


def _chunks(text: str, limit: int = MAX_CHARS) -> list[str]:
    if len(text) <= limit:
        return [text]
    out, current = [], ""
    for sentence in _SENTENCE_SPLIT.split(text):
        if not sentence:
            continue
        while len(sentence) > limit:          # one sentence longer than the cap
            cut = sentence.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit
            if current:
                out.append(current)
                current = ""
            out.append(sentence[:cut])
            sentence = sentence[cut:].lstrip()
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= limit:
            current = candidate
        else:
            out.append(current)
            current = sentence
    if current:
        out.append(current)
    return out


def translate_sync(text: str, language_pair: str) -> TranslationResult:
    """Translate an English reply into the pair's Ghanaian language.

    Never raises. An unsupported pair, a missing key, or a failing API all come
    back as an empty-text result carrying the reason.
    """
    iso = PAIR_TO_ISO.get(language_pair)
    if iso is None:
        return TranslationResult(target=language_pair,
                                 error=f"no translation model for '{language_pair}'")
    key = os.getenv("KHAYA_API_KEY")
    if not key:
        return TranslationResult(source="eng", target=iso, error="KHAYA_API_KEY not set")
    if not text.strip():
        return TranslationResult(source="eng", target=iso, error="nothing to translate")

    started = time.time()
    pieces = []
    try:
        for chunk in _chunks(text.strip()):
            resp = requests.post(
                f"{KHAYA_MT_BASE}/translate",
                headers={"Ocp-Apim-Subscription-Key": key,
                         "Content-Type": "application/json"},
                json={"in": chunk, "lang": f"eng-{iso}"},
                timeout=KHAYA_MT_TIMEOUT_S,
            )
            resp.raise_for_status()
            piece = resp.json()
            if not isinstance(piece, str):
                return TranslationResult(
                    source="eng", target=iso,
                    error=f"unexpected response shape: {str(piece)[:120]}",
                )
            pieces.append(piece.strip())
    except Exception as e:
        return TranslationResult(source="eng", target=iso,
                                 error=f"{type(e).__name__}: {e}")

    return TranslationResult(
        text=" ".join(p for p in pieces if p),
        provider="khaya",
        source="eng",
        target=iso,
        latency_ms=int((time.time() - started) * 1000),
    )


async def translate(text: str, language_pair: str) -> TranslationResult:
    """Async wrapper — blocking `requests`, keep it off the event loop."""
    return await asyncio.to_thread(translate_sync, text, language_pair)
