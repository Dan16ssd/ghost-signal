"""Turn one incoming text message into one short reply."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import unquote

from . import lang as L
from . import sms, sources
from .config import settings

log = logging.getLogger(__name__)

HELP_WORDS = {"help", "?", "ຊ່ວຍ", "مساعدة", "مساعده"}
WEATHER_WORDS = {"weather", "ອາກາດ", "طقس", "الطقس"}
RATE_WORDS = {"rate", "rates", "ອັດຕາ", "سعر", "صرف"}
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
    per = 153 if language == "en" else 67  # non-Latin scripts force UCS-2
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


def _search(question: str, language: str) -> list[sources.Source]:
    """Local-language Wikipedia first, then English (translating the question if AI is on)."""
    found: list[sources.Source] = []
    if language != "en":
        found = sources.wikipedia(question, language)
        if not found and settings.use_llm:
            try:
                query = _claude(QUERY_PROMPT, question, max_tokens=1000)
                if query:
                    found = sources.wikipedia(query.strip().strip('"'), "en")
            except Exception:  # noqa: BLE001
                log.exception("query translation failed")
    if not found:
        found = sources.wikipedia(question, "en")
    return found


def _rate(args: list[str], language: str) -> Reply:
    codes = [a.upper() for a in args if CURRENCY.match(a)]
    if not codes:  # "RATE" alone: dollar against both teams' currencies and more
        base, targets = "USD", DEFAULT_RATE_TARGETS
    elif len(codes) == 1:
        local = L.LOCAL_CURRENCY.get(language)
        base = codes[0]
        targets = [local] if local and local != base else ["USD", "EUR", "EGP", "LAK"]
    else:
        base, targets = codes[0], codes[1:]
    text = sources.exchange_rate(base, targets)
    if text is None:
        return Reply(L.msg("not_found", language), language, "not_found")
    return Reply(sms.fit(text, settings.max_segments), language, "rate")


def handle(text: str) -> Reply:
    text = (text or "").strip()
    language = L.detect(text)
    words = text.split()
    first = words[0].lower() if words else ""

    if not text or first in HELP_WORDS:
        return Reply(L.msg("help", language), language, "help")

    try:
        if first in RATE_WORDS:
            return _rate(words[1:], language)

        if first in WEATHER_WORDS:
            if len(words) < 2:
                return Reply(L.msg("no_city", language), language, "help")
            city = " ".join(words[1:])
            forecast = sources.weather(city)
            if forecast is None and language != "en" and settings.use_llm:
                try:  # unknown local spelling: ask for the English name once
                    english = _claude("Reply with the English name of this city only.", city, max_tokens=1000)
                    forecast = sources.weather(english) if english else None
                except Exception:  # noqa: BLE001
                    log.exception("city translation failed")
            if forecast is None:
                return Reply(L.msg("not_found", language), language, "not_found")
            return Reply(sms.fit(forecast, settings.max_segments), language, "weather")

        found = _search(text, language)
        if not found:
            return Reply(L.msg("not_found", language), language, "not_found")

        used = 0
        if settings.use_llm:
            try:
                result = _llm_answer(text, found, language)
                if result is None:
                    return Reply(L.msg("not_found", language), language, "not_found")
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
        return Reply(L.msg("error", language), language, "error")
