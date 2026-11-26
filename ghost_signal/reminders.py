"""Understand 'REMIND <when> <what>' in the sender's local time.

English times are parsed by rules (fast, free, tested):
    REMIND 8pm take medicine          REMIND tomorrow 7:30am vaccine
    REMIND in 2 hours call mum        REMIND take pills at 21:00
Other languages ("ذكرني غدا الساعة 8 مساء بالدواء") go to the AI with the local time.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

MAX_AHEAD = timedelta(days=30)
MIN_AHEAD = timedelta(seconds=30)

_IN = re.compile(
    r"\bin\s+(\d{1,3})\s*(m|mins?|minutes?|h|hrs?|hours?|d|days?)\b", re.I
)
_TIME = re.compile(r"(?:\bat\s+)?\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b|(?:\bat\s+)?\b(\d{1,2}):(\d{2})\b", re.I)
_DAY = re.compile(r"\b(today|tonight|tomorrow|tmrw)\b", re.I)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"^\s*(to|that)\s+", "", text.strip(" ,.:-"), flags=re.I)).strip()


def parse(text: str, now: datetime) -> tuple[datetime, str] | None:
    """(due time, what) from English text, in `now`'s time zone; None if no time is found."""
    m = _IN.search(text)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
        step = timedelta(minutes=n) if unit.startswith("m") else timedelta(hours=n) if unit.startswith("h") else timedelta(days=n)
        what = _clean(text[: m.start()] + " " + text[m.end():])
        # Real elapsed time, also across a daylight-saving change.
        due = (now.astimezone(timezone.utc) + step).astimezone(now.tzinfo)
        return (due, what) if what else None

    t = _TIME.search(text)
    if not t:
        return None
    if t.group(1):
        hour, minute, ampm = int(t.group(1)), int(t.group(2) or 0), t.group(3).lower()
        if not 1 <= hour <= 12:
            return None
        hour = hour % 12 + (12 if ampm == "pm" else 0)
    else:
        hour, minute = int(t.group(4)), int(t.group(5))
    if hour > 23 or minute > 59:
        return None

    rest = text[: t.start()] + " " + text[t.end():]
    d = _DAY.search(rest)
    day_word = d.group(1).lower() if d else ""
    if d:
        rest = rest[: d.start()] + " " + rest[d.end():]
    what = _clean(rest)
    if not what:
        return None

    due = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if day_word in {"tomorrow", "tmrw"}:
        due += timedelta(days=1)
    elif due.timestamp() <= now.timestamp():  # "8pm" said at 9pm means tomorrow
        due += timedelta(days=1)
    if due.timestamp() <= now.timestamp():  # a clock time skipped by daylight saving
        due += timedelta(days=1)
    return due, what


AI_PROMPT = """The local date and time is {now} ({weekday}). Read this SMS asking for a reminder.
Reply with JSON only: {{"when": "YYYY-MM-DDTHH:MM", "what": "<what to remind, in the SMS's language>"}}
using local time. If there is no clear time, reply exactly: NONE"""


def parse_ai_reply(reply: str | None, now: datetime) -> tuple[datetime, str] | None:
    """Read the AI's JSON; None if it gave no usable time."""
    if not reply or "NONE" in reply:
        return None
    m = re.search(r"\{.*\}", reply, re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        due = datetime.fromisoformat(data["when"]).replace(tzinfo=now.tzinfo)
        what = _clean(str(data["what"]))
    except (ValueError, KeyError, TypeError):
        return None
    return (due, what) if what else None


def in_range(due: datetime, now: datetime) -> bool:
    return now + MIN_AHEAD <= due <= now + MAX_AHEAD


def label(due: datetime, language: str) -> str:
    """How the due time is shown back: 'Fri 28 Nov 20:00' in English, '2026-11-28 20:00' otherwise."""
    return due.strftime("%a %d %b %H:%M") if language == "en" else due.strftime("%Y-%m-%d %H:%M")
