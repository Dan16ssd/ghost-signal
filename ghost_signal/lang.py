"""Language detection by script, plus fixed replies in each supported language.

Detection is by alphabet, which is reliable for short SMS:
Lao, Arabic and Thai each have their own script; everything else counts as English.
"""

from __future__ import annotations

SCRIPTS = {
    "lo": [(0x0E80, 0x0EFF)],
    "th": [(0x0E00, 0x0E7F)],
    "ar": [(0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF), (0xFB50, 0xFDFF), (0xFE70, 0xFEFF)],
}

# Local currency used when someone asks for rates without naming one.
LOCAL_CURRENCY = {"lo": "LAK", "ar": "EGP", "th": "THB"}


def _in(code: str, c: str) -> bool:
    o = ord(c)
    return any(a <= o <= b for a, b in SCRIPTS[code])


def is_lao(text: str) -> bool:
    return any(_in("lo", c) for c in text)


def detect(text: str) -> str:
    """Return "lo", "ar", "th" or "en" (the default)."""
    counts = {code: sum(1 for c in text if _in(code, c)) for code in SCRIPTS}
    best = max(counts, key=counts.get)
    return best if counts[best] else "en"


MESSAGES = {
    "en": {
        "help": "GHOST SIGNAL: text any question for a short answer with its source. "
        "WEATHER <city> = forecast. RATE <currency> = exchange rate. HELP = this message.",
        "not_found": "Sorry, I could not find a trusted answer. Try fewer or simpler words.",
        "error": "Sorry, the spirits are quiet right now. Please try again in a minute.",
        "rate_limited": "Too many questions this hour. Please try again later.",
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
    return MESSAGES.get(lang, MESSAGES["en"])[key]
