"""
providers/factory.py

Builds provider instances from settings.

LLM resolution order per step:
  1. Step-specific model (e.g. QUERY_ANALYZER_MODEL)
  2. Falls back to LLM_MODEL if not set

Model strings use LiteLLM format: provider/model-name
The prefix determines which API key and base URL to use.
"""

import logging

from config import Settings
from providers.base import BaseLLMProvider, BaseSearchProvider

logger = logging.getLogger(__name__)

_OLLAMA_PREFIXES = ("ollama", "ollama_chat")


def _build_llm(model: str, settings: Settings) -> BaseLLMProvider:
    if not model:
        raise ValueError(
            "LLM model is not configured. Set LLM_MODEL in .env "
            "(e.g. LLM_MODEL=groq/llama-3.3-70b-versatile)."
        )

    from providers.llm.litellm_provider import LiteLLMProvider

    prefix = model.split("/")[0].lower() if "/" in model else ""
    api_key = ""
    api_base = ""

    if prefix == "groq":
        api_key = settings.groq_api_key
    elif prefix == "openai":
        api_key = settings.openai_api_key
    elif prefix == "anthropic":
        api_key = settings.anthropic_api_key
    elif prefix in _OLLAMA_PREFIXES:
        api_base = settings.ollama_base_url

    logger.debug(f"[Factory] Building LiteLLM provider: {model}")
    return LiteLLMProvider(model=model, api_key=api_key, api_base=api_base)


def get_llm_provider(settings: Settings) -> BaseLLMProvider:
    return _build_llm(settings.llm_model, settings)


def get_query_analyzer_llm(settings: Settings) -> BaseLLMProvider:
    model = settings.query_analyzer_model or settings.llm_model
    logger.info(f"[Factory] Query analyzer: {model}")
    return _build_llm(model, settings)


def get_extraction_llm(settings: Settings) -> BaseLLMProvider:
    model = settings.extraction_model or settings.llm_model
    logger.info(f"[Factory] Extraction LLM: {model}")
    return _build_llm(model, settings)


def get_validator_llm(settings: Settings) -> BaseLLMProvider:
    model = settings.validator_model or settings.llm_model
    logger.info(f"[Factory] Validator LLM: {model}")
    return _build_llm(model, settings)


def get_search_provider(settings: Settings) -> BaseSearchProvider:
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
