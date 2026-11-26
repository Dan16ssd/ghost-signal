"""Medicine reminders by phone call: 'MEDS 8am 8pm blood pressure pill'.

Every day at those local times Ghost Signal calls the person's own phone, says what to take in
their language and asks them to press 1. No 1 -> one more call 10 minutes later -> if still
nothing, an SMS to the family contact they chose (who must have replied YES first).

Voices: Twilio <Say> voices per language. There is no Lao voice, so Lao speakers hear Thai
(Lao and Thai are close; most Lao understand spoken Thai): the call script is written in Thai.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .reminders import _TIME

MAX_TIMES = 4
MAX_MEDS = 3
RETRY_MINUTES = 10
MAX_ATTEMPTS = 2  # calls per dose before the family is told

# language -> (Twilio <Say> language, voice). Check names in the Twilio console (Voice > TwiML > Text-to-speech).
VOICES: dict[str, tuple[str, str]] = {
    "en": ("en-US", "Polly.Joanna"),
    "ar": ("arb", "Polly.Zeina"),
    "th": ("th-TH", "Google.th-TH-Standard-A"),
    "lo": ("th-TH", "Google.th-TH-Standard-A"),  # no Lao voice: Lao speakers hear Thai
    "es": ("es-MX", "Polly.Mia"),
    "fr": ("fr-FR", "Polly.Celine"),
    "pt": ("pt-BR", "Polly.Camila"),
    "hi": ("hi-IN", "Polly.Aditi"),
    "ru": ("ru-RU", "Polly.Tatyana"),
    "tr": ("tr-TR", "Polly.Filiz"),
    "zh": ("cmn-CN", "Polly.Zhiyu"),
    "ja": ("ja-JP", "Polly.Mizuki"),
    "ko": ("ko-KR", "Polly.Seoyeon"),
    "id": ("id-ID", "Google.id-ID-Standard-A"),
    "vi": ("vi-VN", "Google.vi-VN-Standard-A"),
    "bn": ("bn-IN", "Google.bn-IN-Standard-A"),
}

# Which script the call voice reads, when it differs from the person's language.
SPOKEN_AS = {"lo": "th"}

# Hand-written call scripts. Other voiced languages get an AI translation of the English one.
SCRIPT = {
    "en": {
        "intro": "Hello, this is Ghost Signal. It is time for your medicine.",
        "press": "Press 1 when you have taken it.",
        "thanks": "Thank you. Stay well.",
        "retry": "We will call you again in ten minutes.",
    },
    "ar": {
        "intro": "مرحباً، معك Ghost Signal. حان وقت الدواء.",
        "press": "اضغط واحد بعد أن تأخذ الدواء.",
        "thanks": "شكراً لك. نتمنى لك الصحة.",
        "retry": "سنتصل بك مرة أخرى بعد عشر دقائق.",
    },
    "th": {  # also what Lao speakers hear
        "intro": "สวัสดีค่ะ นี่คือโกสต์ซิกแนล ถึงเวลากินยาแล้วค่ะ",
        "press": "กินยาแล้ว กดหนึ่งค่ะ",
        "thanks": "ขอบคุณค่ะ ดูแลสุขภาพนะคะ",
        "retry": "จะโทรมาอีกครั้งในสิบนาทีค่ะ",
    },
}


def can_call(language: str) -> bool:
    return language in VOICES


def voice_language(language: str) -> str:
    """The language the call is spoken in (Lao -> Thai)."""
    return SPOKEN_AS.get(language, language)


def parse(text: str) -> tuple[list[str], str] | None:
    """'8am 8pm blood pressure pill' -> (['08:00', '20:00'], 'blood pressure pill'); None without times."""
    times: list[str] = []
    for m in _TIME.finditer(text):
        if m.group(1):
            hour, minute, ampm = int(m.group(1)), int(m.group(2) or 0), m.group(3).lower()
            if not 1 <= hour <= 12:
                return None
            hour = hour % 12 + (12 if ampm == "pm" else 0)
        else:
            hour, minute = int(m.group(4)), int(m.group(5))
        if hour > 23 or minute > 59:
            return None
        times.append(f"{hour:02d}:{minute:02d}")
    what = _TIME.sub(" ", text)
    what = re.sub(r"\b(and|every ?day|daily|at)\b|[,&+]", " ", what, flags=re.I)
    what = re.sub(r"\s+", " ", what).strip(" .:-")
    times = sorted(set(times))
    if not times or len(times) > MAX_TIMES or not what:
        return None
    return times, what[:80]


AI_PROMPT = """Read this SMS that sets daily medicine reminders. Reply with JSON only:
{"times": ["HH:MM", ...], "what": "<medicine, in the SMS's language>"} using 24-hour local times
(at most 4). If there is no clear time, reply exactly: NONE"""


def parse_ai_reply(reply: str | None) -> tuple[list[str], str] | None:
    if not reply or "NONE" in reply:
        return None
    m = re.search(r"\{.*\}", reply, re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        times = sorted({datetime.strptime(t, "%H:%M").strftime("%H:%M") for t in data["times"]})
        what = str(data["what"]).strip()[:80]
    except (ValueError, KeyError, TypeError):
        return None
    if not times or len(times) > MAX_TIMES or not what:
        return None
    return times, what


def next_due(times: str, tz: str, after: float) -> float:
    """Next of the daily local `times` ('08:00,20:00') strictly after the Unix time `after`."""
    zone = ZoneInfo(tz)
    start = datetime.fromtimestamp(after, zone)
    for day in range(0, 3):
        date = (start + timedelta(days=day)).date()
        for t in times.split(","):
            h, m = map(int, t.split(":"))
            candidate = datetime(date.year, date.month, date.day, h, m, tzinfo=zone).timestamp()
            if candidate > after:
                return candidate
    raise ValueError("no time found")  # unreachable for valid times


def call_parts(language: str, spoken_what: str, script: dict[str, str]) -> list[str]:
    """What the voice says when the phone is answered."""
    parts = [script["intro"]]
    if spoken_what:
        parts.append(spoken_what)
    parts.append(script["press"])
    return parts
