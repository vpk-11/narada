"""LLM retry wait honors the provider's 'try again in Ns' hint."""

from providers.llm.litellm_provider import _RETRY_AFTER_RE


def test_retry_after_parsed_from_groq_message():
    msg = "Rate limit reached ... Limit 8000, Used 6229, Requested 2867. Please try again in 8.22s. Need more"
    assert float(_RETRY_AFTER_RE.search(msg).group(1)) == 8.22


def test_no_hint_no_match():
    assert _RETRY_AFTER_RE.search("connection reset") is None
