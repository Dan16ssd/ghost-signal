"""Answer pipeline and web server, with the network stubbed out."""

import pytest
from fastapi.testclient import TestClient

from ghost_signal import answer, app as appmod, lang, sources, store, twilio_sms
from ghost_signal.config import Settings


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """No network and no AI in tests."""
    monkeypatch.setattr(answer, "settings", Settings(use_llm=False, max_segments=3))
    monkeypatch.setattr(appmod, "settings", Settings(use_llm=False, twilio_auth_token="", twilio_account_sid=""))
    monkeypatch.setattr(
        sources,
        "wikipedia",
        lambda q, lang="en", limit=3: [
            sources.Source(
                "Dengue fever",
                "Dengue fever is a mosquito-borne disease caused by the dengue virus. "
                "Symptoms include high fever, headache and muscle pain. Rest and fluids help.",
                "https://en.m.wikipedia.org/wiki/Dengue_fever",
            )
        ]
        if "dengue" in q.lower()
        else [],
    )
    monkeypatch.setattr(
        sources, "weather", lambda city: None if city == "Nowhere" else f"{city}: now 31C, partly cloudy. (Open-Meteo)"
    )
    store.open_db(":memory:")
    answer._translated.cache_clear()


def test_help():
    assert answer.handle("HELP").kind == "help"
    assert answer.handle("").kind == "help"
    assert lang.is_lao(answer.handle("ຊ່ວຍ").text)


def test_question_gets_answer_with_source():
    r = answer.handle("what is dengue fever")
    assert r.kind == "answer"
    assert "mosquito" in r.text
    assert "Src: en.wikipedia.org/wiki/Dengue_fever" in r.text
    assert r.segments <= 3


def test_unknown_question():
    assert answer.handle("zzzz qqqq").kind == "not_found"


def test_weather():
    assert answer.handle("WEATHER Vientiane").text.startswith("Vientiane")
    assert answer.handle("weather Nowhere").kind == "not_found"
    assert answer.handle("WEATHER").kind == "help"


def test_lao_question_gets_lao_messages():
    r = answer.handle("ຄຳຖາມ ທີ່ບໍ່ມີຄຳຕອບ")
    assert r.lang == "lo" and r.kind == "not_found" and lang.is_lao(r.text)


def test_simulator_api_and_page():
    c = TestClient(appmod.app)
    assert "GHOST SIGNAL" in c.get("/").text
    data = c.post("/api/ask", json={"text": "dengue"}).json()
    assert data["kind"] == "answer" and data["segments"] >= 1


def test_sms_webhook_inline_twiml():
    c = TestClient(appmod.app)
    r = c.post("/sms", data={"From": "+15550001111", "Body": "dengue"})
    assert r.status_code == 200
    assert "<Message>" in r.text and "mosquito" in r.text


def test_sms_webhook_rejects_bad_signature(monkeypatch):
    monkeypatch.setattr(appmod, "settings", Settings(use_llm=False, twilio_auth_token="secret"))
    c = TestClient(appmod.app)
    r = c.post("/sms", data={"From": "+1", "Body": "hi"}, headers={"X-Twilio-Signature": "wrong"})
    assert r.status_code == 403


def test_sms_webhook_accepts_good_signature(monkeypatch):
    monkeypatch.setattr(appmod, "settings", Settings(use_llm=False, twilio_auth_token="secret"))
    c = TestClient(appmod.app)
    params = {"From": "+1", "Body": "dengue"}
    sig = twilio_sms.expected_signature("secret", "http://testserver/sms", params)
    r = c.post("/sms", data=params, headers={"X-Twilio-Signature": sig})
    assert r.status_code == 200


def test_rate_limit(monkeypatch):
    monkeypatch.setattr(appmod, "settings", Settings(max_questions_per_hour=2))
    assert appmod.allowed("+1", now=0)
    assert appmod.allowed("+1", now=1)
    assert not appmod.allowed("+1", now=2)
    assert appmod.allowed("+1", now=4000)  # an hour later


def test_twiml_escapes():
    assert "&lt;b&gt;" in twilio_sms.twiml("<b>")


class _FakeClaude:
    """Stands in for anthropic.Anthropic; returns a fixed reply."""

    reply = "Dengue is a virus spread by mosquitoes. Rest, drink fluids, see a health worker. [1]"

    def __init__(self, **kwargs):
        self.beta = self
        self.messages = self

    def create(self, **kwargs):
        from types import SimpleNamespace as NS

        assert kwargs["fallbacks"] == "default"
        return NS(stop_reason="end_turn", content=[NS(type="text", text=self.reply)])


def test_ai_answer_cites_the_source_it_used(monkeypatch):
    import anthropic

    monkeypatch.setattr(answer, "settings", Settings(use_llm=True, max_segments=3))
    monkeypatch.setattr(anthropic, "Anthropic", _FakeClaude)
    r = answer.handle("dengue")
    assert r.kind == "answer"
    assert "[1]" not in r.text
    assert r.text.startswith("Dengue is a virus") and "Src: en.wikipedia.org/wiki/Dengue_fever" in r.text


def test_ai_not_found(monkeypatch):
    import anthropic

    monkeypatch.setattr(answer, "settings", Settings(use_llm=True))
    monkeypatch.setattr(_FakeClaude, "reply", "NOT_FOUND")
    monkeypatch.setattr(anthropic, "Anthropic", _FakeClaude)
    assert answer.handle("dengue").kind == "not_found"


def test_detect_languages():
    assert lang.detect("ما هي حمى الضنك؟") == "ar"
    assert lang.detect("ສະບາຍດີ") == "lo"
    assert lang.detect("สวัสดี") == "th"
    assert lang.detect("hello") == "en"


def test_arabic_help_and_not_found():
    assert lang.detect(answer.handle("مساعدة").text) == "ar"
    r = answer.handle("سؤال بلا إجابة")
    assert r.lang == "ar" and r.kind == "not_found" and lang.detect(r.text) == "ar"


def test_arabic_weather_command():
    assert answer.handle("طقس القاهرة").kind == "weather"


def test_rate_command(monkeypatch):
    calls = []

    def fake_rate(base, targets):
        calls.append((base, targets))
        return f"1 {base} = " + ", ".join(f"1 {t}" for t in targets)

    monkeypatch.setattr(sources, "exchange_rate", fake_rate)
    assert answer.handle("RATE").kind == "rate"
    assert calls[-1][0] == "USD" and "PHP" in calls[-1][1] and "LAK" in calls[-1][1]
    answer.handle("سعر USD")
    assert calls[-1] == ("USD", ["EGP"])  # Arabic speaker gets Egyptian pounds
    answer.handle("ອັດຕາ USD")
    assert calls[-1] == ("USD", ["LAK"])  # Lao speaker gets kip
    answer.handle("rate EUR THB")
    assert calls[-1] == ("EUR", ["THB"])


def test_lao_question_translated_for_english_search(monkeypatch):
    import anthropic

    seen = []
    real = sources.wikipedia

    def wiki(q, lang="en", limit=3):
        seen.append((q, lang))
        return real(q, lang, limit)

    monkeypatch.setattr(sources, "wikipedia", wiki)
    monkeypatch.setattr(answer, "settings", Settings(use_llm=True))
    monkeypatch.setattr(_FakeClaude, "reply", "dengue fever")
    monkeypatch.setattr(anthropic, "Anthropic", _FakeClaude)
    answer.handle("ໄຂ້ເລືອດອອກ")
    assert ("dengue fever", "en") in seen
