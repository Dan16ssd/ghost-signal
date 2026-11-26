"""Turn one incoming text message into one short reply."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import unquote

from . import lang as L
from . import countries, sms, sources
from .config import settings

log = logging.getLogger(__name__)

# English commands work everywhere; a few local words for the biggest languages.
HELP_WORDS = {"help", "?", "ຊ່ວຍ", "مساعدة", "مساعده", "ayuda", "aide", "ajuda", "msaada", "bantuan",
              "मदद", "সাহায্য", "помощь", "yardım", "hilfe", "tulong"}
WEATHER_WORDS = {"weather", "ອາກາດ", "طقس", "الطقس", "clima", "tiempo", "météo", "meteo", "tempo", "hewa",
                 "cuaca", "मौसम", "আবহাওয়া", "погода", "hava", "wetter", "panahon", "thời_tiết"}
RATE_WORDS = {"rate", "rates", "ອັດຕາ", "سعر", "صرف", "cambio", "taux", "câmbio", "kurs", "kiwango",
              "विनिमय", "курс", "döviz"}
DEFAULT_RATE_TARGETS = ["EGP", "LAK", "THB", "EUR"]
CURRENCY = re.compile(r"^[A-Za-z]{3}$")

SYSTEM_PROMPT = """You answer questions sent by SMS from basic phones, often by people with no internet (for example in rural Laos or Egypt).
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
    kind: str  # help | weather | rate | answer | not_found | error

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


def _claude(system: str, user: str, max_tokens: int = 2000) -> str | None:
    """One Claude call. Returns the text, or None on refusal."""
    import anthropic

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
        targets = [local] if local and local != base else ["USD", "EUR", "EGP", "LAK"]
    else:
        base, targets = codes[0], codes[1:]
    text = sources.exchange_rate(base, targets)
    if text is None:
        return Reply(message("not_found", language), language, "not_found")
    return Reply(sms.fit(text, settings.max_segments), language, "rate")


def handle(text: str, sender: str | None = None, country: countries.Country | None = None) -> Reply:
    """Answer one SMS. `sender` is the phone number (+20...); it tells us the country."""
    text = (text or "").strip()
    country = country or countries.from_number(sender)
    language = L.detect(text, country.lang if country else None)
    words = text.split()
    first = words[0].lower() if words else ""

    if not text or first in HELP_WORDS:
        return Reply(message("help", language), language, "help")

    try:
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

        found = _search(text, language)
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
