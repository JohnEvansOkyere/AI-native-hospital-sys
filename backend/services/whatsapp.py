"""
WhatsApp Cloud API adapter — Meta Graph client.

Transport only. This module sends messages, downloads media and validates
webhook signatures; it knows nothing about patients, adherence or escalation.
Inbound messages are handed to `ingest_patient_message()` in main.py, which is
the same path the built-in simulator uses, so WhatsApp and the demo pane run
identical agent logic.

Setup (Meta for Developers → your app → WhatsApp → Configuration):
  META_ACCESS_TOKEN     from the API Setup tab
  META_PHONE_NUMBER_ID  from the API Setup tab (NOT the phone number itself)
  META_VERIFY_TOKEN     any random string; paste the same value into the webhook form
  META_APP_SECRET       Settings → Basic; enables request signature checking

Everything degrades gracefully: with no credentials the webhook still starts,
it just declines to send. The demo must never hard-fail on missing config.
"""

import hashlib
import hmac
import logging
import os
from dataclasses import dataclass
from pathlib import Path

import httpx

from config import production_like

logger = logging.getLogger(__name__)

GRAPH_API = os.getenv("META_GRAPH_API", "https://graph.facebook.com/v19.0")

# WhatsApp voice notes arrive as OGG/Opus. Map Meta's mime types onto the
# suffixes stt.py accepts, so the provider SDKs sniff the container correctly.
MIME_SUFFIX = {
    "audio/ogg": ".ogg",
    "audio/opus": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/amr": ".amr",
    "audio/aac": ".m4a",
}


@dataclass(frozen=True)
class SendResult:
    """What Meta accepted, without exposing credentials or patient details."""

    delivered: bool
    message_id: str = ""
    error: str = ""


def _meta_error(response: httpx.Response) -> str:
    """Return the useful, operator-safe part of a Graph API error."""
    try:
        error = response.json().get("error") or {}
        message = str(error.get("message") or "WhatsApp rejected the message")
        code = error.get("code")
        return f"Meta {code}: {message}" if code else message
    except Exception:
        return f"WhatsApp HTTP {response.status_code}"


def is_configured() -> bool:
    return bool(os.getenv("META_ACCESS_TOKEN") and os.getenv("META_PHONE_NUMBER_ID"))


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {os.getenv('META_ACCESS_TOKEN')}"}


def mask_phone(phone: str) -> str:
    """Never log a patient's full number — these are health-adjacent identifiers."""
    return f"{phone[:5]}…{phone[-2:]}" if len(phone) > 7 else "…"


def verify_signature(raw_body: bytes, supplied: str | None) -> bool:
    """Validate Meta's X-Hub-Signature-256 over the raw request body.

    Returns True when META_APP_SECRET is unset — that's the local-dev path, and
    refusing to boot without it would break the offline demo. Set it in
    production; the webhook is otherwise an open endpoint.
    """
    secret = os.getenv("META_APP_SECRET")
    if not secret:
        return not production_like()
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, supplied or "")


def verify_challenge(mode: str | None, token: str | None, challenge: str | None) -> int:
    """Answer Meta's GET verification handshake. Raises ValueError on mismatch."""
    if mode == "subscribe" and token and token == os.getenv("META_VERIFY_TOKEN"):
        logger.info("WhatsApp webhook verified")
        return int(challenge or 0)
    raise ValueError("verify token mismatch")


async def _send_message(to: str, payload: dict) -> SendResult:
    """Send one Cloud API message and preserve Meta's message id or failure."""
    if not is_configured():
        logger.warning("WhatsApp not configured; dropping reply to %s", mask_phone(to))
        return SendResult(False, error="WhatsApp credentials are not configured")

    url = f"{GRAPH_API}/{os.getenv('META_PHONE_NUMBER_ID')}/messages"
    payload = {"messaging_product": "whatsapp", "to": normalize_phone(to), **payload}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                url, json=payload, headers={**_auth_headers(), "Content-Type": "application/json"}
            )
            resp.raise_for_status()
        messages = resp.json().get("messages") or []
        message_id = str(messages[0].get("id") or "") if messages else ""
        return SendResult(True, message_id=message_id)
    except httpx.HTTPStatusError as e:
        error = _meta_error(e.response)
        logger.error("WhatsApp send failed to %s: %s — %s",
                     mask_phone(to), e, e.response.text[:200])
        return SendResult(False, error=error)
    except httpx.HTTPError as e:
        logger.error("WhatsApp HTTP error to %s: %s", mask_phone(to), e)
        return SendResult(False, error=f"WhatsApp connection failed: {type(e).__name__}")


