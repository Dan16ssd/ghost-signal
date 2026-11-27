"""MEDS: daily medicine calls with press-1 confirmation, retries and a family alert."""

import dataclasses
import re
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, given, settings as hsettings, strategies as st

from ghost_signal import answer, app as appmod, meds, store, twilio_sms
from ghost_signal.config import Settings
from tests.test_answer_and_app import _FakeClaude, offline  # noqa: F401

EGYPT = "+201001234567"
LAOS = "+8562055512345"
LIVE = Settings(twilio_account_sid="AC1", twilio_auth_token="tok", twilio_from_number="+15550000000",
                public_base_url="https://ghost.example")


@pytest.fixture(autouse=True)
def no_signature_check(monkeypatch):
    """Signatures have their own tests; here the fake Twilio calls the voice pages directly."""
    monkeypatch.setattr(appmod, "_check_twilio", lambda request, params: None)


def test_parse_times_and_medicine():
    assert meds.parse("8am 8pm blood pressure pill") == (["08:00", "20:00"], "blood pressure pill")
    assert meds.parse("metformin at 7:30am and 19:30") == (["07:30", "19:30"], "metformin")
    assert meds.parse("every day 9pm insulin") == (["21:00"], "insulin")
    assert meds.parse("blood pressure pill") is None
    assert meds.parse("8am") is None
    assert meds.parse("1am 2am 3am 4am 5am pill") is None  # at most 4 times


def test_ai_reading_for_other_languages():
    assert meds.parse_ai_reply('{"times": ["20:00", "08:00"], "what": "دواء الضغط"}') == (
        ["08:00", "20:00"], "دواء الضغط")
    assert meds.parse_ai_reply("NONE") is None
    assert meds.parse_ai_reply('{"times": ["25:00"], "what": "x"}') is None


@hsettings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    times=st.lists(st.tuples(st.integers(0, 23), st.integers(0, 59)), min_size=1, max_size=4, unique=True),
    offset=st.integers(0, 2 * 365 * 24 * 60),
    zone=st.sampled_from(["Asia/Vientiane", "Africa/Cairo", "America/New_York", "Europe/London"]),
)
def test_next_dose_is_always_the_next_listed_time_within_a_day(times, offset, zone):
    spec = ",".join(f"{h:02d}:{m:02d}" for h, m in sorted(times))
    after = datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() + offset * 60
    due = meds.next_due(spec, zone, after)
    assert after < due <= after + 25 * 3600
    local = datetime.fromtimestamp(due, ZoneInfo(zone))
    # Usually exactly a listed time; on a daylight-saving day the clock can show a skipped hour.
    assert f"{local.hour:02d}:{local.minute:02d}" in spec.split(",") or local.dst() != datetime.fromtimestamp(after, ZoneInfo(zone)).dst()


def test_meds_command_sets_daily_calls_in_local_time():
    r = answer.handle("MEDS 8am 8pm blood pressure pill", sender=EGYPT)
    assert r.kind == "meds" and "08:00 20:00" in r.text and "UTC" not in r.text
    (m,) = store.meds_of(EGYPT)
    assert m.tz == "Africa/Cairo" and m.spoken == "blood pressure pill"
    (d,) = store.doses_to_try(time.time() + 2 * 86400)
    local = datetime.fromtimestamp(d.due, ZoneInfo("Africa/Cairo"))
    assert (local.hour, local.minute) in {(8, 0), (20, 0)} and d.due > time.time()


def test_list_delete_limit_and_bad_input(monkeypatch):
    assert answer.handle("MEDS LIST", sender=EGYPT).text == answer.message("meds_none", "ar")
    answer.handle("MEDS 8am pill one", sender=EGYPT)
    answer.handle("MEDS 9pm pill two", sender=EGYPT)
    assert "pill two" in answer.handle("meds list", sender=EGYPT).text
    assert "pill one" in answer.handle("MEDS DEL 1", sender=EGYPT).text
    assert [m.what for m in store.meds_of(EGYPT)] == ["pill two"]
    assert answer.handle("MEDS someday", sender=EGYPT).text == answer.message("meds_bad", "ar")
    monkeypatch.setattr(meds, "MAX_MEDS", 1)
    assert answer.handle("MEDS 7am pill three", sender=EGYPT).text == answer.message("meds_full", "en")


def test_lao_medicine_is_spoken_in_thai(monkeypatch):
    import anthropic

    monkeypatch.setattr(answer, "settings", Settings(use_llm=True))
    monkeypatch.setattr(_FakeClaude, "reply", "ยาความดัน")
    monkeypatch.setattr(anthropic, "Anthropic", _FakeClaude)
    r = answer.handle("ຢາ 8am ຢາຄວາມດັນ", sender=LAOS)
    assert r.kind == "meds" and r.lang == "lo"
    (m,) = store.meds_of(LAOS)
    assert m.what == "ຢາຄວາມດັນ" and m.spoken == "ยาความดัน" and m.tz == "Asia/Vientiane"
    script, say_lang, voice = answer.call_voice("lo")
    assert say_lang == "th-TH" and script == meds.SCRIPT["th"]


