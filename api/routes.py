"""
api/routes.py

Narada API routes.

REST conventions:
  POST /api/search      — run the pipeline (triggers work, always POST)
  DELETE /api/cache     — clear all cached results
  GET  /api/providers   — retrieve active provider config (read-only)
  GET  /health          — liveness check (on root app, not router)
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import get_settings
from core.cache import clear_cache
from core.models import PipelineResult
from core.pipeline import run_pipeline
from providers.factory import (
    get_extraction_llm,
    get_query_analyzer_llm,
    get_search_provider,
    get_validator_llm,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# --------------------------------------------------------------------------- #
# Request / Response shapes
# --------------------------------------------------------------------------- #

class SearchRequest(BaseModel):
    query: str
    refresh: bool = False


class SearchResponse(BaseModel):
    result: PipelineResult


class CacheClearResponse(BaseModel):
    deleted: int
    message: str


class ProviderInfo(BaseModel):
    provider: str
    model: str


class ProvidersResponse(BaseModel):
    default: ProviderInfo
    query_analyzer: ProviderInfo
    extractor: ProviderInfo
    validator: ProviderInfo
    search: str
    available_llm_providers: list[str]
    available_search_providers: list[str]


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #

@router.post("/search", response_model=SearchResponse)
async def search(body: SearchRequest) -> SearchResponse:
    """
    Run the Narada pipeline for a query.
    Results are cached — identical queries return instantly on repeat calls.
    Set refresh=true to bypass cache and force a fresh run.
    """
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query cannot be empty")

    settings = get_settings()
    search_provider = get_search_provider(settings)

    try:
        result = await run_pipeline(
            query=query,
            settings=settings,
            search=search_provider,
            use_cache=not body.refresh,
        )
        return SearchResponse(result=result)

    except Exception as e:
        logger.error(f"[Routes] Pipeline failed for '{query}': {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@router.delete("/cache", response_model=CacheClearResponse)
async def delete_cache() -> CacheClearResponse:
    """Clear all cached pipeline results."""
    deleted = clear_cache()
    return CacheClearResponse(
        deleted=deleted,
        message=f"Cleared {deleted} cached result(s)",
    )


@router.get("/providers", response_model=ProvidersResponse)
async def get_providers() -> ProvidersResponse:
    """
    Return active provider config per pipeline step.
    Shows which model is used for each step and what the fallback is.
    """
    settings = get_settings()

    from providers.factory import get_llm_provider
    default = get_llm_provider(settings)
    analyzer = get_query_analyzer_llm(settings)
    extractor = get_extraction_llm(settings)
    validator = get_validator_llm(settings)
    search = get_search_provider(settings)

    return ProvidersResponse(
        default=ProviderInfo(provider=default.provider_name, model=default.model_name),
        query_analyzer=ProviderInfo(provider=analyzer.provider_name, model=analyzer.model_name),
        extractor=ProviderInfo(provider=extractor.provider_name, model=extractor.model_name),
        validator=ProviderInfo(provider=validator.provider_name, model=validator.model_name),
        search=search.provider_name,
        available_llm_providers=["ollama", "groq", "openai", "anthropic"],
        available_search_providers=["duckduckgo", "brave", "tavily"],
    )