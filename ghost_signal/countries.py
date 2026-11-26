"""Country from the sender's phone number: its main language and currency.

Twilio sends the sender in international format (+20..., +856...), so the
calling code tells us where the person is. The country is only a hint: what
the message is written in always wins (see lang.detect).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Country:
    code: str  # ISO 3166 alpha-2
    lang: str  # main language (Wikipedia code)
    currency: str  # ISO 4217


# calling code -> country (main language, currency). Longest prefix wins.
_BY_PREFIX: dict[str, Country] = {
    p: Country(*v)
    for p, v in {
        "1": ("US", "en", "USD"),
        "7": ("RU", "ru", "RUB"),
        "20": ("EG", "ar", "EGP"),
        "27": ("ZA", "en", "ZAR"),
        "30": ("GR", "el", "EUR"),
        "31": ("NL", "nl", "EUR"),
        "33": ("FR", "fr", "EUR"),
        "34": ("ES", "es", "EUR"),
        "39": ("IT", "it", "EUR"),
        "40": ("RO", "ro", "RON"),
        "44": ("GB", "en", "GBP"),
        "48": ("PL", "pl", "PLN"),
        "49": ("DE", "de", "EUR"),
        "51": ("PE", "es", "PEN"),
        "52": ("MX", "es", "MXN"),
        "53": ("CU", "es", "CUP"),
        "54": ("AR", "es", "ARS"),
        "55": ("BR", "pt", "BRL"),
        "56": ("CL", "es", "CLP"),
        "57": ("CO", "es", "COP"),
        "58": ("VE", "es", "VES"),
        "60": ("MY", "ms", "MYR"),
        "61": ("AU", "en", "AUD"),
        "62": ("ID", "id", "IDR"),
        "63": ("PH", "tl", "PHP"),
        "64": ("NZ", "en", "NZD"),
        "65": ("SG", "en", "SGD"),
        "66": ("TH", "th", "THB"),
        "81": ("JP", "ja", "JPY"),
        "82": ("KR", "ko", "KRW"),
        "84": ("VN", "vi", "VND"),
        "86": ("CN", "zh", "CNY"),
        "90": ("TR", "tr", "TRY"),
        "91": ("IN", "hi", "INR"),
        "92": ("PK", "ur", "PKR"),
        "93": ("AF", "fa", "AFN"),
        "94": ("LK", "si", "LKR"),
        "95": ("MM", "my", "MMK"),
        "98": ("IR", "fa", "IRR"),
        "211": ("SS", "en", "SSP"),
        "212": ("MA", "ar", "MAD"),
        "213": ("DZ", "ar", "DZD"),
        "216": ("TN", "ar", "TND"),
        "218": ("LY", "ar", "LYD"),
        "220": ("GM", "en", "GMD"),
        "221": ("SN", "fr", "XOF"),
        "223": ("ML", "fr", "XOF"),
        "225": ("CI", "fr", "XOF"),
        "226": ("BF", "fr", "XOF"),
        "227": ("NE", "fr", "XOF"),
        "229": ("BJ", "fr", "XOF"),
        "231": ("LR", "en", "LRD"),
        "232": ("SL", "en", "SLE"),
        "233": ("GH", "en", "GHS"),
        "234": ("NG", "en", "NGN"),
        "235": ("TD", "fr", "XAF"),
        "237": ("CM", "fr", "XAF"),
        "243": ("CD", "fr", "CDF"),
        "244": ("AO", "pt", "AOA"),
        "249": ("SD", "ar", "SDG"),
        "250": ("RW", "rw", "RWF"),
        "251": ("ET", "am", "ETB"),
        "252": ("SO", "so", "SOS"),
        "254": ("KE", "sw", "KES"),
        "255": ("TZ", "sw", "TZS"),
        "256": ("UG", "en", "UGX"),
        "257": ("BI", "fr", "BIF"),
        "258": ("MZ", "pt", "MZN"),
        "260": ("ZM", "en", "ZMW"),
        "261": ("MG", "mg", "MGA"),
        "263": ("ZW", "en", "ZWG"),
        "265": ("MW", "en", "MWK"),
        "380": ("UA", "uk", "UAH"),
        "509": ("HT", "fr", "HTG"),
        "591": ("BO", "es", "BOB"),
        "593": ("EC", "es", "USD"),
        "855": ("KH", "km", "KHR"),
        "856": ("LA", "lo", "LAK"),
        "880": ("BD", "bn", "BDT"),
        "961": ("LB", "ar", "LBP"),
        "962": ("JO", "ar", "JOD"),
        "963": ("SY", "ar", "SYP"),
        "964": ("IQ", "ar", "IQD"),
        "966": ("SA", "ar", "SAR"),
        "967": ("YE", "ar", "YER"),
        "970": ("PS", "ar", "ILS"),
        "971": ("AE", "ar", "AED"),
        "977": ("NP", "ne", "NPR"),
        "992": ("TJ", "tg", "TJS"),
        "994": ("AZ", "az", "AZN"),
        "995": ("GE", "ka", "GEL"),
        "996": ("KG", "ky", "KGS"),
        "998": ("UZ", "uz", "UZS"),
    }.items()
}


def from_number(number: str | None) -> Country | None:
    """'+201001234567' -> Egypt. None for unknown or non-phone senders."""
    digits = (number or "").strip()
    if not digits.startswith("+"):
        return None
    digits = "".join(c for c in digits if c.isdigit())
    for n in (3, 2, 1):
        country = _BY_PREFIX.get(digits[:n])
        if country:
            return country
    return None


def from_code(code: str | None) -> Country | None:
    """'EG' -> Egypt (used by the web simulator's country picker)."""
    code = (code or "").upper()
    return next((c for c in _BY_PREFIX.values() if c.code == code), None)


# Main time zone per country (big countries use their most populous zone).
TIMEZONES = {
    "US": "America/New_York", "RU": "Europe/Moscow", "EG": "Africa/Cairo", "ZA": "Africa/Johannesburg",
    "GR": "Europe/Athens", "NL": "Europe/Amsterdam", "FR": "Europe/Paris", "ES": "Europe/Madrid",
    "IT": "Europe/Rome", "RO": "Europe/Bucharest", "GB": "Europe/London", "PL": "Europe/Warsaw",
    "DE": "Europe/Berlin", "PE": "America/Lima", "MX": "America/Mexico_City", "CU": "America/Havana",
    "AR": "America/Argentina/Buenos_Aires", "BR": "America/Sao_Paulo", "CL": "America/Santiago",
    "CO": "America/Bogota", "VE": "America/Caracas", "MY": "Asia/Kuala_Lumpur", "AU": "Australia/Sydney",
    "ID": "Asia/Jakarta", "PH": "Asia/Manila", "NZ": "Pacific/Auckland", "SG": "Asia/Singapore",
    "TH": "Asia/Bangkok", "JP": "Asia/Tokyo", "KR": "Asia/Seoul", "VN": "Asia/Ho_Chi_Minh",
    "CN": "Asia/Shanghai", "TR": "Europe/Istanbul", "IN": "Asia/Kolkata", "PK": "Asia/Karachi",
    "AF": "Asia/Kabul", "LK": "Asia/Colombo", "MM": "Asia/Yangon", "IR": "Asia/Tehran",
    "SS": "Africa/Juba", "MA": "Africa/Casablanca", "DZ": "Africa/Algiers", "TN": "Africa/Tunis",
    "LY": "Africa/Tripoli", "GM": "Africa/Banjul", "SN": "Africa/Dakar", "ML": "Africa/Bamako",
    "CI": "Africa/Abidjan", "BF": "Africa/Ouagadougou", "NE": "Africa/Niamey", "BJ": "Africa/Porto-Novo",
    "LR": "Africa/Monrovia", "SL": "Africa/Freetown", "GH": "Africa/Accra", "NG": "Africa/Lagos",
    "TD": "Africa/Ndjamena", "CM": "Africa/Douala", "CD": "Africa/Kinshasa", "AO": "Africa/Luanda",
    "SD": "Africa/Khartoum", "RW": "Africa/Kigali", "ET": "Africa/Addis_Ababa", "SO": "Africa/Mogadishu",
    "KE": "Africa/Nairobi", "TZ": "Africa/Dar_es_Salaam", "UG": "Africa/Kampala", "BI": "Africa/Bujumbura",
    "MZ": "Africa/Maputo", "ZM": "Africa/Lusaka", "MG": "Indian/Antananarivo", "ZW": "Africa/Harare",
    "MW": "Africa/Blantyre", "UA": "Europe/Kyiv", "HT": "America/Port-au-Prince", "BO": "America/La_Paz",
    "EC": "America/Guayaquil", "KH": "Asia/Phnom_Penh", "LA": "Asia/Vientiane", "BD": "Asia/Dhaka",
    "LB": "Asia/Beirut", "JO": "Asia/Amman", "SY": "Asia/Damascus", "IQ": "Asia/Baghdad",
    "SA": "Asia/Riyadh", "YE": "Asia/Aden", "PS": "Asia/Gaza", "AE": "Asia/Dubai", "NP": "Asia/Kathmandu",
    "TJ": "Asia/Dushanbe", "AZ": "Asia/Baku", "GE": "Asia/Tbilisi", "KG": "Asia/Bishkek",
    "UZ": "Asia/Tashkent",
}


def timezone(country: Country | None) -> str:
    """IANA time zone for a country; UTC when unknown."""
    return TIMEZONES.get(country.code, "UTC") if country else "UTC"


def mask(number: str) -> str:
    """'+201001234567' -> '+20*******567' for logs and screens."""
    if not number.startswith("+") or len(number) < 7:
        return number
    return number[:3] + "*" * (len(number) - 6) + number[-3:]
