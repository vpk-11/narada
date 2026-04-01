"""
config.py

Single source of truth for all Narada settings.
Every value is read from environment variables / .env file.
Nothing is hardcoded — no URLs, no keys, no model names.

Provider resolution order per step:
  1. Step-specific provider (e.g. QUERY_ANALYZER_LLM_PROVIDER)
  2. Falls back to LLM_PROVIDER if step-specific is not set

This means you can run everything on one model, or mix and match
any combination of local and cloud providers per step.
"""

import logging
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # ── Default provider — fallback for all steps ─────────────────────────── #
    llm_provider: str = "ollama"
    search_provider: str = "tavily"

    # ── Per-step LLM provider overrides ───────────────────────────────────── #
    # Leave empty to fall back to llm_provider for that step.
    query_analyzer_llm_provider: str = ""   # Step 1: query analysis
    extraction_llm_provider: str = ""       # Step 4: entity extraction
    validator_llm_provider: str = ""        # Step 7: post-extraction validation

    # ── Ollama ────────────────────────────────────────────────────────────── #
    ollama_base_url: str
    ollama_model: str                        # default Ollama model
    query_analyzer_ollama_model: str = ""   # override for query analysis step
    extraction_ollama_model: str = ""       # override for extraction step
    validator_ollama_model: str = ""        # override for validation step

    # ── Groq ──────────────────────────────────────────────────────────────── #
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
    return Settings()


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )