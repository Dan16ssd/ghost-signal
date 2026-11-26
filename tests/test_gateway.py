"""Production guards: STOP/START, duplicate webhooks, daily AI budget, masking, health."""

from fastapi.testclient import TestClient

from ghost_signal import answer, app as appmod, countries, store
from ghost_signal.config import Settings
from tests.test_answer_and_app import _FakeClaude, offline  # noqa: F401


def test_stop_then_silence_then_start():
    n = "+201001234567"
    assert answer.handle("STOP", sender=n).kind == "stop"
    assert answer.handle("what is dengue", sender=n).kind == "silent"
    assert answer.handle("HELP", sender=n).text == ""
    assert answer.handle("start", sender=n).kind == "start"
    assert answer.handle("what is dengue", sender=n).kind == "answer"


def test_local_stop_word_answers_in_that_language():
    r = answer.handle("توقف", sender="+201001234567")
    assert r.kind == "stop" and r.lang == "ar"


def test_stop_inside_a_sentence_is_a_question():
    assert answer.handle("how to stop dengue", sender="+1555").kind != "stop"


def test_stop_cancels_waiting_reminders():
    n = "+8562055512345"
    answer.handle("REMIND in 1 hour pills", sender=n)
    answer.handle("STOP", sender=n)
    assert store.waiting(n) == []


def test_opted_out_number_gets_empty_twiml():
    c = TestClient(appmod.app)
    c.post("/sms", data={"From": "+15550001111", "Body": "STOP", "MessageSid": "SM1"})
    r = c.post("/sms", data={"From": "+15550001111", "Body": "dengue", "MessageSid": "SM2"})
    assert "<Message>" not in r.text


def test_twilio_retry_is_answered_once():
    c = TestClient(appmod.app)
    first = c.post("/sms", data={"From": "+15550001111", "Body": "dengue", "MessageSid": "SMabc"})
    again = c.post("/sms", data={"From": "+15550001111", "Body": "dengue", "MessageSid": "SMabc"})
    assert "<Message>" in first.text and "<Message>" not in again.text


def test_daily_ai_budget_falls_back_to_extract(monkeypatch):
    import anthropic

    monkeypatch.setattr(answer, "settings", Settings(use_llm=True, max_ai_calls_per_day=1))
    monkeypatch.setattr(anthropic, "Anthropic", _FakeClaude)
    assert answer.handle("dengue").text.startswith("Dengue is a virus")  # AI answer, uses the budget
    r = answer.handle("dengue")
    assert r.kind == "answer" and r.text.startswith("Dengue fever is a mosquito-borne")  # plain extract
    assert store.used_today("ai") == 1


def test_mask():
    assert countries.mask("+201001234567") == "+20*******567"
    assert countries.mask("web:1.2.3.4") == "web:1.2.3.4"


def test_health_reports_usage():
    answer.handle("dengue")
    data = TestClient(appmod.app).get("/health").json()
    assert data["ok"] and data["questions_today"] == 1 and "ai_budget_per_day" in data


def test_simulator_inbox():
    store.add_reminder("web:testclient", 0, "drink water", "en", "now")
    appmod.deliver_due_reminders()
    assert TestClient(appmod.app).get("/api/inbox").json() == {"messages": ["REMINDER: drink water"], "calls": []}
