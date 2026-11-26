"""Turn one incoming text message into one short reply."""

from __future__ import annotations

import logging
import time
import re
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo
from functools import lru_cache
from urllib.parse import unquote

from . import lang as L
from . import countries, meds, reminders, sms, sources, store
from .config import settings

log = logging.getLogger(__name__)

# English commands work everywhere; a few local words for the biggest languages.
HELP_WORDS = {"help", "?", "ຊ່ວຍ", "مساعدة", "مساعده", "ayuda", "aide", "ajuda", "msaada", "bantuan",
              "मदद", "সাহায্য", "помощь", "yardım", "hilfe", "tulong"}
WEATHER_WORDS = {"weather", "ອາກາດ", "طقس", "الطقس", "clima", "tiempo", "météo", "meteo", "tempo", "hewa",
                 "cuaca", "मौसम", "আবহাওয়া", "погода", "hava", "wetter", "panahon", "thời_tiết"}
RATE_WORDS = {"rate", "rates", "palitan", "ອັດຕາ", "سعر", "صرف", "cambio", "taux", "câmbio", "kurs", "kiwango",
              "विनिमय", "курс", "döviz"}
REMIND_WORDS = {"remind", "reminder", "paalala", "ipaalala", "ເຕືອນ", "ذكرني", "ذكّرني", "recuérdame", "recordar", "rappel", "rappelle",
                "lembrar", "lembre", "nikumbushe", "ingatkan", "याद", "напомни"}
# Carrier-standard opt-out / opt-in words (Twilio uses the same ones), plus local ones.
STOP_WORDS = {"stop", "stopall", "unsubscribe", "end", "quit", "cancel", "ຢຸດ", "توقف", "إيقاف", "الغاء", "إلغاء"}
START_WORDS = {"start", "unstop", "ເລີ່ມ", "ابدأ", "ابدا"}
MEDS_WORDS = {"meds", "medicine", "medicines", "pills", "gamot", "ຢາ", "دواء", "الدواء", "medicina", "medicamento",
              "médicament", "dawa", "obat", "दवा"}
TAKEN_WORDS = {"1", "taken", "done", "ok", "nainom", "ກິນແລ້ວ", "تم", "اخذته", "أخذته"}
YES_WORDS = {"yes", "y", "oo", "opo", "ໂດຍ", "ແມ່ນ", "نعم", "sí", "si", "oui", "sim", "ndiyo", "ya", "हाँ", "haan"}
PHONE = re.compile(r"^\+\d{8,15}$")
DEFAULT_RATE_TARGETS = ["LAK", "PHP", "THB", "EUR"]
CURRENCY = re.compile(r"^[A-Za-z]{3}$")

SYSTEM_PROMPT = """You answer questions sent by SMS from basic phones, often by people with no internet (often older people in rural Laos and elsewhere).
Rules:
- Answer ONLY from the sources given. If they do not answer the question, reply exactly: NOT_FOUND
- Reply in the same language as the question, even if the sources are in another language.
- Plain text, no markdown, no emoji, no line breaks.
- Be short: at most {limit} characters. Lead with the direct answer.
- For health, medicine or safety questions, add "see a health worker" (in the reply language).
- End with the number of the source you used in brackets, e.g. [2]. Ignore sources about a different meaning of the words."""

QUERY_PROMPT = """Turn this SMS question into a short English Wikipedia search query (2-6 words).
Reply with the query only, nothing else."""


@dataclass
class Reply:
    text: str
    lang: str
    kind: str  # help | weather | rate | answer | not_found | error | remind | meds | family | stop | start | silent
    outbox: list[tuple[str, str]] = field(default_factory=list)  # extra SMS to send: (to, text)

    @property
    def segments(self) -> int:
        return sms.segments(self.text)

    @property
    def encoding(self) -> str:
        return sms.encoding(self.text)


def _char_budget(language: str) -> int:
    per = 153 if language in L.GSM_LANGS else 67  # accents and non-Latin scripts force UCS-2
    return per * settings.max_segments - 40  # room for the source link


