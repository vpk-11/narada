"""
api/routes.py

Narada API routes.

REST conventions:
  POST /api/search      — run the pipeline for a query (triggers work, always POST)
  DELETE /api/cache     — clear all cached results
  GET  /api/providers   — retrieve active provider config (read-only, GET is correct)
  GET  /api/health      — liveness check (read-only, GET is correct)
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import get_settings
from core.cache import clear_cache
from core.models import PipelineResult
from core.pipeline import run_pipeline
from providers.factory import get_extraction_llm_provider, get_llm_provider, get_search_provider

logger = logging.getLogger(__name__)
router = APIRouter()


# --------------------------------------------------------------------------- #
# Request / Response shapes
# --------------------------------------------------------------------------- #

class SearchRequest(BaseModel):
    query: str
    refresh: bool = False  # set True to bypass cache and force a fresh run


class SearchResponse(BaseModel):
    """Wraps PipelineResult — room to add pagination or request metadata later."""
    result: PipelineResult


class CacheClearResponse(BaseModel):
    deleted: int
    message: str


class ProvidersResponse(BaseModel):
    active_llm_provider: str
    active_llm_model: str
    active_extraction_llm_provider: str
    active_extraction_llm_model: str
    active_search_provider: str
    available_llm_providers: list[str]
    available_search_providers: list[str]


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #

@router.post("/search", response_model=SearchResponse)
async def search(body: SearchRequest) -> SearchResponse:
    """
    Run the Narada pipeline for a query.

    Returns a structured table of entities with source-traced attributes.
    Results are cached — identical queries return instantly on repeat calls.
    Set refresh=true to bypass cache and force a fresh pipeline run.
    """
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query cannot be empty")

    settings = get_settings()
    llm = get_llm_provider(settings)
    extraction_llm = get_extraction_llm_provider(settings)
    search_provider = get_search_provider(settings)

    try:
        result = await run_pipeline(
            query=query,
            settings=settings,
            llm=llm,
            search=search_provider,
            extraction_llm=extraction_llm,
            use_cache=not body.refresh,
        )
        return SearchResponse(result=result)

    except Exception as e:
        logger.error(f"[Routes] Pipeline failed for '{query}': {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@router.delete("/cache", response_model=CacheClearResponse)
async def delete_cache() -> CacheClearResponse:
    """
    Clear all cached pipeline results.
    Use when you want fresh results for previously cached queries.
    """
    deleted = clear_cache()
    return CacheClearResponse(
        deleted=deleted,
        message=f"Cleared {deleted} cached result(s)",
    )


@router.get("/providers", response_model=ProvidersResponse)
async def get_providers() -> ProvidersResponse:
    """
    Return active provider config and available options.
    Read-only — confirms which models and search provider are in use.
    """
    settings = get_settings()
    llm = get_llm_provider(settings)
    extraction_llm = get_extraction_llm_provider(settings) or llm
    search_provider = get_search_provider(settings)

    return ProvidersResponse(
        active_llm_provider=llm.provider_name,
        active_llm_model=llm.model_name,
        active_extraction_llm_provider=extraction_llm.provider_name,
        active_extraction_llm_model=extraction_llm.model_name,
        active_search_provider=search_provider.provider_name,
        available_llm_providers=["ollama", "groq", "openai", "anthropic"],
        available_search_providers=["duckduckgo", "brave", "tavily"],
    )