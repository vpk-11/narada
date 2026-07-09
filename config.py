"""
config.py

Single source of truth for all Narada settings.
Every value is read from environment variables / .env file.

LLM model strings use LiteLLM format: provider/model-name
  groq/llama-3.3-70b-versatile
  openai/gpt-4o-mini
  anthropic/claude-haiku-4-5-20251001
  ollama/qwen3:4b

Per-step overrides follow the same format. Leave empty to use llm_model for all steps.
"""

import logging
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # ── Default LLM — full LiteLLM model string ───────────────────────────── #
    llm_model: str = "ollama/qwen3:4b"
    search_provider: str = "tavily"

    # ── Per-step LLM overrides ────────────────────────────────────────────── #
    # Leave empty to fall back to llm_model for that step.
    query_analyzer_model: str = ""   # Step 1: query analysis
    extraction_model: str = ""       # Step 4: entity extraction
    validator_model: str = ""        # Step 6: post-extraction validation

    # ── Ollama ────────────────────────────────────────────────────────────── #
    ollama_base_url: str = "http://localhost:11434"

    # ── API Keys ──────────────────────────────────────────────────────────── #
    groq_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    brave_api_key: str = ""
    tavily_api_key: str = ""

    # ── Pipeline tuning ───────────────────────────────────────────────────── #
    search_results_per_query: int = 8
    max_pages_to_scrape: int = 6
    scrape_timeout_seconds: int = 10
    # Hard cap on pipeline runs executing at once, server-wide. Protects the
    # server's own configured keys from an unthrottled pile of concurrent
    # requests — separate from the per-IP rate limit in api/routes.py, which
    # only throttles one client, not total server load.
    max_concurrent_pipeline_runs: int = 5

    # ── Agentic gap-filling ───────────────────────────────────────────────── #
    # After validation, if more than this fraction of cells are empty, the
    # pipeline generates follow-up search queries and runs another round.
    agent_gap_threshold: float = 0.5
    # Hard cap on gap-filling rounds. 1 = no re-search, the loop only ever
    # runs the first pass. Each additional round costs a query-gen LLM call
    # plus a full search+scrape+extract round.
    agent_max_iterations: int = 2

    # Allow the frontend to use server-side keys as a fallback when the user
    # has not provided their own keys (production only).
    fallback_allow: bool = False

    # Optional admin key for DELETE /api/cache. When set, the x-admin-key
    # header must match. Leave empty to allow unauthenticated cache clears.
    cache_admin_key: str = ""

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
