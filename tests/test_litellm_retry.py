"""LLM retry wait honors the provider's retry hint."""

from providers.llm.litellm_provider import _retry_after_seconds


def test_groq_seconds():
    msg = "Rate limit reached ... Requested 2867. Please try again in 8.22s. Need more"
    assert _retry_after_seconds(msg) == 8.22


def test_gemini_seconds():
    assert _retry_after_seconds("RESOURCE_EXHAUSTED. Please retry in 34.5s.") == 34.5


def test_minutes_and_seconds():
    assert _retry_after_seconds("Please try again in 1m5.5s.") == 65.5


def test_milliseconds():
    assert _retry_after_seconds("Please try again in 850ms.") == 0.85


def test_no_hint():
    assert _retry_after_seconds("connection reset") is None
