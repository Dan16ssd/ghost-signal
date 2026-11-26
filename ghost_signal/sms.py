"""SMS length rules.

One SMS holds 160 characters when every character is in the GSM-7 alphabet,
or 70 when any character is not (Lao script, emoji...), which forces UCS-2.
Longer messages are split into parts of 153 (GSM-7) or 67 (UCS-2).
"""

from __future__ import annotations

import math

GSM7_BASIC = (
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)
GSM7_EXTENDED = "^{}\\[~]|€\f"  # each costs 2 characters (escape + char)

_BASIC = set(GSM7_BASIC)
_EXT = set(GSM7_EXTENDED)


def is_gsm7(text: str) -> bool:
    return all(c in _BASIC or c in _EXT for c in text)


def encoding(text: str) -> str:
    return "GSM-7" if is_gsm7(text) else "UCS-2"


def units(text: str) -> int:
    """Length in the units the carrier counts."""
    if is_gsm7(text):
        return sum(2 if c in _EXT else 1 for c in text)
    # UTF-16 code units; counted by hand so broken (lone surrogate) input can't crash us.
    return sum(2 if ord(c) > 0xFFFF else 1 for c in text)


def segments(text: str) -> int:
    """Number of SMS parts needed to send `text` (0 for empty text)."""
    n = units(text)
    if n == 0:
        return 0
    single, multi = (160, 153) if is_gsm7(text) else (70, 67)
    return 1 if n <= single else math.ceil(n / multi)


def fit(text: str, max_segments: int) -> str:
    """Shorten `text` so it fits in `max_segments` SMS parts.

    Cuts at a word boundary when possible and marks the cut with "...".
    """
    if max_segments < 1:
        raise ValueError("max_segments must be >= 1")
    text = text.strip()
    if segments(text) <= max_segments:
        return text
    mark = "..."
    lo, hi = 0, len(text)
    # Longest prefix that still fits with the mark (binary search).
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if segments(text[:mid].rstrip() + mark) <= max_segments:
            lo = mid
        else:
            hi = mid - 1
    cut = text[:lo]
    space = cut.rfind(" ")
    if space > len(cut) * 0.6:  # don't throw away too much for a clean cut
        cut = cut[:space]
    return cut.rstrip() + mark
