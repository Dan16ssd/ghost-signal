"""Any country: language from the text, country (currency, language hint) from the phone number."""

from fastapi.testclient import TestClient

from ghost_signal import answer, app as appmod, countries, lang, sources
from ghost_signal.config import Settings
from tests.test_answer_and_app import _FakeClaude, offline  # noqa: F401 - reuse the offline fixture


def test_country_from_phone_number():
    assert countries.from_number("+201001234567").code == "EG"
    assert countries.from_number("+8562055512345").currency == "LAK"
    assert countries.from_number("+254712345678").lang == "sw"
    assert countries.from_number("+15551234567").code == "US"
    assert countries.from_number("web:127.0.0.1") is None
    assert countries.from_code("ng").currency == "NGN"


def test_detect_many_languages():
    assert lang.detect("डेंगू क्या है") == "hi"
    assert lang.detect("ডেঙ্গু কী") == "bn"
    assert lang.detect("Что такое денге") == "ru"
    assert lang.detect("デング熱とは") == "ja"
    assert lang.detect("登革热") == "zh"
    assert lang.detect("¿Cómo tratar el dengue?") == "es"
    assert lang.detect("Qu'est-ce que la dengue") == "fr"
    assert lang.detect("Homa ya dengue ni nini") == "sw"
    assert lang.detect("what is dengue") == "en"


def test_country_breaks_ties():
    assert lang.detect("دنگی چیست", hint="fa") == "fa"  # Persian in Arabic letters
    assert lang.detect("dengue", hint="pt") == "pt"  # no common words: trust the country
    assert lang.detect("dengue", hint="hi") == "en"  # Latin text from India: English
    assert lang.detect("what is dengue", hint="es") == "en"  # the text wins


def test_rate_uses_the_senders_currency(monkeypatch):
    calls = []
    monkeypatch.setattr(sources, "exchange_rate", lambda b, t: calls.append((b, t)) or f"1 {b} = 1 {t[0]}")
    answer.handle("RATE", sender="+234803000000")
    assert calls[-1][0] == "USD" and calls[-1][1][0] == "NGN"  # Nigeria
    answer.handle("RATE EUR", sender="+254712345678")
    assert calls[-1] == ("EUR", ["KES"])  # Kenya
    answer.handle("RATE", sender="+15551234567")
    assert calls[-1][0] == "EUR" and calls[-1][1][0] == "USD"  # US: euro in dollars


def test_question_searches_the_local_wikipedia(monkeypatch):
    seen = []
    monkeypatch.setattr(sources, "wikipedia", lambda q, lang="en", limit=3: seen.append(lang) or [])
    answer.handle("Homa ya dengue ni nini", sender="+254712345678")
    assert seen[0] == "sw"


def test_unwritten_language_gets_translated_message_once(monkeypatch):
    import anthropic

    made = []

    class Fake(_FakeClaude):
        reply = "Los fantasmas no encontraron nada."

        def __init__(self, **kw):
            made.append(1)
            super().__init__(**kw)

    monkeypatch.setattr(answer, "settings", Settings(use_llm=True))
    monkeypatch.setattr(anthropic, "Anthropic", Fake)
    assert answer.message("not_found", "es") == "Los fantasmas no encontraron nada."
    assert answer.message("not_found", "es") == "Los fantasmas no encontraron nada."
    assert len(made) == 1  # cached
    assert answer.message("not_found", "ar") == lang.msg("not_found", "ar")  # hand-written, no AI


def test_no_ai_falls_back_to_english_messages():
    assert answer.message("error", "sw") == lang.msg("error", "en")


def test_local_help_words():
    assert answer.handle("ayuda").kind == "help"
    assert answer.handle("मदद").kind == "help"


def test_simulator_country_picker(monkeypatch):
    calls = []
    monkeypatch.setattr(sources, "exchange_rate", lambda b, t: calls.append((b, t)) or f"1 {b} = 1 {t[0]}")
    c = TestClient(appmod.app)
    data = c.post("/api/ask", json={"text": "RATE", "country": "BR"}).json()
    assert data["kind"] == "rate" and calls[-1][1][0] == "BRL"


def test_sms_webhook_uses_sender_country(monkeypatch):
    calls = []
    monkeypatch.setattr(sources, "exchange_rate", lambda b, t: calls.append((b, t)) or f"1 {b} = 1 {t[0]}")
    c = TestClient(appmod.app)
    c.post("/sms", data={"From": "+201001234567", "Body": "rate"})
    assert calls[-1][1][0] == "EGP"


def test_ai_retries_english_when_local_wikipedia_misses(monkeypatch):
    import anthropic

    seen = []

    def wiki(q, lang="en", limit=3):
        seen.append((q, lang))
        url = f"https://{lang}.wikipedia.org/wiki/X"
        return [sources.Source("X", "Malaria is ..." if lang == "sw" else "Dengue is spread by mosquitoes.", url)]

    replies = iter(["NOT_FOUND", "dengue fever", "Dengue huenezwa na mbu. [1]"])

    class Fake(_FakeClaude):
        def create(self, **kw):
            from types import SimpleNamespace as NS

            return NS(stop_reason="end_turn", content=[NS(type="text", text=next(replies))])

    monkeypatch.setattr(sources, "wikipedia", wiki)
    monkeypatch.setattr(answer, "settings", Settings(use_llm=True))
    monkeypatch.setattr(anthropic, "Anthropic", Fake)
    r = answer.handle("Homa ya dengue ni nini", sender="+254712345678")
    assert r.kind == "answer" and r.text.startswith("Dengue huenezwa na mbu")
    assert seen == [("Homa ya dengue ni nini", "sw"), ("dengue fever", "en")]
    assert "en.wikipedia.org" in r.text
