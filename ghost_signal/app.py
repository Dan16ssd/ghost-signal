"""Web server: Twilio SMS webhook, simulator API and the phone simulator page.

Run:  uvicorn ghost_signal.app:app --reload
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from . import answer, twilio_sms
from . import lang as L
from .config import settings

log = logging.getLogger(__name__)
STATIC = Path(__file__).parent / "static"

app = FastAPI(title="Ghost Signal", version="0.1.0")

# phone number -> times of recent questions (in-memory; resets on restart)
_recent: dict[str, deque[float]] = defaultdict(deque)


def allowed(sender: str, now: float | None = None) -> bool:
    """At most N questions per sender per hour, so texts can't drain the balance."""
    now = time.time() if now is None else now
    q = _recent[sender]
    while q and now - q[0] > 3600:
        q.popleft()
    if len(q) >= settings.max_questions_per_hour:
        return False
    q.append(now)
    return True


@app.get("/")
def simulator() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health() -> dict:
    return {"ok": True, "twilio_send": settings.twilio_can_send, "llm": settings.use_llm}


class Ask(BaseModel):
    text: str = Field(max_length=480)


@app.post("/api/ask")
def ask(body: Ask, request: Request) -> dict:
    sender = f"web:{request.client.host if request.client else 'unknown'}"
    if not allowed(sender):
        language = L.detect(body.text)
        return {"reply": L.msg("rate_limited", language), "segments": 1, "encoding": "", "kind": "rate_limited"}
    r = answer.handle(body.text)
    return {"reply": r.text, "segments": r.segments, "encoding": r.encoding, "kind": r.kind}


def _reply_later(to: str, text: str) -> None:
    r = answer.handle(text)
    try:
        twilio_sms.send_sms(to, r.text)
    except Exception:  # noqa: BLE001
        log.exception("sending SMS failed")


@app.post("/sms")
async def sms_webhook(request: Request, background: BackgroundTasks) -> Response:
    form = await request.form()
    params = {k: str(v) for k, v in form.items()}

    if settings.twilio_auth_token:
        url = (settings.public_base_url + request.url.path) if settings.public_base_url else str(request.url)
        if not twilio_sms.signature_ok(
            settings.twilio_auth_token, url, params, request.headers.get("X-Twilio-Signature", "")
        ):
            raise HTTPException(status_code=403, detail="bad signature")

    sender = params.get("From", "unknown")
    text = params.get("Body", "")
    if not allowed(sender):
        return Response(twilio_sms.twiml(L.msg("rate_limited", L.detect(text))), media_type="application/xml")

    if settings.twilio_can_send:
        # Answer after Twilio's 15 s webhook window: reply empty now, text back when ready.
        background.add_task(_reply_later, sender, text)
        return Response(twilio_sms.twiml(None), media_type="application/xml")

    r = answer.handle(text)
    return Response(twilio_sms.twiml(r.text), media_type="application/xml")
