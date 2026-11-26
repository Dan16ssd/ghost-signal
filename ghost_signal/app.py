"""Web server: Twilio SMS webhook, simulator API, reminder delivery and the phone simulator page.

Run:  uvicorn ghost_signal.app:app --reload
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from . import __version__, answer, countries, store, twilio_sms
from . import lang as L
from .config import settings

log = logging.getLogger(__name__)
STATIC = Path(__file__).parent / "static"
REMINDER_TICK_SECONDS = 20


def deliver_due_reminders(now: float | None = None) -> int:
    """Send every reminder that is due. Web visitors get theirs in the simulator inbox."""
    sent = 0
    for r in store.due_reminders(now):
        if store.opted_out(r.number):
            store.mark(r.id, "cancelled")
        elif r.number.startswith("web:") or not settings.twilio_can_send:
            store.mark(r.id, "inbox")
        else:
            try:
                twilio_sms.send_sms(r.number, answer.due_text(r))
                store.mark(r.id, "sent")
                sent += 1
            except Exception:  # noqa: BLE001
                log.exception("reminder %s to %s failed", r.id, countries.mask(r.number))
                store.mark(r.id, "failed")
    return sent


async def _reminder_loop() -> None:
    while True:
        try:
            await run_in_threadpool(deliver_due_reminders)
        except Exception:  # noqa: BLE001 - keep the loop alive
            log.exception("reminder loop")
        await asyncio.sleep(REMINDER_TICK_SECONDS)


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI):
    store.open_db()
    task = asyncio.create_task(_reminder_loop())
    yield
    task.cancel()


app = FastAPI(title="Ghost Signal", version=__version__, lifespan=lifespan)


def allowed(sender: str, now: float | None = None) -> bool:
    """At most N questions per sender per hour, so texts can't drain the balance."""
    return store.allowed(sender, settings.max_questions_per_hour, now)


@app.get("/")
def simulator() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "version": __version__,
        "twilio_send": settings.twilio_can_send,
        "llm": settings.use_llm,
        **store.stats(),
    }


class Ask(BaseModel):
    text: str = Field(max_length=480)
    country: str | None = Field(default=None, max_length=2)  # simulator: pretend to text from here


def _web_sender(request: Request) -> str:
    return f"web:{request.client.host if request.client else 'unknown'}"


def _limited_reply(text: str, country: countries.Country | None) -> str:
    language = L.detect(text, country.lang if country else None)
    return answer.message("rate_limited", language)


@app.post("/api/ask")
def ask(body: Ask, request: Request) -> dict:
    sender = _web_sender(request)
    country = countries.from_code(body.country)
    if not allowed(sender):
        return {"reply": _limited_reply(body.text, country), "segments": 1, "encoding": "", "kind": "rate_limited"}
    r = answer.handle(body.text, sender=sender, country=country)
    return {"reply": r.text, "segments": r.segments, "encoding": r.encoding, "kind": r.kind, "lang": r.lang}


@app.get("/api/inbox")
def inbox(request: Request) -> dict:
    """Reminders that came due for this simulator visitor."""
    return {"messages": [answer.due_text(r) for r in store.inbox(_web_sender(request))]}


def _reply_later(to: str, text: str) -> None:
    r = answer.handle(text, sender=to)
    if not r.text:
        return
    try:
        twilio_sms.send_sms(to, r.text)
    except Exception:  # noqa: BLE001
        log.exception("sending SMS to %s failed", countries.mask(to))


def _xml(message: str | None) -> Response:
    return Response(twilio_sms.twiml(message or None), media_type="application/xml")


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

    if not store.first_time(params.get("MessageSid")):
        return _xml(None)  # Twilio retried a message we already answered

    sender = params.get("From", "unknown")
    text = params.get("Body", "")[:1600]
    if not allowed(sender):
        if store.opted_out(sender):
            return _xml(None)
        return _xml(_limited_reply(text, countries.from_number(sender)))

    if settings.twilio_can_send:
        # Answer after Twilio's 15 s webhook window: reply empty now, text back when ready.
        background.add_task(_reply_later, sender, text)
        return _xml(None)

    return _xml(answer.handle(text, sender=sender).text)
