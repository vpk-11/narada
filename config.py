"""
config.py

Single source of truth for all Narada settings.
Every value is read from environment variables / .env file.
Nothing is hardcoded here — no URLs, no keys, no model names.

To change providers or tune the pipeline: edit .env only.
"""

import logging
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # ── Provider selection ────────────────────────────────────────────────── #
    llm_provider: str = "ollama"            # ollama | groq | openai | anthropic
    search_provider: str = "duckduckgo"     # duckduckgo | brave | tavily

    # ── Multi-model: optional separate provider for extraction step ───────── #
    # If set, extraction uses this provider. All other steps use llm_provider.
    # Example: llm_provider=ollama, extraction_llm_provider=groq
    extraction_llm_provider: str = ""       # leave empty to use llm_provider for all steps

    # ── Ollama ────────────────────────────────────────────────────────────── #
    ollama_base_url: str
    ollama_model: str

    # ── Groq (free, fast, recommended for extraction) ─────────────────────── #
    groq_api_key: str = ""
    groq_model: str = ""

    # ── OpenAI ────────────────────────────────────────────────────────────── #
    openai_api_key: str = ""
    openai_model: str = ""

    # ── Anthropic ─────────────────────────────────────────────────────────── #
    anthropic_api_key: str = ""
    anthropic_model: str = ""

    # ── Brave ─────────────────────────────────────────────────────────────── #
    brave_api_key: str = ""

    # ── Tavily ────────────────────────────────────────────────────────────── #
    tavily_api_key: str = ""

    # ── Pipeline tuning ───────────────────────────────────────────────────── #
    search_results_per_query: int = 8
    max_pages_to_scrape: int = 6
    scrape_timeout_seconds: int = 10

    # ── Logging ───────────────────────────────────────────────────────────── #
    log_level: str = "INFO"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    Use this everywhere instead of instantiating Settings() directly.
    """
    return Settings()


def configure_logging(settings: Settings) -> None:
    """Set up root logger from settings."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )