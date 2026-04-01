"""
providers/factory.py

Builds the correct provider instances from settings.

Resolution order for every step-specific provider:
  1. Step-specific provider env var (e.g. QUERY_ANALYZER_LLM_PROVIDER)
  2. Falls back to LLM_PROVIDER if not set

For Ollama specifically, each step can also use a different model:
  1. Step-specific model (e.g. QUERY_ANALYZER_OLLAMA_MODEL)
  2. Falls back to OLLAMA_MODEL if not set
"""

import logging

from config import Settings
from providers.base import BaseLLMProvider, BaseSearchProvider

logger = logging.getLogger(__name__)


def _build_llm(
    provider: str,
    settings: Settings,
    model_override: str = "",
) -> BaseLLMProvider:
    """
    Instantiate an LLM provider by name.

    Args:
        provider: provider name string
        settings: app settings
        model_override: use this model regardless of provider type.
                        Falls back to provider-specific default if empty.
    """
    if provider == "ollama":
        from providers.llm.ollama import OllamaProvider
        model = model_override or settings.ollama_model
        logger.debug(f"[Factory] Building Ollama provider with model={model}")
        return OllamaProvider(model=model, base_url=settings.ollama_base_url)

    if provider == "groq":
        from providers.llm.groq import GroqProvider
        model = model_override or settings.groq_model
        return GroqProvider(api_key=settings.groq_api_key, model=model)

    if provider == "openai":
        from providers.llm.openai import OpenAIProvider
        model = model_override or settings.openai_model
        return OpenAIProvider(api_key=settings.openai_api_key, model=model)

    if provider == "anthropic":
        from providers.llm.anthropic import AnthropicProvider
        model = model_override or settings.anthropic_model
        return AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=model,
        )

    raise ValueError(
        f"Unknown LLM provider: '{provider}'. "
        "Valid options: ollama | groq | openai | anthropic"
    )


def get_llm_provider(settings: Settings) -> BaseLLMProvider:
    """
    Returns the default LLM provider.
    Used as the fallback when no step-specific provider is configured.
    """
    return _build_llm(settings.llm_provider, settings)


def _get_step_model_override(provider: str, settings: Settings, step: str) -> str:
    """
    Get the model override for a specific step and provider combination.
    Returns empty string if no override is set -- _build_llm will use the default.
    """
    if provider == "ollama":
        return {
            "query_analyzer": settings.query_analyzer_ollama_model,
            "extractor": settings.extraction_ollama_model,
            "validator": settings.validator_ollama_model,
        }.get(step, "")
    return ""


def get_query_analyzer_llm(settings: Settings) -> BaseLLMProvider:
    """LLM for Step 1: query analysis. Falls back to LLM_PROVIDER."""
    provider = settings.query_analyzer_llm_provider or settings.llm_provider
    model = _get_step_model_override(provider, settings, "query_analyzer")
    logger.info(f"[Factory] Query analyzer: {provider}/{model or '(default)'}")
    return _build_llm(provider, settings, model_override=model)


def get_extraction_llm(settings: Settings) -> BaseLLMProvider:
    """LLM for Step 4: entity extraction. Falls back to LLM_PROVIDER."""
    provider = settings.extraction_llm_provider or settings.llm_provider
    model = _get_step_model_override(provider, settings, "extractor")
    logger.info(f"[Factory] Extraction LLM: {provider}/{model or '(default)'}")
    return _build_llm(provider, settings, model_override=model)


def get_validator_llm(settings: Settings) -> BaseLLMProvider:
    """LLM for Step 6: post-extraction validation. Falls back to LLM_PROVIDER."""
    provider = settings.validator_llm_provider or settings.llm_provider
    model = _get_step_model_override(provider, settings, "validator")
    logger.info(f"[Factory] Validator LLM: {provider}/{model or '(default)'}")
    return _build_llm(provider, settings, model_override=model)


def get_search_provider(settings: Settings) -> BaseSearchProvider:
    """Returns the configured search provider."""
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