def _short_url(url: str) -> str:
    url = unquote(url)  # show Arabic/Lao titles as text, not %D8%AD...
    return re.sub(r"^https?://", "", url).replace(".m.wikipedia.org", ".wikipedia.org")


def _relevant(question: str, found: list[sources.Source]) -> list[sources.Source]:
    """Without AI nobody checks the page fits, so keep only pages that share a real word with the question."""
    words = {w for w in re.findall(r"\w{4,}", question.lower()) if not w.isdigit()}
    return [s for s in found if words & set(re.findall(r"\w{4,}", f"{s.title} {s.text}".lower()))]


def _extractive(found: list[sources.Source], language: str) -> str:
    """No-AI fallback: first sentences of the best source."""
    text = found[0].text
    budget = _char_budget(language)
    out = ""
    for s in re.split(r"(?<=[.!?。])\s+", text):
        if len(out) + len(s) + 1 > budget:
            break
        out = f"{out} {s}".strip()
    return out or text[:budget]


class BudgetSpent(RuntimeError):
    """Today's AI budget for everyone is used up; callers fall back to no-AI answers."""


def _claude(system: str, user: str, max_tokens: int = 2000) -> str | None:
    """One Claude call. Returns the text, or None on refusal."""
    import anthropic

    if store.used_today("ai") >= settings.max_ai_calls_per_day:
        raise BudgetSpent("daily AI budget reached")
    store.count("ai")

    client = anthropic.Anthropic(timeout=30.0, max_retries=1)
    response = client.beta.messages.create(
        model=settings.model,
        max_tokens=max_tokens,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "low"},
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    if response.stop_reason == "refusal":
        return None
    return " ".join(b.text for b in response.content if b.type == "text").strip()


@lru_cache(maxsize=512)
def _translated(key: str, language: str) -> str:
    """A fixed message in a language we did not hand-write, translated once and cached."""
    english = L.msg(key, "en")
    if language in L.MESSAGES or not settings.use_llm:
        return L.msg(key, language)
    try:
        text = _claude(
            f"Translate this SMS into the language with code '{language}'. Keep 'GHOST SIGNAL' and the "
            "English command words (HELP, WEATHER, RATE) as they are. Reply with the translation only.",
            english,
            max_tokens=1000,
        )
    except Exception:  # noqa: BLE001
        log.exception("message translation failed")
        text = None
    return re.sub(r"\s+", " ", text).strip() if text else english


def message(key: str, language: str) -> str:
    """Fixed reply in the sender's language (hand-written, else AI-translated, else English)."""
    if language in L.MESSAGES or not settings.use_llm:
        return L.msg(key, language)
    return _translated(key, language)


def _llm_answer(question: str, found: list[sources.Source], language: str) -> tuple[str, int] | None:
    """Claude writes the answer: (text, index of the source used), or None if not found."""
    docs = "\n\n".join(
        f'<source n="{i + 1}" title="{s.title}">\n{s.text}\n</source>' for i, s in enumerate(found)
    )
    text = _claude(SYSTEM_PROMPT.format(limit=_char_budget(language)), f"{docs}\n\nQuestion: {question}")
    if not text or "NOT_FOUND" in text:
        return None
    used = 0
    m = re.search(r"\[(\d+)\]\s*$", text)
    if m:
        used = min(max(int(m.group(1)) - 1, 0), len(found) - 1)
        text = text[: m.start()]
    return re.sub(r"\s+", " ", text).strip(), used


def _english_sources(question: str, language: str) -> list[sources.Source]:
    """English Wikipedia, with the question turned into English keywords if AI is on."""
    if language != "en" and settings.use_llm:
        try:
            query = _claude(QUERY_PROMPT, question, max_tokens=1000)
            if query:
                found = sources.wikipedia(query.strip().strip('"'), "en")
                if found:
                    return found
        except Exception:  # noqa: BLE001
            log.exception("query translation failed")
    return sources.wikipedia(question, "en")


