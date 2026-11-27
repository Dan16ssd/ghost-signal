"""REMIND: parsing in local time, storage, delivery."""

import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from hypothesis import HealthCheck, given, settings as hsettings, strategies as st

from ghost_signal import answer, app as appmod, reminders, store
from ghost_signal.config import Settings
from tests.test_answer_and_app import _FakeClaude, offline  # noqa: F401

VTE = ZoneInfo("Asia/Vientiane")
NOW = datetime(2026, 11, 27, 18, 0, tzinfo=VTE)  # Friday 18:00 in Laos


def test_parse_english_forms():
    assert reminders.parse("8pm take medicine", NOW) == (NOW.replace(hour=20), "take medicine")
    assert reminders.parse("take medicine at 8pm", NOW) == (NOW.replace(hour=20), "take medicine")
    assert reminders.parse("tomorrow 7:30am vaccine", NOW) == (
        NOW.replace(hour=7, minute=30) + timedelta(days=1), "vaccine")
    assert reminders.parse("in 2 hours call mum", NOW) == (NOW + timedelta(hours=2), "call mum")
    assert reminders.parse("in 15 min drink water", NOW) == (NOW + timedelta(minutes=15), "drink water")
    assert reminders.parse("pills at 21:00", NOW) == (NOW.replace(hour=21), "pills")


def test_past_time_today_means_tomorrow():
    due, _ = reminders.parse("7am feed the buffalo", NOW)
    assert due == NOW.replace(hour=7) + timedelta(days=1)


def test_no_time_or_no_task():
    assert reminders.parse("take medicine", NOW) is None
    assert reminders.parse("8pm", NOW) is None
    assert reminders.parse("13pm eat", NOW) is None
    assert reminders.parse("at 25:00 eat", NOW) is None


@hsettings(suppress_health_check=[HealthCheck.too_slow], deadline=None)  # a Windows pause is not a bug
@given(
    hour=st.integers(1, 12),
    minute=st.integers(0, 59),
    ampm=st.sampled_from(["am", "pm"]),
    offset=st.integers(0, 2 * 365 * 24 * 60),
    zone=st.sampled_from(["Asia/Vientiane", "Africa/Cairo", "America/New_York", "Asia/Kolkata"]),
)
def test_clock_times_are_always_in_the_next_24_hours(hour, minute, ampm, offset, zone):
    # A real clock reading: walk in UTC, then show it in the zone (never a time skipped by DST).
    now = (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=offset)).astimezone(ZoneInfo(zone))
    due, what = reminders.parse(f"{hour}:{minute:02d}{ampm} eat rice", now)
    assert what == "eat rice"
    assert now.timestamp() < due.timestamp() <= now.timestamp() + 25 * 3600  # 25 h: DST autumn day
    assert due.hour == hour % 12 + (12 if ampm == "pm" else 0) and due.minute == minute


def test_ai_reply_parsing():
    reply = '{"when": "2026-11-28T20:00", "what": "الدواء"}'
    assert reminders.parse_ai_reply(reply, NOW) == (datetime(2026, 11, 28, 20, 0, tzinfo=VTE), "الدواء")
    assert reminders.parse_ai_reply("NONE", NOW) is None
    assert reminders.parse_ai_reply("{bad json", NOW) is None
    assert reminders.parse_ai_reply(None, NOW) is None


def test_range():
    assert not reminders.in_range(NOW - timedelta(minutes=1), NOW)
    assert reminders.in_range(NOW + timedelta(hours=1), NOW)
    assert not reminders.in_range(NOW + timedelta(days=31), NOW)


def test_remind_command_uses_sender_time_zone():
    r = answer.handle("REMIND in 1 hour take medicine", sender="+8562055512345")
    assert r.kind == "remind" and "take medicine" in r.text and "UTC" not in r.text
    items = store.waiting("+8562055512345")
    assert len(items) == 1 and abs(items[0].due - (time.time() + 3600)) < 5


def test_unknown_country_says_utc():
    assert "UTC" in answer.handle("REMIND in 1 hour x", sender="web:1.2.3.4").text


def test_list_delete_and_limit(monkeypatch):
    n = "+201001234567"
    assert answer.handle("REMIND LIST", sender=n).text == answer.message("reminder_none", "ar")
    answer.handle("REMIND in 1 hour first", sender=n)
    answer.handle("REMIND in 2 hours second", sender=n)
    listed = answer.handle("remind list", sender=n).text
    assert "1)" in listed and "first" in listed and "second" in listed
    assert "second" in answer.handle("REMIND DEL 2", sender=n).text
    assert [x.what for x in store.waiting(n)] == ["first"]
    monkeypatch.setattr(answer, "settings", Settings(use_llm=False, max_reminders=1))
    assert answer.handle("REMIND in 3 hours third", sender=n).text == answer.message("reminder_full", "en")


def test_bad_time_explains_how():
    assert answer.handle("REMIND someday maybe", sender="+1555").text == answer.message("reminder_bad", "en")


def test_arabic_reminder_through_ai(monkeypatch):
    import anthropic

    monkeypatch.setattr(answer, "settings", Settings(use_llm=True))
    tomorrow = (datetime.now(ZoneInfo("Africa/Cairo")) + timedelta(days=1)).strftime("%Y-%m-%d")
    monkeypatch.setattr(_FakeClaude, "reply", '{"when": "' + tomorrow + 'T20:00", "what": "الدواء"}')
    monkeypatch.setattr(anthropic, "Anthropic", _FakeClaude)
    r = answer.handle("ذكرني غدا الساعة 8 مساء بالدواء", sender="+201001234567")
    assert r.kind == "remind" and r.lang == "ar" and f"{tomorrow} 20:00" in r.text


def test_delivery_to_web_inbox_and_phones(monkeypatch):
    sent = []
    monkeypatch.setattr(appmod.twilio_sms, "send_sms", lambda to, body: sent.append((to, body)))
    monkeypatch.setattr(
        appmod, "settings", Settings(twilio_account_sid="AC1", twilio_auth_token="t", twilio_from_number="+1")
    )
    store.add_reminder("web:9.9.9.9", 0, "drink water", "en", "now")
    store.add_reminder("+254712345678", 0, "vaccine day", "en", "now")
    store.add_reminder("+254700000000", time.time() + 999, "later", "en", "later")
    assert appmod.deliver_due_reminders() == 1
    assert sent == [("+254712345678", "REMINDER: vaccine day")]
    assert [r.what for r in store.inbox("web:9.9.9.9")] == ["drink water"]
    assert store.inbox("web:9.9.9.9") == []  # delivered once
    assert appmod.deliver_due_reminders() == 0  # nothing sent twice
