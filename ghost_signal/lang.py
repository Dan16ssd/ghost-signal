"""Very small language detection: Lao script or not."""

from __future__ import annotations

LAO_START, LAO_END = 0x0E80, 0x0EFF


def is_lao(text: str) -> bool:
    return any(LAO_START <= ord(c) <= LAO_END for c in text)


def detect(text: str) -> str:
    """Return "lo" for Lao script, otherwise "en"."""
    return "lo" if is_lao(text) else "en"


MESSAGES = {
    "en": {
        "help": "GHOST SIGNAL: text any question and get a short answer with its source. "
        "WEATHER <city> for the forecast. HELP for this message.",
        "not_found": "Sorry, I could not find a trusted answer. Try fewer or simpler words.",
        "error": "Sorry, the spirits are quiet right now. Please try again in a minute.",
        "rate_limited": "Too many questions this hour. Please try again later.",
        "no_city": "Send WEATHER and a city, for example: WEATHER Vientiane",
    },
    "lo": {
        "help": "GHOST SIGNAL: ສົ່ງຄຳຖາມມາ ແລ້ວຮັບຄຳຕອບສັ້ນໆ ພ້ອມແຫຼ່ງທີ່ມາ. "
        "ອາກາດ <ເມືອງ> ເພື່ອເບິ່ງສະພາບອາກາດ.",
        "not_found": "ຂໍອະໄພ, ບໍ່ພົບຄຳຕອບທີ່ເຊື່ອຖືໄດ້. ລອງໃຊ້ຄຳສັບທີ່ງ່າຍກວ່ານີ້.",
        "error": "ຂໍອະໄພ, ລະບົບຂັດຂ້ອງຊົ່ວຄາວ. ກະລຸນາລອງໃໝ່.",
        "rate_limited": "ຖາມຫຼາຍເກີນໄປໃນຊົ່ວໂມງນີ້. ກະລຸນາລອງໃໝ່ພາຍຫຼັງ.",
        "no_city": "ສົ່ງ ອາກາດ ແລະ ຊື່ເມືອງ, ຕົວຢ່າງ: ອາກາດ ວຽງຈັນ",
    },
}


def msg(key: str, lang: str) -> str:
    return MESSAGES.get(lang, MESSAGES["en"])[key]
