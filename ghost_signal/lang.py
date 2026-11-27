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
# Medicine words, so 'MEDS 8am blood pressure pill' shows it is English (the call language).
MED_WORDS = {
    "en": "pill pills tablet tablets blood pressure sugar heart medicine take insulin vitamin morning night".split(),
    "es": "pastilla pastillas presión azúcar corazón tomar medicina tableta".split(),
    "fr": "comprimé comprimés pilule tension sucre cœur médicament prendre".split(),
    "pt": "comprimido remédio pressão açúcar coração tomar".split(),
    "sw": "dawa vidonge presha sukari moyo".split(),
    "id": "obat tablet darah tekanan gula jantung minum".split(),
    "tl": "gamot presyon dugo asukal puso inumin".split(),
}

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


def has_own_language(text: str) -> bool:
    """True when the text itself shows its language (its alphabet, or common words), not only a hint."""
    return any(_in(code, c) for code in SCRIPTS for c in text) or _latin_guess(text, None) is not None


def _latin_guess(text: str, hint: str | None) -> str | None:
    words = re.findall(r"\w+", text.lower())
    scores = {code: sum(w in vocab or w in MED_WORDS.get(code, ()) for w in words) for code, vocab in LATIN_WORDS.items()}
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
        "WEATHER <city>. RATE <currency>. REMIND 8pm <what>. MEDS 8am <pill> = daily call. STOP ends texts.",
        "not_found": "The ghosts searched every tomb and found no trusted answer. Try fewer, simpler words, or send HELP.",
        "error": "Boo! A spirit tripped over a cable. Please try again in a minute.",
        "rate_limited": "Even ghosts need rest: too many questions this hour. Please try again later.",
        "no_city": "Send WEATHER and a city, for example: WEATHER Vientiane",
        "reminder_set": "Reminder saved. I will text you on",
        "reminder_bad": "I could not read the time. Try: REMIND 8pm take medicine, or REMIND in 2 hours call mum",
        "reminder_none": "No reminders waiting. Try: REMIND 8pm take medicine",
        "reminder_list": "Your reminders (REMIND DEL <number> deletes one):",
        "reminder_deleted": "Reminder deleted:",
        "reminder_full": "You have the most reminders allowed. Send REMIND LIST, then REMIND DEL <number>.",
        "reminder_due": "REMINDER:",
        "stopped": "You will get no more texts from Ghost Signal. Send START to come back.",
        "started": "Welcome back! The ghosts are listening again. Send HELP for commands.",
        "meds_set": "Medicine calls set. I will call you every day at",
        "meds_sms": "Medicine reminders set (by SMS: no voice for your language yet). Every day at",
        "meds_bad": "I could not read the times. Try: MEDS 8am 8pm blood pressure pill",
        "meds_none": "No medicine calls. Try: MEDS 8am 8pm blood pressure pill",
        "meds_list": "Your medicine calls (MEDS DEL <number> stops one):",
        "meds_deleted": "Medicine calls stopped:",
        "meds_full": "You have the most medicines allowed. Send MEDS LIST, then MEDS DEL <number>.",
        "meds_due": "MEDICINE TIME:",
        "meds_press": "Reply 1 when you have taken it.",
        "meds_taken": "Thank you! Taken. Stay well.",
        "family_set": "Invitation sent. They will get an SMS if you miss a dose, after they reply YES.",
        "family_bad": "Send MEDS FAMILY and their number with country code, for example: MEDS FAMILY +8562055512345",
        "family_invite": "Ghost Signal: the number below asks you to be their family contact for medicine reminders. Reply YES to get an SMS if they miss a dose. Number:",
        "family_ok": "Thank you. You will get an SMS if they miss a dose. Send STOP to stop.",
        "family_alert": "Ghost Signal: no answer to 2 medicine calls. Please check on",
    },
    "lo": {
        "help": "GHOST SIGNAL: ສົ່ງຄຳຖາມ ຮັບຄຳຕອບສັ້ນໆ. "
        "ອາກາດ <ເມືອງ>. ອັດຕາ <ເງິນ>. ເຕືອນ 8pm <ເລື່ອງ>. MEDS 8am <ຢາ>. STOP",
        "not_found": "ຂໍອະໄພ, ບໍ່ພົບຄຳຕອບທີ່ເຊື່ອຖືໄດ້. ລອງໃຊ້ຄຳສັບທີ່ງ່າຍກວ່ານີ້.",
        "error": "ຂໍອະໄພ, ລະບົບຂັດຂ້ອງຊົ່ວຄາວ. ກະລຸນາລອງໃໝ່.",
        "rate_limited": "ຖາມຫຼາຍເກີນໄປໃນຊົ່ວໂມງນີ້. ກະລຸນາລອງໃໝ່ພາຍຫຼັງ.",
        "no_city": "ສົ່ງ ອາກາດ ແລະ ຊື່ເມືອງ, ຕົວຢ່າງ: ອາກາດ ວຽງຈັນ",
        "reminder_set": "ບັນທຶກການເຕືອນແລ້ວ. ຈະສົ່ງຫາທ່ານ",
        "reminder_bad": "ອ່ານເວລາບໍ່ໄດ້. ລອງ: ເຕືອນ 8pm ກິນຢາ",
        "reminder_none": "ບໍ່ມີການເຕືອນ. ລອງ: ເຕືອນ 8pm ກິນຢາ",
        "reminder_list": "ການເຕືອນຂອງທ່ານ (REMIND DEL <ເລກ> ເພື່ອລຶບ):",
        "reminder_deleted": "ລຶບການເຕືອນແລ້ວ:",
        "reminder_full": "ການເຕືອນເຕັມແລ້ວ. ສົ່ງ REMIND LIST ແລ້ວ REMIND DEL <ເລກ>.",
        "reminder_due": "ແຈ້ງເຕືອນ:",
        "stopped": "ທ່ານຈະບໍ່ໄດ້ຮັບຂໍ້ຄວາມອີກ. ສົ່ງ START ເພື່ອກັບມາ.",
        "started": "ຍິນດີຕ້ອນຮັບກັບມາ! ສົ່ງ HELP ເພື່ອເບິ່ງຄຳສັ່ງ.",
        "meds_set": "ຕັ້ງໂທເຕືອນກິນຢາແລ້ວ. ຈະໂທຫາທ່ານທຸກມື້ເວລາ",
        "meds_sms": "ຕັ້ງເຕືອນກິນຢາແລ້ວ (ທາງ SMS). ທຸກມື້ເວລາ",
        "meds_bad": "ອ່ານເວລາບໍ່ໄດ້. ລອງ: MEDS 8am 8pm ຢາຄວາມດັນ",
        "meds_none": "ບໍ່ມີການໂທເຕືອນກິນຢາ. ລອງ: MEDS 8am 8pm ຢາຄວາມດັນ",
        "meds_list": "ການເຕືອນກິນຢາ (MEDS DEL <ເລກ> ເພື່ອຢຸດ):",
        "meds_deleted": "ຢຸດໂທເຕືອນແລ້ວ:",
        "meds_full": "ຢາເຕັມແລ້ວ. ສົ່ງ MEDS LIST ແລ້ວ MEDS DEL <ເລກ>.",
        "meds_due": "ເຖິງເວລາກິນຢາ:",
        "meds_press": "ກິນແລ້ວ ຕອບ 1.",
        "meds_taken": "ຂອບໃຈ! ກິນຢາແລ້ວ. ຮັກສາສຸຂະພາບເດີ້.",
        "family_set": "ສົ່ງຄຳເຊີນແລ້ວ. ເມື່ອເຂົາຕອບ YES, ເຂົາຈະໄດ້ SMS ຖ້າທ່ານລືມກິນຢາ.",
        "family_bad": "ສົ່ງ MEDS FAMILY ແລະ ເບີໂທພ້ອມລະຫັດປະເທດ, ຕົວຢ່າງ: MEDS FAMILY +8562055512345",
        "family_invite": "Ghost Signal: ເບີນີ້ຂໍໃຫ້ທ່ານເປັນຄົນໃນຄອບຄົວສຳລັບເຕືອນກິນຢາ. ຕອບ YES ເພື່ອຮັບ SMS ຖ້າເຂົາລືມກິນຢາ. ເບີ:",
        "family_ok": "ຂອບໃຈ. ທ່ານຈະໄດ້ SMS ຖ້າເຂົາລືມກິນຢາ. ສົ່ງ STOP ເພື່ອຢຸດ.",
        "family_alert": "Ghost Signal: ໂທເຕືອນກິນຢາ 2 ເທື່ອ ບໍ່ມີຄົນຮັບ. ກະລຸນາຖາມຂ່າວ",
    },
    "ar": {
        "help": "GHOST SIGNAL: أرسل سؤالك لتصلك إجابة قصيرة. "
        "طقس <مدينة>. سعر <عملة>. ذكرني <وقت> <أمر>. MEDS 8am <دواء>. STOP",
        "not_found": "عذراً، لم أجد إجابة موثوقة. جرّب كلمات أقل أو أبسط.",
        "error": "عذراً، الخدمة متوقفة مؤقتاً. حاول مرة أخرى بعد دقيقة.",
        "rate_limited": "أسئلة كثيرة في هذه الساعة. حاول لاحقاً.",
        "no_city": "أرسل طقس واسم المدينة، مثال: طقس القاهرة",
        "reminder_set": "تم حفظ التذكير. سأرسل لك في",
        "reminder_bad": "لم أفهم الوقت. جرّب: ذكرني الساعة 8 مساءً بالدواء",
        "reminder_none": "لا توجد تذكيرات. جرّب: ذكرني الساعة 8 مساءً بالدواء",
        "reminder_list": "تذكيراتك (REMIND DEL <رقم> للحذف):",
        "reminder_deleted": "تم حذف التذكير:",
        "reminder_full": "وصلت للحد الأقصى من التذكيرات. أرسل REMIND LIST ثم REMIND DEL <رقم>.",
        "reminder_due": "تذكير:",
        "stopped": "لن تصلك رسائل أخرى من Ghost Signal. أرسل START للعودة.",
        "started": "أهلاً بعودتك! أرسل HELP لمعرفة الأوامر.",
        "meds_set": "تم ضبط مكالمات الدواء. سأتصل بك كل يوم الساعة",
        "meds_sms": "تم ضبط تذكير الدواء (برسالة SMS). كل يوم الساعة",
        "meds_bad": "لم أفهم المواعيد. جرّب: MEDS 8am 8pm دواء الضغط",
        "meds_none": "لا توجد مكالمات دواء. جرّب: MEDS 8am 8pm دواء الضغط",
        "meds_list": "مكالمات الدواء (MEDS DEL <رقم> للإيقاف):",
        "meds_deleted": "تم إيقاف مكالمات الدواء:",
        "meds_full": "وصلت للحد الأقصى من الأدوية. أرسل MEDS LIST ثم MEDS DEL <رقم>.",
        "meds_due": "وقت الدواء:",
        "meds_press": "أرسل 1 بعد أن تأخذه.",
        "meds_taken": "شكراً! تم. نتمنى لك الصحة.",
        "family_set": "تم إرسال الدعوة. سيصله SMS إذا فاتتك جرعة، بعد أن يرد بـ YES.",
        "family_bad": "أرسل MEDS FAMILY ورقمه مع رمز الدولة، مثال: MEDS FAMILY +8562055512345",
        "family_invite": "Ghost Signal: صاحب الرقم أدناه يطلب أن تكون جهة اتصال عائلية لتذكير الدواء. أرسل YES لتصلك رسالة إذا فاتته جرعة. الرقم:",
        "family_ok": "شكراً. ستصلك رسالة إذا فاتته جرعة. أرسل STOP للإيقاف.",
        "family_alert": "Ghost Signal: لا رد على مكالمتين للدواء. يرجى الاطمئنان على",
    },
}


def msg(key: str, lang: str) -> str:
    """Hand-written message; English for languages we have not written (answer.py translates those)."""
    return MESSAGES.get(lang, MESSAGES["en"])[key]