def test_lao_without_ai_still_calls_without_the_name():
    answer.handle("MEDS 8am ຢາຄວາມດັນ", sender=LAOS)
    assert store.meds_of(LAOS)[0].spoken == ""


def test_language_without_voice_gets_sms_reminders():
    r = answer.handle("MEDS 8am dawa ya presha", sender="+254712345678")  # Swahili: no voice
    assert r.text.startswith(answer.message("meds_sms", "sw"))


def _due_now(number):
    """Move this person's next dose to now."""
    (d,) = [x for x in store.doses_to_try(time.time() + 3 * 86400)
            if store.med(x.med_id).number == number]
    store._run("UPDATE doses SET due = ?, next_try = ? WHERE id = ?", (time.time() - 1, time.time() - 1, d.id))
    return d.id


def test_call_press_1_confirms_and_plans_next_dose(monkeypatch):
    calls = []
    monkeypatch.setattr(twilio_sms, "place_call", lambda to, url: calls.append((to, url)))
    monkeypatch.setattr(appmod, "settings", LIVE)
    answer.handle("MEDS 8am 8pm blood pressure pill", sender=EGYPT)
    dose_id = _due_now(EGYPT)
    assert appmod.run_doses() == 1
    assert calls == [(EGYPT, f"https://ghost.example/voice/dose/{dose_id}")]

    c = TestClient(appmod.app)
    xml = c.post(f"/voice/dose/{dose_id}").text
    assert "<Gather" in xml and "blood pressure pill" in xml and 'language="arb"' not in xml  # English sender
    assert "Thank you" in c.post(f"/voice/answer/{dose_id}", data={"Digits": "1"}).text
    assert store.dose(dose_id).state == "confirmed"
    upcoming = store.doses_to_try(time.time() + 2 * 86400)
    assert len(upcoming) == 1 and upcoming[0].id != dose_id  # exactly one next dose


def test_arabic_call_uses_arabic_voice(monkeypatch):
    monkeypatch.setattr(twilio_sms, "place_call", lambda to, url: None)
    monkeypatch.setattr(appmod, "settings", LIVE)
    answer.handle("دواء 8am دواء الضغط", sender=EGYPT)
    dose_id = _due_now(EGYPT)
    appmod.run_doses()
    xml = TestClient(appmod.app).post(f"/voice/dose/{dose_id}").text
    assert 'language="arb"' in xml and "حان وقت الدواء" in xml and "دواء الضغط" in xml


def test_no_answer_retries_then_alerts_family(monkeypatch):
    calls, texts = [], []
    monkeypatch.setattr(twilio_sms, "place_call", lambda to, url: calls.append(to))
    monkeypatch.setattr(twilio_sms, "send_sms", lambda to, body: texts.append((to, body)))
    monkeypatch.setattr(appmod, "settings", LIVE)
    daughter = "+201009999999"
    r = answer.handle(f"MEDS FAMILY {daughter}", sender=EGYPT)
    assert r.kind == "family" and r.outbox and r.outbox[0][0] == daughter and EGYPT in r.outbox[0][1]
    assert answer.handle("YES", sender=daughter).kind == "family"
    answer.handle("MEDS 8am pill", sender=EGYPT)
    dose_id = _due_now(EGYPT)
    now = time.time()
    appmod.run_doses(now)  # first call
    appmod.run_doses(now + 5 * 60)  # too early for the retry
    appmod.run_doses(now + 11 * 60)  # second call
    assert calls == [EGYPT, EGYPT]
    appmod.run_doses(now + 22 * 60)  # no answer twice: tell the family
    assert store.dose(dose_id).state == "missed"
    assert len(texts) == 1 and texts[0][0] == daughter and EGYPT in texts[0][1] and "pill" in texts[0][1]


def test_family_only_after_yes(monkeypatch):
    texts = []
    monkeypatch.setattr(twilio_sms, "place_call", lambda to, url: None)
    monkeypatch.setattr(twilio_sms, "send_sms", lambda to, body: texts.append(to))
    monkeypatch.setattr(appmod, "settings", LIVE)
    answer.handle("MEDS FAMILY +201009999999", sender=EGYPT)  # never accepted
    answer.handle("MEDS 8am pill", sender=EGYPT)
    _due_now(EGYPT)
    for minutes in (0, 11, 22):
        appmod.run_doses(time.time() + minutes * 60)
    assert texts == []


def test_family_number_must_be_valid():
    assert answer.handle("MEDS FAMILY 12345", sender=EGYPT).text == answer.message("family_bad", "ar")
    assert answer.handle(f"MEDS FAMILY {EGYPT}", sender=EGYPT).text == answer.message("family_bad", "ar")


def test_texting_1_confirms_a_ringing_dose(monkeypatch):
    monkeypatch.setattr(twilio_sms, "place_call", lambda to, url: None)
    monkeypatch.setattr(appmod, "settings", LIVE)
    answer.handle("MEDS 8am pill", sender=EGYPT)
    dose_id = _due_now(EGYPT)
    appmod.run_doses()
    assert answer.handle("1", sender=EGYPT).text == answer.message("meds_taken", "ar")
    assert store.dose(dose_id).state == "confirmed"
    assert answer.handle("1", sender=EGYPT).kind != "meds"  # nothing ringing any more


