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
    ollama_model_override: str = "",
) -> BaseLLMProvider:
    """
    Instantiate an LLM provider by name.

    Args:
        provider: provider name string
        settings: app settings
        ollama_model_override: use this model instead of settings.ollama_model
                               when provider is ollama. Falls back to ollama_model
                               if empty.
    """
    if provider == "ollama":
        from providers.llm.ollama import OllamaProvider
        model = ollama_model_override or settings.ollama_model
        logger.debug(f"[Factory] Building Ollama provider with model={model}")
        return OllamaProvider(model=model, base_url=settings.ollama_base_url)

    if provider == "groq":
        from providers.llm.groq import GroqProvider
        return GroqProvider(api_key=settings.groq_api_key, model=settings.groq_model)

    if provider == "openai":
        from providers.llm.openai import OpenAIProvider
        return OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model)

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


def get_llm_provider(settings: Settings) -> BaseLLMProvider:
    """
    Returns the default LLM provider.
    Used as the fallback when no step-specific provider is configured.
    """
    return _build_llm(settings.llm_provider, settings)


def get_query_analyzer_llm(settings: Settings) -> BaseLLMProvider:
    """
    Returns the LLM for Step 1: query analysis.
    Falls back to default LLM_PROVIDER if QUERY_ANALYZER_LLM_PROVIDER is not set.
    """
    provider = settings.query_analyzer_llm_provider or settings.llm_provider
    model_override = (
        settings.query_analyzer_ollama_model
        if provider == "ollama"
        else ""
    )
    logger.info(f"[Factory] Query analyzer: {provider}/{model_override or settings.ollama_model}")
    return _build_llm(provider, settings, ollama_model_override=model_override)


def get_extraction_llm(settings: Settings) -> BaseLLMProvider:
    """
    Returns the LLM for Step 4: entity extraction.
    Falls back to default LLM_PROVIDER if EXTRACTION_LLM_PROVIDER is not set.
    """
    provider = settings.extraction_llm_provider or settings.llm_provider
    model_override = (
        settings.extraction_ollama_model
        if provider == "ollama"
        else ""
    )
    logger.info(f"[Factory] Extraction LLM: {provider}/{model_override or settings.ollama_model}")
    return _build_llm(provider, settings, ollama_model_override=model_override)


def get_validator_llm(settings: Settings) -> BaseLLMProvider:
    """
    Returns the LLM for Step 7: post-extraction validation.
    Falls back to default LLM_PROVIDER if VALIDATOR_LLM_PROVIDER is not set.
    """
    provider = settings.validator_llm_provider or settings.llm_provider
    model_override = (
        settings.validator_ollama_model
        if provider == "ollama"
        else ""
    )
    logger.info(f"[Factory] Validator LLM: {provider}/{model_override or settings.ollama_model}")
    return _build_llm(provider, settings, ollama_model_override=model_override)


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