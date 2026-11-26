"""Property-based tests for SMS length rules (Hypothesis)."""

from hypothesis import given, settings
from hypothesis import strategies as st

from ghost_signal import sms

LAO = st.characters(min_codepoint=0x0E81, max_codepoint=0x0EDF)
TEXT = st.text(
    alphabet=st.one_of(st.sampled_from(sms.GSM7_BASIC + sms.GSM7_EXTENDED), LAO, st.characters()),
    max_size=1200,
)


def test_known_lengths():
    assert sms.segments("") == 0
    assert sms.segments("a" * 160) == 1
    assert sms.segments("a" * 161) == 2
    assert sms.segments("ກ" * 70) == 1
    assert sms.segments("ກ" * 71) == 2
    assert sms.encoding("hello") == "GSM-7"
    assert sms.encoding("ສະບາຍດີ") == "UCS-2"
    assert sms.units("{}") == 4  # extended chars cost two


@settings(max_examples=300)
@given(TEXT, st.integers(min_value=1, max_value=5))
def test_fit_always_fits(text, n):
    assert sms.segments(sms.fit(text, n)) <= n


@given(TEXT, st.integers(min_value=1, max_value=5))
def test_fit_keeps_short_text_unchanged(text, n):
    if sms.segments(text.strip()) <= n:
        assert sms.fit(text, n) == text.strip()


@given(TEXT, st.integers(min_value=1, max_value=5))
def test_fit_is_prefix_with_mark(text, n):
    out = sms.fit(text, n)
    if out != text.strip():
        assert out.endswith("...")
        assert text.strip().startswith(out[:-3].rstrip())


@given(TEXT)
def test_more_text_never_needs_fewer_segments(text):
    assert sms.segments(text + "x") >= sms.segments(text) or not sms.is_gsm7(text)