def test_without_voice_the_reminder_is_an_sms(monkeypatch):
    texts = []
    monkeypatch.setattr(twilio_sms, "send_sms", lambda to, body: texts.append(body))
    monkeypatch.setattr(appmod, "settings", Settings(twilio_account_sid="AC1", twilio_from_number="+1",
                                                     twilio_auth_token="tok", voice_calls=False))
    answer.handle("MEDS 8am pill", sender=EGYPT)
    _due_now(EGYPT)
    assert appmod.run_doses() == 0
    assert texts and texts[0].startswith("MEDICINE TIME: pill") and "Reply 1" in texts[0]


def test_daily_call_cap(monkeypatch):
    calls = []
    monkeypatch.setattr(twilio_sms, "place_call", lambda to, url: calls.append(to))
    monkeypatch.setattr(twilio_sms, "send_sms", lambda to, body: None)
    monkeypatch.setattr(appmod, "settings", Settings(**{**LIVE.__dict__, "max_calls_per_day": 0}))
    answer.handle("MEDS 8am pill", sender=EGYPT)
    _due_now(EGYPT)
    assert appmod.run_doses() == 0 and calls == []


def test_stop_ends_medicine_calls():
    answer.handle("MEDS 8am pill", sender=EGYPT)
    answer.handle("STOP", sender=EGYPT)
    assert store.meds_of(EGYPT) == [] and store.doses_to_try(time.time() + 3 * 86400) == []


def test_simulator_phone_rings_and_press_1(monkeypatch):
    c = TestClient(appmod.app)
    c.post("/api/ask", json={"text": "MEDS 8am blood pressure pill", "country": "EG"})
    dose_id = _due_now("web:testclient")
    appmod.run_doses()
    calls = c.get("/api/inbox").json()["calls"]
    assert calls and calls[0]["dose"] == dose_id and "Press 1" in calls[0]["text"] and calls[0]["voice"] == "en-US"
    assert c.get("/api/inbox").json()["calls"] == []  # rings once
    assert c.post(f"/api/dose/{dose_id}/press", json={"digit": "1"}).json()["reply"] == "Thank you. Stay well."
    assert store.dose(dose_id).state == "confirmed"


def test_simulator_cannot_press_someone_elses_dose():
    answer.handle("MEDS 8am pill", sender=EGYPT)
    dose_id = _due_now(EGYPT)
    assert TestClient(appmod.app).post(f"/api/dose/{dose_id}/press", json={"digit": "1"}).status_code == 404


def test_voice_twiml_escapes_and_gathers():
    xml = twilio_sms.voice_twiml(["a < b"], "en-US", "Polly.Joanna", gather_action="/x?a=1&b=2")
    assert "a &lt; b" in xml and 'action="/x?a=1&amp;b=2"' in xml and re.search(r"<Gather[^>]+numDigits=\"1\"", xml)


def test_meds_in_one_minute_for_demos():
    r = answer.handle("MEDS in 1 min blood pressure pill", sender=EGYPT)
    assert r.kind == "meds"
    (d,) = store.doses_to_try(time.time() + 2 * 86400)
    assert 0 < d.due - time.time() <= 61
    assert store.meds_of(EGYPT)[0].what == "blood pressure pill"


def test_call_language_follows_the_country_when_the_text_shows_none():
    for number, expected in [("+8562055512345", "lo"), ("+919800000000", "hi"), ("+525500000000", "es")]:
        answer.handle("MEDS 8am losartan", sender=number)
        assert store.meds_of(number)[-1].lang == expected, number


def test_written_language_beats_the_country():
    answer.handle("MEDS 8am 8pm take the blood pressure pill", sender="+8562055500001")
    assert store.meds_of("+8562055500001")[-1].lang == "en"


def test_meds_lang_changes_the_call_language():
    answer.handle("MEDS 8am losartan", sender="+8562055500002")
    r = answer.handle("MEDS LANG en", sender="+8562055500002")
    assert r.lang == "en" and store.meds_of("+8562055500002")[-1].lang == "en"


def test_real_call_only_rings_listed_numbers(monkeypatch):
    c = TestClient(appmod.app)
    monkeypatch.setattr(appmod, "settings", dataclasses.replace(appmod.settings, demo_numbers=frozenset({"+8562055512345"})))
    assert c.post("/api/real-call", json={"number": "+8562099999999"}).status_code == 403
    r = c.post("/api/real-call", json={"number": "+856 20 5551 2345"})
    assert r.status_code == 200 and r.json()["lang"] == "lo"
    assert store.meds_of("+8562055512345")[-1].what == "test pill"


def test_real_call_off_without_list(monkeypatch):
    monkeypatch.setattr(appmod, "settings", dataclasses.replace(appmod.settings, demo_numbers=frozenset()))
    assert TestClient(appmod.app).post("/api/real-call", json={"number": "+8562055512345"}).status_code == 403
