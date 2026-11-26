"""Turn one incoming text message into one short reply."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from . import lang as L
from . import sms, sources
from .config import settings

log = logging.getLogger(__name__)

WEATHER_WORDS = ("weather", "ອາກາດ")
HELP_WORDS = ("help", "?", "ຊ່ວຍ")

SYSTEM_PROMPT = """You answer questions sent by SMS from basic phones, often by people in rural Laos with no internet.
Rules:
- Answer ONLY from the sources given. If they do not answer the question, reply exactly: NOT_FOUND
- Reply in the same language as the question (Lao or English).
- Plain text, no markdown, no emoji, no line breaks.
- Be short: at most {limit} characters. Lead with the direct answer.
- For health, medicine or safety questions, add "see a health worker" (in the reply language).
- End with the number of the source you used in brackets, e.g. [2]. Ignore sources about a different meaning of the words."""


@dataclass
class Reply:
    text: str
    lang: str
    kind: str  # help | weather | answer | not_found | error

    @property
    def segments(self) -> int:
        return sms.segments(self.text)

    @property
    def encoding(self) -> str:
        return sms.encoding(self.text)


def _char_budget(language: str) -> int:
    per = 67 if language == "lo" else 153
    return per * settings.max_segments - 40  # room for the source link


def _short_url(url: str) -> str:
    return re.sub(r"^https?://", "", url).replace(".m.wikipedia.org", ".wikipedia.org")


def _extractive(question: str, found: list[sources.Source], language: str) -> str:
    """No-AI fallback: first sentences of the best source."""
    text = found[0].text
    budget = _char_budget(language)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out = ""
    for s in sentences:
        if len(out) + len(s) + 1 > budget:
            break
        out = f"{out} {s}".strip()
    return out or text[:budget]


def _llm(question: str, found: list[sources.Source], language: str) -> tuple[str, int] | None:
    """Write the answer with Claude: (text, index of source used), or None if not found."""
    import anthropic

    docs = "\n\n".join(
        f'<source n="{i + 1}" title="{s.title}">\n{s.text}\n</source>' for i, s in enumerate(found)
    )
    client = anthropic.Anthropic(timeout=30.0, max_retries=1)
    response = client.beta.messages.create(
        model=settings.model,
        max_tokens=2000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "low"},
        system=SYSTEM_PROMPT.format(limit=_char_budget(language)),
        messages=[{"role": "user", "content": f"{docs}\n\nQuestion: {question}"}],
    )
    if response.stop_reason == "refusal":
        return None
    text = " ".join(b.text for b in response.content if b.type == "text").strip()
    if not text or "NOT_FOUND" in text:
        return None
    used = 0
    m = re.search(r"\[(\d+)\]\s*$", text)
    if m:
        used = min(max(int(m.group(1)) - 1, 0), len(found) - 1)
        text = text[: m.start()]
    return re.sub(r"\s+", " ", text).strip(), used


def _search(question: str, language: str) -> list[sources.Source]:
    found: list[sources.Source] = []
    if language == "lo":
        found = sources.wikipedia(question, "lo")
    if not found:
        found = sources.wikipedia(question, "en")
    return found


def handle(text: str) -> Reply:
    text = (text or "").strip()
    language = L.detect(text)
    words = text.split(maxsplit=1)
    first = words[0].lower() if words else ""

    if not text or first in HELP_WORDS:
        return Reply(L.msg("help", language), language, "help")

    try:
        if first in WEATHER_WORDS:
            if len(words) < 2:
                return Reply(L.msg("no_city", language), language, "help")
            forecast = sources.weather(words[1])
            if forecast is None:
                return Reply(L.msg("not_found", language), language, "not_found")
            return Reply(sms.fit(forecast, settings.max_segments), language, "weather")

        found = _search(text, language)
        if not found:
            return Reply(L.msg("not_found", language), language, "not_found")

        used = 0
        if settings.use_llm:
            try:
                result = _llm(text, found, language)
                if result is None:
                    return Reply(L.msg("not_found", language), language, "not_found")
                body, used = result
            except Exception:  # noqa: BLE001 - any AI failure falls back to plain extract
                log.exception("LLM answer failed; using extract")
                body = _extractive(text, found, language)
        else:
            body = _extractive(text, found, language)

        source = f" Src: {_short_url(found[used].url)}"
        reply = sms.fit(body, settings.max_segments)
        if sms.segments(reply + source) <= settings.max_segments:
            reply += source
        return Reply(reply, language, "answer")
    except Exception:  # noqa: BLE001 - the phone must always get something back
        log.exception("handle failed")
        return Reply(L.msg("error", language), language, "error")
