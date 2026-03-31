"""
providers/factory.py

Builds the correct provider instances from settings.
The rest of the codebase calls these functions and never imports
concrete implementations directly.

Adding a new provider: implement the base class, register it here.
"""

from config import Settings
from providers.base import BaseLLMProvider, BaseSearchProvider


def get_llm_provider(settings: Settings, provider_override: str = "") -> BaseLLMProvider:
    """
    Instantiate and return the configured LLM provider.
    provider_override lets the pipeline request a specific provider
    for a specific step (e.g. extraction_llm_provider).
    """
    provider = provider_override or settings.llm_provider

    if provider == "ollama":
        from providers.llm.ollama import OllamaProvider
        return OllamaProvider(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
        )

    if provider == "groq":
        from providers.llm.groq import GroqProvider
        return GroqProvider(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
        )

    if provider == "openai":
        from providers.llm.openai import OpenAIProvider
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )

    if provider == "anthropic":
        from providers.llm.anthropic import AnthropicProvider
        return AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
        )

    raise ValueError(
        f"Unknown LLM provider: '{provider}'. "
        "Valid options: ollama | groq | openai | anthropic"
    )


def get_extraction_llm_provider(settings: Settings) -> BaseLLMProvider | None:
    """
    Returns a separate LLM provider for the extraction step, if configured.
    Returns None if extraction_llm_provider is not set — pipeline uses default.
    """
    if not settings.extraction_llm_provider:
        return None
    return get_llm_provider(settings, provider_override=settings.extraction_llm_provider)


def get_search_provider(settings: Settings) -> BaseSearchProvider:
    """Instantiate and return the configured search provider."""

    if settings.search_provider == "duckduckgo":
        from providers.search.duckduckgo import DuckDuckGoProvider
        return DuckDuckGoProvider()

    if settings.search_provider == "brave":
        from providers.search.brave import BraveProvider
        return BraveProvider(api_key=settings.brave_api_key)

    if settings.search_provider == "tavily":
        from providers.search.tavily import TavilyProvider
        return TavilyProvider(api_key=settings.tavily_api_key)

    raise ValueError(
        f"Unknown search provider: '{settings.search_provider}'. "
        "Valid options: duckduckgo | brave | tavily"
    )