async def send_text_result(to: str, body: str) -> SendResult:
    """Send free text and return the accepted message id or failure reason."""
    return await _send_message(to, {
        "type": "text",
        "text": {"body": body, "preview_url": False},
    })


async def send_text(to: str, body: str) -> bool:
    """Compatibility wrapper used by reply paths that only need success/failure."""
    return (await send_text_result(to, body)).delivered


async def send_template(
    to: str, template_name: str, language_code: str = "en_US",
    body_parameters: list[str] | None = None,
) -> SendResult:
    """Send an approved WhatsApp template for clinic-initiated outreach."""
    template: dict = {
        "name": template_name,
        "language": {"code": language_code},
    }
    if body_parameters:
        template["components"] = [{
            "type": "body",
            "parameters": [{"type": "text", "text": value} for value in body_parameters],
        }]
    return await _send_message(to, {"type": "template", "template": template})


async def send_audio(to: str, audio: bytes, mime: str, filename: str) -> bool:
    """Send a spoken reply as a WhatsApp audio message. Never raises.

    Two hops, the mirror of download_media(): upload the bytes to the media
    endpoint for a media ID, then send a message referencing it.

    Meta accepts audio/aac, audio/amr, audio/mpeg, audio/mp4 and audio/ogg —
    the last one Opus-coded only. Ogg/Opus renders as a proper voice-note bubble
    with a waveform; MP3 arrives as a playable audio attachment. Both play, so
    the caller picks the container and this function stays dumb about it.

    Returns False on any failure so the caller can fall back to text alone,
    which is the reply the patient would have got anyway.
    """
    if not is_configured():
        logger.warning("WhatsApp not configured; dropping voice reply to %s", mask_phone(to))
        return False

    phone_number_id = os.getenv("META_PHONE_NUMBER_ID")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            upload = await client.post(
                f"{GRAPH_API}/{phone_number_id}/media",
                headers=_auth_headers(),
                data={"messaging_product": "whatsapp", "type": mime},
                files={"file": (filename, audio, mime)},
            )
            upload.raise_for_status()
            media_id = upload.json().get("id")
            if not media_id:
                logger.error("Media upload returned no id: %s", upload.text[:200])
                return False

            resp = await client.post(
                f"{GRAPH_API}/{phone_number_id}/messages",
                headers={**_auth_headers(), "Content-Type": "application/json"},
                json={
                    "messaging_product": "whatsapp",
                    "to": normalize_phone(to),
                    "type": "audio",
                    "audio": {"id": media_id},
                },
            )
            resp.raise_for_status()
        return True
    except httpx.HTTPStatusError as e:
        logger.error("WhatsApp audio send failed to %s: %s — %s",
                     mask_phone(to), e, e.response.text[:200])
    except httpx.HTTPError as e:
        logger.error("WhatsApp audio HTTP error to %s: %s", mask_phone(to), e)
    return False


async def download_media(media_id: str, dest_dir: Path, stem: str) -> Path | None:
    """Fetch a voice note by media ID and write it to disk.

    Two hops, per the Cloud API: resolve the ID to a short-lived CDN URL, then
    download that URL with the same bearer token. Returns the saved path, or
    None on any failure — the caller asks the patient to resend.
    """
    if not is_configured():
        return None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            meta = await client.get(f"{GRAPH_API}/{media_id}", headers=_auth_headers())
            meta.raise_for_status()
            info = meta.json()

            media_url = info.get("url")
            if not media_url:
                logger.error("No media URL for %s: %s", media_id, info)
                return None

            mime = (info.get("mime_type") or "").split(";")[0].strip()
            suffix = MIME_SUFFIX.get(mime, ".ogg")

            # The CDN URL still requires the access token.
            blob = await client.get(media_url, headers=_auth_headers())
            blob.raise_for_status()

        dest_dir.mkdir(exist_ok=True)
        path = dest_dir / f"{stem}{suffix}"
        path.write_bytes(blob.content)
        return path
    except Exception as e:
        logger.error("Media download failed for %s: %s", media_id, e)
        return None


def normalize_phone(phone: str) -> str:
    """Reduce a phone number to comparable digits.

    Meta sends E.164 without '+' ("233241000001"); patients are stored with it.
    Stripping non-digits makes both sides comparable without guessing at
    country-code rules.
    """
    return "".join(ch for ch in phone if ch.isdigit())
