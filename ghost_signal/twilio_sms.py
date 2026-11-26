"""Minimal Twilio helpers: check the webhook signature and send an SMS.

Uses plain HTTP so the project needs no Twilio SDK.
Signature rules: https://www.twilio.com/docs/usage/webhooks/webhooks-security
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from xml.sax.saxutils import escape

import httpx

from .config import settings


def expected_signature(auth_token: str, url: str, params: dict[str, str]) -> str:
    """HMAC-SHA1 of the full URL followed by each POST param (sorted by name) as name+value."""
    payload = url + "".join(f"{k}{params[k]}" for k in sorted(params))
    digest = hmac.new(auth_token.encode(), payload.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


def signature_ok(auth_token: str, url: str, params: dict[str, str], signature: str) -> bool:
    return hmac.compare_digest(expected_signature(auth_token, url, params), signature or "")


def twiml(message: str | None) -> str:
    """TwiML reply. None = reply nothing now (we send it later through the API)."""
    if message is None:
        return '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
    return f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{escape(message)}</Message></Response>'


def send_sms(to: str, body: str) -> None:
    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
    r = httpx.post(
        url,
        data={"To": to, "From": settings.twilio_from_number, "Body": body},
        auth=(settings.twilio_account_sid, settings.twilio_auth_token),
        timeout=15,
    )
    r.raise_for_status()


def place_call(to: str, twiml_url: str) -> None:
    """Start an outgoing voice call; Twilio fetches the call's TwiML from `twiml_url` (POST)."""
    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Calls.json"
    r = httpx.post(
        url,
        data={"To": to, "From": settings.twilio_from_number, "Url": twiml_url, "Method": "POST", "Timeout": "30"},
        auth=(settings.twilio_account_sid, settings.twilio_auth_token),
        timeout=15,
    )
    r.raise_for_status()


def voice_twiml(parts: list[str], language: str, voice: str, gather_action: str | None = None,
                after_gather: str | None = None) -> str:
    """Spoken TwiML. With `gather_action`, the speech waits for one key press sent to that URL."""
    say = "".join(
        f'<Say language="{escape(language)}" voice="{escape(voice)}">{escape(p)}</Say><Pause length="1"/>'
        for p in parts
    )
    if gather_action:
        body = (f'<Gather numDigits="1" timeout="8" action="{escape(gather_action)}" method="POST">{say}</Gather>'
                + (f'<Say language="{escape(language)}" voice="{escape(voice)}">{escape(after_gather)}</Say>'
                   if after_gather else ""))
    else:
        body = say
    return f'<?xml version="1.0" encoding="UTF-8"?><Response>{body}</Response>'