def _search(question: str, language: str) -> list[sources.Source]:
    """Local-language Wikipedia first, then English."""
    found = sources.wikipedia(question, language) if language != "en" else []
    return found or _english_sources(question, language)


def _rate(args: list[str], language: str, country: countries.Country | None) -> Reply:
    codes = [a.upper() for a in args if CURRENCY.match(a)]
    local = country.currency if country else L.LOCAL_CURRENCY.get(language)
    if not codes:  # "RATE" alone: the dollar in the local currency (or a world list)
        base = "USD" if local != "USD" else "EUR"
        targets = [local] + [c for c in DEFAULT_RATE_TARGETS if c != local] if local else DEFAULT_RATE_TARGETS
    elif len(codes) == 1:
        base = codes[0]
        targets = [local] if local and local != base else ["USD", "EUR", "LAK", "PHP"]
    else:
        base, targets = codes[0], codes[1:]
    text = sources.exchange_rate(base, targets)
    if text is None:
        return Reply(message("not_found", language), language, "not_found")
    return Reply(sms.fit(text, settings.max_segments), language, "rate")


def _remind(args: list[str], sender: str, language: str, country: countries.Country | None) -> Reply:
    sub = args[0].lower() if args else ""
    if sub in {"list", ""}:
        items = store.waiting(sender)
        if not items:
            return Reply(message("reminder_none", language), language, "remind")
        lines = " ".join(f"{i}) {x.label} {x.what}" for i, x in enumerate(items, 1))
        return Reply(sms.fit(f"{message('reminder_list', language)} {lines}", settings.max_segments), language, "remind")
    if sub in {"del", "delete", "cancel", "x"} and len(args) > 1 and args[1].isdigit():
        gone = store.cancel_reminder(sender, int(args[1]))
        if gone is None:
            return Reply(message("reminder_none", language), language, "remind")
        return Reply(f"{message('reminder_deleted', language)} {gone.what}", language, "remind")
    if len(store.waiting(sender)) >= settings.max_reminders:
        return Reply(message("reminder_full", language), language, "remind")

    now = datetime.now(ZoneInfo(countries.timezone(country)))
    text = " ".join(args)
    parsed = reminders.parse(text, now)
    if parsed is None and settings.use_llm:
        try:
            prompt = reminders.AI_PROMPT.format(now=now.strftime("%Y-%m-%dT%H:%M"), weekday=now.strftime("%A"))
            parsed = reminders.parse_ai_reply(_claude(prompt, text, max_tokens=1000), now)
        except Exception:  # noqa: BLE001
            log.exception("reminder AI parse failed")
    if parsed is None or not reminders.in_range(parsed[0], now):
        return Reply(message("reminder_bad", language), language, "remind")
    due, what = parsed
    what = what[:120]
    shown = reminders.label(due, language)
    store.add_reminder(sender, due.timestamp(), what, language, shown)
    tz = "" if country else " UTC"
    return Reply(sms.fit(f"{message('reminder_set', language)} {shown}{tz}: {what}", settings.max_segments),
                 language, "remind")


def call_voice(language: str) -> tuple[dict[str, str], str, str]:
    """(call script, Twilio <Say> language, voice) for a person's language."""
    spoken = meds.voice_language(language)
    say_lang, voice = meds.VOICES.get(language, meds.VOICES["en"])
    if spoken in meds.SCRIPT:
        return meds.SCRIPT[spoken], say_lang, voice
    if settings.use_llm and language in meds.VOICES:
        script = {k: _translated_line(v, spoken) for k, v in meds.SCRIPT["en"].items()}
        if all(script.values()):
            return script, say_lang, voice
    return meds.SCRIPT["en"], *meds.VOICES["en"]


@lru_cache(maxsize=256)
def _translated_line(text: str, language: str) -> str:
    try:
        out = _claude(f"Translate this phone-call sentence into the language with code '{language}'. "
                      "Keep 'Ghost Signal' as it is. Reply with the translation only.", text, max_tokens=500)
    except Exception:  # noqa: BLE001
        log.exception("call script translation failed")
        return ""
    return re.sub(r"\s+", " ", out).strip() if out else ""


