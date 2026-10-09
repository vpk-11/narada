"""providers/factory.py picks the right key for each LiteLLM prefix."""

from config import Settings
from providers.factory import get_llm_provider


def test_gemini_prefix_uses_gemini_key():
    s = Settings(llm_model="gemini/gemini-2.5-flash-lite", gemini_api_key="g", groq_api_key="x")
    assert get_llm_provider(s)._api_key == "g"


def test_groq_prefix_uses_groq_key():
    s = Settings(llm_model="groq/openai/gpt-oss-20b", gemini_api_key="g", groq_api_key="x")
    assert get_llm_provider(s)._api_key == "x"
