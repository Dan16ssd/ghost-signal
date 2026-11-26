"""Web server: Twilio SMS webhook, simulator API, reminder delivery and the phone simulator page.

Run:  uvicorn ghost_signal.app:app --reload
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from . import __version__, answer, countries, meds, store, twilio_sms
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


def _send(to: str, body: str) -> bool:
    """One SMS, unless the number opted out or SMS sending is not configured."""
    if store.opted_out(to) or to.startswith("web:") or not settings.twilio_can_send:
        return False
    try:
        twilio_sms.send_sms(to, body)
        return True
    except Exception:  # noqa: BLE001
        log.exception("SMS to %s failed", countries.mask(to))
        return False


def run_doses(now: float | None = None) -> int:
    """Call (or text) everyone whose medicine is due; after 2 unanswered calls, tell the family."""
    now = time.time() if now is None else now
    calls = 0
    for d in store.doses_to_try(now):
        m = store.med(d.med_id)
        if m is None:
            store.set_dose_state(d.id, "cancelled")
            continue
        if store.opted_out(m.number):
            store.stop_all_meds(m.number)
            continue
        if d.attempts >= meds.MAX_ATTEMPTS:
            answer.finish_dose(d, "missed")
            for contact in store.family_of(m.number):
                c = countries.from_number(contact)
                language = c.lang if c else m.lang
                _send(contact, f"{answer.message('family_alert', language)} {m.number} ({m.what})")
            continue
        retry_at = now + meds.RETRY_MINUTES * 60
        if m.number.startswith("web:"):
            store.dose_tried(d.id, retry_at, ring_web=True)  # the simulator phone rings
            continue
        store.dose_tried(d.id, retry_at)
        voice_ok = (settings.twilio_can_send and settings.voice_calls and settings.public_base_url
                    and meds.can_call(m.lang) and store.used_today("call") < settings.max_calls_per_day)
        if voice_ok:
            try:
                twilio_sms.place_call(m.number, f"{settings.public_base_url}/voice/dose/{d.id}")
                store.count("call")
                calls += 1
                continue
            except Exception:  # noqa: BLE001 - fall back to an SMS reminder
                log.exception("call to %s failed", countries.mask(m.number))
        _send(m.number, f"{answer.message('meds_due', m.lang)} {m.what}. {answer.message('meds_press', m.lang)}")
    return calls


async def _reminder_loop() -> None:
    while True:
        try:
            await run_in_threadpool(deliver_due_reminders)
            await run_in_threadpool(run_doses)
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
    # The simulator cannot text other phones: outbox messages are shown, not sent.
    notes = [f"(SMS to {countries.mask(to)}: {text})" for to, text in r.outbox]
    return {"reply": r.text, "segments": r.segments, "encoding": r.encoding, "kind": r.kind, "lang": r.lang,
            "notes": notes}


def _call_text(d: store.Dose) -> tuple[str, str, str]:
    """What the voice says, the language it is spoken in, and the browser speech code."""
    m = store.med(d.med_id)
    script, say_lang, _ = answer.call_voice(m.lang)
    return " ".join(meds.call_parts(m.lang, m.spoken, script)), meds.voice_language(m.lang), meds.browser_lang(say_lang)


@app.get("/api/inbox")
def inbox(request: Request) -> dict:
    """Reminders that came due, and medicine calls ringing, for this simulator visitor."""
    sender = _web_sender(request)
    calls = []
    for d in store.web_rings(sender):
        text, spoken_in, voice = _call_text(d)
        calls.append({"dose": d.id, "text": text, "spoken_in": spoken_in, "voice": voice})
    return {"messages": [answer.due_text(r) for r in store.inbox(sender)], "calls": calls}


class Press(BaseModel):
    digit: str = Field(max_length=1)


@app.post("/api/dose/{dose_id}/press")
def press(dose_id: int, body: Press, request: Request) -> dict:
    """The simulator visitor pressed a key during a ringing medicine call."""
    d = store.dose(dose_id)
    m = store.med(d.med_id) if d else None
    if m is None or m.number != _web_sender(request):
        raise HTTPException(status_code=404)
    script, say_lang, _ = answer.call_voice(m.lang)
    voice = meds.browser_lang(say_lang)
    if body.digit == "1":
        answer.confirm_dose(dose_id)
        return {"reply": script["thanks"], "voice": voice}
    return {"reply": script["retry"], "voice": voice}


def _reply_later(to: str, text: str) -> None:
    r = answer.handle(text, sender=to)
    if r.text:
        _send(to, r.text)
    for other, body in r.outbox:
        _send(other, body)


def _xml(message: str | None) -> Response:
    return Response(twilio_sms.twiml(message or None), media_type="application/xml")


def _check_twilio(request: Request, params: dict[str, str]) -> None:
    """Only Twilio may call the webhooks: check X-Twilio-Signature when a token is set."""
    if not settings.twilio_auth_token:
        return
    url = (settings.public_base_url + request.url.path) if settings.public_base_url else str(request.url)
    if not twilio_sms.signature_ok(settings.twilio_auth_token, url, params,
                                   request.headers.get("X-Twilio-Signature", "")):
        raise HTTPException(status_code=403, detail="bad signature")


def _voice(xml: str) -> Response:
    return Response(xml, media_type="application/xml")


@app.post("/voice/dose/{dose_id}")
async def voice_dose(dose_id: int, request: Request) -> Response:
    """Twilio asks what to say when the person answers a medicine call."""
    _check_twilio(request, {k: str(v) for k, v in (await request.form()).items()})
    d = store.dose(dose_id)
    m = store.med(d.med_id) if d else None
    if m is None:
        return _voice(twilio_sms.voice_twiml([], "en-US", "Polly.Joanna"))
    script, say_lang, voice = answer.call_voice(m.lang)
    if d.state != "waiting":
        return _voice(twilio_sms.voice_twiml([script["thanks"]], say_lang, voice))
    action = f"{settings.public_base_url}/voice/answer/{dose_id}" if settings.public_base_url \
        else f"/voice/answer/{dose_id}"
    parts = meds.call_parts(m.lang, m.spoken, script)
    return _voice(twilio_sms.voice_twiml(parts, say_lang, voice, gather_action=action,
                                         after_gather=script["retry"]))


@app.post("/voice/answer/{dose_id}")
async def voice_answer(dose_id: int, request: Request) -> Response:
    """The key the person pressed during the call."""
    params = {k: str(v) for k, v in (await request.form()).items()}
    _check_twilio(request, params)
    d = store.dose(dose_id)
    m = store.med(d.med_id) if d else None
    if m is None:
        return _voice(twilio_sms.voice_twiml([], "en-US", "Polly.Joanna"))
    script, say_lang, voice = answer.call_voice(m.lang)
    if params.get("Digits") == "1":
        answer.confirm_dose(dose_id)
        return _voice(twilio_sms.voice_twiml([script["thanks"]], say_lang, voice))
    return _voice(twilio_sms.voice_twiml([script["retry"]], say_lang, voice))


@app.post("/sms")
async def sms_webhook(request: Request, background: BackgroundTasks) -> Response:
    form = await request.form()
    params = {k: str(v) for k, v in form.items()}

    _check_twilio(request, params)

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

    r = answer.handle(text, sender=sender)
    for other, body in r.outbox:
        _send(other, body)
    return _xml(r.text)
