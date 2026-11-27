"""A language file that misses keys must not crash msg(): English fills the gaps."""

import logging

from ghost_signal import lang


def test_missing_key_falls_back_to_english_and_warns_once(monkeypatch, caplog):
    monkeypatch.setitem(lang.MESSAGES, "xx", {"help": "x-help"})
    monkeypatch.setattr(lang, "_warned", set())
    with caplog.at_level(logging.WARNING, logger="ghost_signal.lang"):
        assert lang.msg("help", "xx") == "x-help"  # present key still wins
        assert lang.msg("meds_set", "xx") == lang.MESSAGES["en"]["meds_set"]
        assert lang.msg("stopped", "xx") == lang.MESSAGES["en"]["stopped"]
    warnings = [r for r in caplog.records if "'xx'" in r.getMessage()]
    assert len(warnings) == 1
    assert "meds_set" in warnings[0].getMessage()


def test_unknown_language_is_english():
    assert lang.msg("help", "zz") == lang.MESSAGES["en"]["help"]