def _spoken_what(what: str, language: str) -> str:
    """The medicine name as the call voice can say it (Lao is spoken by a Thai voice)."""
    target = meds.voice_language(language)
    if target == language:
        return what
    if not settings.use_llm:
        return ""  # the voice cannot read this script; the call still says it is medicine time
    try:
        out = _claude(f"Write this medicine name in the language with code '{target}' so a "
                      f"text-to-speech voice can read it. Reply with the words only.", what, max_tokens=300)
    except Exception:  # noqa: BLE001
        log.exception("medicine name translation failed")
        return ""
    return (out or "").strip()[:80]


def _meds(args: list[str], sender: str, language: str, country: countries.Country | None) -> Reply:
    sub = args[0].lower() if args else ""
    if sub in {"list", ""}:
        items = store.meds_of(sender)
        if not items:
            return Reply(message("meds_none", language), language, "meds")
        lines = " ".join(f"{i}) {m.times.replace(',', ' ')} {m.what}" for i, m in enumerate(items, 1))
        return Reply(sms.fit(f"{message('meds_list', language)} {lines}", settings.max_segments), language, "meds")
    if sub in {"del", "delete", "stop", "x"} and len(args) > 1 and args[1].isdigit():
        items = store.meds_of(sender)
        n = int(args[1])
        if not 1 <= n <= len(items):
            return Reply(message("meds_none", language), language, "meds")
        store.stop_med(items[n - 1].id)
        return Reply(f"{message('meds_deleted', language)} {items[n - 1].what}", language, "meds")
    if sub in {"family", "fam", "عائلة", "ຄອບຄົວ"}:
        contact = args[1] if len(args) > 1 else ""
        if not PHONE.match(contact) or contact == sender:
            return Reply(message("family_bad", language), language, "family")
        store.invite_family(sender, contact)
        c_country = countries.from_number(contact)
        c_lang = c_country.lang if c_country else language
        invite = f"{message('family_invite', c_lang)} {sender}"
        return Reply(message("family_set", language), language, "family", outbox=[(contact, invite)])
    if len(store.meds_of(sender)) >= meds.MAX_MEDS:
        return Reply(message("meds_full", language), language, "meds")

    text = " ".join(args)
    tz = countries.timezone(country)
    parsed = meds.parse(text)
    soon = reminders._IN.search(text)
    if parsed is None and soon:  # "MEDS in 1 min pill": first call soon, then daily at that time
        due, what = reminders.parse(text, datetime.now(ZoneInfo(tz))) or (None, "")
        if due is not None and what:
            parsed = ([due.strftime("%H:%M")], what[:80])
    if parsed is None and settings.use_llm:
        try:
            parsed = meds.parse_ai_reply(_claude(meds.AI_PROMPT, text, max_tokens=500))
        except Exception:  # noqa: BLE001
            log.exception("meds AI parse failed")
    if parsed is None:
        return Reply(message("meds_bad", language), language, "meds")
    times, what = parsed
    med_id = store.add_med(sender, ",".join(times), what, _spoken_what(what, language), language, tz)
    store.add_dose(med_id, meds.next_due(",".join(times), tz, time.time()))
    key = "meds_set" if meds.can_call(language) else "meds_sms"
    zone = "" if country else " UTC"
    return Reply(sms.fit(f"{message(key, language)} {' '.join(times)}{zone}: {what}", settings.max_segments),
                 language, "meds")


def confirm_dose(dose_id: int) -> None:
    """The person pressed or texted 1: this dose is taken; plan the next one."""
    d = store.dose(dose_id)
    if d is None or d.state != "waiting":
        return
    finish_dose(d, "confirmed")


