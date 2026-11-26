"""Language detection by script, plus fixed replies in each supported language.

Detection is by alphabet, which is reliable for short SMS:
scripts such as Lao, Arabic, Devanagari or Cyrillic point to a language;
Latin text is matched by common words, then by the sender's country.
"""

from __future__ import annotations

import re

# Scripts that point to one language (checked by counting letters).
SCRIPTS = {
    "lo": [(0x0E80, 0x0EFF)],
    "th": [(0x0E00, 0x0E7F)],
    "ar": [(0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF), (0xFB50, 0xFDFF), (0xFE70, 0xFEFF)],
    "hi": [(0x0900, 0x097F)],
    "bn": [(0x0980, 0x09FF)],
    "pa": [(0x0A00, 0x0A7F)],
    "gu": [(0x0A80, 0x0AFF)],
    "ta": [(0x0B80, 0x0BFF)],
    "te": [(0x0C00, 0x0C7F)],
    "kn": [(0x0C80, 0x0CFF)],
    "ml": [(0x0D00, 0x0D7F)],
    "si": [(0x0D80, 0x0DFF)],
    "my": [(0x1000, 0x109F)],
    "ka": [(0x10A0, 0x10FF)],
    "am": [(0x1200, 0x139F)],
    "km": [(0x1780, 0x17FF)],
    "ru": [(0x0400, 0x04FF)],
    "el": [(0x0370, 0x03FF)],
    "he": [(0x0590, 0x05FF)],
    "hy": [(0x0530, 0x058F)],
    "ko": [(0xAC00, 0xD7AF), (0x1100, 0x11FF)],
    "ja": [(0x3040, 0x30FF)],
    "zh": [(0x4E00, 0x9FFF)],
}

# Same script, different language: the sender's country decides.
SCRIPT_SHARED_BY = {
    "ar": {"fa", "ur"},  # Arabic letters: Persian, Urdu
    "ru": {"uk", "kk", "ky", "tg", "bg", "sr", "mn"},  # Cyrillic
    "hi": {"ne", "mr"},  # Devanagari
}

# Latin-script languages: a few very common short words each.
LATIN_WORDS = {
    "en": "the what how is are a of to in do does can my i you why where when which for and".split(),
    "es": "el la los las que qué es como cómo de del en por para un una mi y está hay cuál dónde".split(),
    "fr": "le la les est ce qu que quoi comment de du des un une et mon je pour où quel quelle dans".split(),
    "pt": "o a os as que é como de do da em um uma meu eu para não onde qual está".split(),
    "sw": "ni nini vipi ya wa na kwa za la je gani wapi homa jinsi mimi".split(),
    "id": "apa bagaimana yang di dan ini itu untuk saya adalah dengan cara ke dari".split(),
    "tl": "ang ng mga sa ano paano ko ba at na ay".split(),
    "tr": "ne nasıl bir ve bu için mi mı nedir nerede".split(),
    "de": "der die das ist wie was ein eine und ich nicht wo warum".split(),
    "vi": "là gì có không của và tôi như thế nào ở".split(),
}

# Languages whose replies fit the cheap GSM-7 SMS alphabet (160 chars).
GSM_LANGS = {"en", "sw", "id", "tl", "ms"}

# Local currency used when someone asks for rates without naming one
# and we don't know their country from the phone number.
LOCAL_CURRENCY = {"lo": "LAK", "ar": "EGP", "th": "THB"}


def _in(code: str, c: str) -> bool:
    o = ord(c)
    return any(a <= o <= b for a, b in SCRIPTS[code])


def is_lao(text: str) -> bool:
    return any(_in("lo", c) for c in text)


def _latin_guess(text: str, hint: str | None) -> str | None:
    words = re.findall(r"\w+", text.lower())
    scores = {code: sum(w in vocab for w in words) for code, vocab in LATIN_WORDS.items()}
    top = max(scores.values())
    if not top:
        return None
    tied = [code for code, n in scores.items() if n == top]
    if len(tied) == 1:
        return tied[0]
    return hint if hint in tied else None


def detect(text: str, hint: str | None = None) -> str:
    """Language code of a message. `hint` is the sender's country language, if known.

    What the text is written in wins; the hint breaks ties (Persian vs Arabic
    letters, Latin text with no common words, and so on).
    """
    counts = {code: sum(1 for c in text if _in(code, c)) for code in SCRIPTS}
    best = max(counts, key=counts.get)
    if counts[best]:
        if best == "zh" and counts["ja"]:
            return "ja"  # Japanese mixes kanji with kana
        if hint in SCRIPT_SHARED_BY.get(best, ()):
            return hint
        return best
    guess = _latin_guess(text, hint)
    if guess:
        return guess
    if hint and hint not in SCRIPTS and hint not in {h for v in SCRIPT_SHARED_BY.values() for h in v}:
        return hint  # Latin text, Latin-script country language
    return "en"


MESSAGES = {
    "en": {
        "help": "GHOST SIGNAL: text any question for a short answer with its source. "
        "WEATHER <city> = forecast. RATE <currency> = exchange rate. HELP = this message.",
        "not_found": "The ghosts searched every tomb and found no trusted answer. Try fewer, simpler words, or send HELP.",
        "error": "Boo! A spirit tripped over a cable. Please try again in a minute.",
        "rate_limited": "Even ghosts need rest: too many questions this hour. Please try again later.",
        "no_city": "Send WEATHER and a city, for example: WEATHER Vientiane",
    },
    "lo": {
        "help": "GHOST SIGNAL: ສົ່ງຄຳຖາມມາ ແລ້ວຮັບຄຳຕອບສັ້ນໆ ພ້ອມແຫຼ່ງທີ່ມາ. "
        "ອາກາດ <ເມືອງ> = ສະພາບອາກາດ. ອັດຕາ <ສະກຸນເງິນ> = ອັດຕາແລກປ່ຽນ.",
        "not_found": "ຂໍອະໄພ, ບໍ່ພົບຄຳຕອບທີ່ເຊື່ອຖືໄດ້. ລອງໃຊ້ຄຳສັບທີ່ງ່າຍກວ່ານີ້.",
        "error": "ຂໍອະໄພ, ລະບົບຂັດຂ້ອງຊົ່ວຄາວ. ກະລຸນາລອງໃໝ່.",
        "rate_limited": "ຖາມຫຼາຍເກີນໄປໃນຊົ່ວໂມງນີ້. ກະລຸນາລອງໃໝ່ພາຍຫຼັງ.",
        "no_city": "ສົ່ງ ອາກາດ ແລະ ຊື່ເມືອງ, ຕົວຢ່າງ: ອາກາດ ວຽງຈັນ",
    },
    "ar": {
        "help": "GHOST SIGNAL: أرسل أي سؤال لتحصل على إجابة قصيرة مع مصدرها. "
        "طقس <مدينة> = حالة الطقس. سعر <عملة> = سعر الصرف.",
        "not_found": "عذراً، لم أجد إجابة موثوقة. جرّب كلمات أقل أو أبسط.",
        "error": "عذراً، الخدمة متوقفة مؤقتاً. حاول مرة أخرى بعد دقيقة.",
        "rate_limited": "أسئلة كثيرة في هذه الساعة. حاول لاحقاً.",
        "no_city": "أرسل طقس واسم المدينة، مثال: طقس القاهرة",
    },
}


def msg(key: str, lang: str) -> str:
    """Hand-written message; English for languages we have not written (answer.py translates those)."""
    return MESSAGES.get(lang, MESSAGES["en"])[key]