def finish_dose(d: store.Dose, state: str) -> None:
    store.set_dose_state(d.id, state)
    m = store.med(d.med_id)
    if m is not None:
        store.add_dose(m.id, meds.next_due(m.times, m.tz, max(d.due, time.time())))


def due_text(r: store.Reminder) -> str:
    """The SMS sent when a reminder is due."""
    return sms.fit(f"{message('reminder_due', r.lang)} {r.what}", settings.max_segments)


def handle(text: str, sender: str | None = None, country: countries.Country | None = None) -> Reply:
    """Answer one SMS. `sender` is the phone number (+20...); it tells us the country."""
    text = (text or "").strip()
    sender = sender or "anonymous"
    country = country or countries.from_number(sender)
    language = L.detect(text, country.lang if country else None)
    words = text.split()
    first = words[0].lower().strip(".!") if words else ""

    # STOP always wins, and nothing is sent to an opted-out number except the START answer.
    if first in STOP_WORDS and len(words) == 1:
        store.opt_out(sender)
        return Reply(message("stopped", language), language, "stop")
    if first in START_WORDS and len(words) == 1:
        store.opt_in(sender)
        return Reply(message("started", language), language, "start")
    if store.opted_out(sender):
        return Reply("", language, "silent")

    # A family contact accepting, or a person confirming a medicine dose by SMS.
    if first in YES_WORDS and len(words) == 1 and store.pending_invites(sender):
        store.accept_family(sender)
        return Reply(message("family_ok", language), language, "family")
    if first in TAKEN_WORDS and len(words) <= 2:
        ringing = store.ringing_dose(sender)
        if ringing is not None:
            confirm_dose(ringing.id)
            return Reply(message("meds_taken", language), language, "meds")

    if not text or first in HELP_WORDS:
        return Reply(message("help", language), language, "help")

    try:
        if first in MEDS_WORDS:
            return _meds(words[1:], sender, language, country)

        if first in REMIND_WORDS:
            return _remind(words[1:], sender, language, country)

        if first in RATE_WORDS:
            return _rate(words[1:], language, country)

        if first in WEATHER_WORDS:
            if len(words) < 2:
                return Reply(message("no_city", language), language, "help")
            city = " ".join(words[1:])
            forecast = sources.weather(city)
            if forecast is None and language != "en" and settings.use_llm:
                try:  # unknown local spelling: ask for the English name once
                    english = _claude("Reply with the English name of this city only.", city, max_tokens=1000)
                    forecast = sources.weather(english) if english else None
                except Exception:  # noqa: BLE001
                    log.exception("city translation failed")
            if forecast is None:
                return Reply(message("not_found", language), language, "not_found")
            return Reply(sms.fit(forecast, settings.max_segments), language, "weather")

        store.count("question")
        found = _search(text, language)
        if not settings.use_llm:
            found = _relevant(text, found)
            if not found and language != "en":
                found = _relevant(text, sources.wikipedia(text, "en"))
        if not found:
            return Reply(message("not_found", language), language, "not_found")

        used = 0
        if settings.use_llm:
            try:
                result = _llm_answer(text, found, language)
                if result is None and language != "en" and "wikipedia.org" in found[0].url                         and not found[0].url.split("//")[-1].startswith("en."):
                    # Small local Wikipedias often miss the topic: try the English one.
                    found = _english_sources(text, language)
                    result = _llm_answer(text, found, language) if found else None
                if result is None:
                    return Reply(message("not_found", language), language, "not_found")
                body, used = result
            except Exception:  # noqa: BLE001 - any AI failure falls back to plain extract
                log.exception("LLM answer failed; using extract")
                body = _extractive(found, language)
        else:
            body = _extractive(found, language)

        source = f" Src: {_short_url(found[used].url)}"
        reply = sms.fit(body, settings.max_segments)
        if sms.segments(reply + source) <= settings.max_segments:
            reply += source
        return Reply(reply, language, "answer")
    except Exception:  # noqa: BLE001 - the phone must always get something back
        log.exception("handle failed")
        return Reply(message("error", language), language, "error")
