"""
api/routes.py

Narada API routes.

Endpoints:
  POST /api/search      — run the pipeline for a query
  GET  /api/search      — same, for quick browser/Postman testing
  DELETE /api/cache     — clear all cached results
  GET  /api/providers   — list available and active providers
"""

import logging

from fastapi import APIRouter, HTTPException, Query
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

@router.post("/search", response_model=PipelineResult)
async def search_post(body: SearchRequest) -> PipelineResult:
    """
    Run the Narada pipeline for a query.
    Returns a structured table of entities with source-traced attributes.
    Set refresh=true to bypass cache and force a fresh run.
    """
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query cannot be empty")

    settings = get_settings()
    llm = get_llm_provider(settings)
    extraction_llm = get_extraction_llm_provider(settings)
    search = get_search_provider(settings)

    try:
        return await run_pipeline(
            query=query,
            settings=settings,
            llm=llm,
            search=search,
            extraction_llm=extraction_llm,
            use_cache=not body.refresh,
        )
    except Exception as e:
        logger.error(f"[Routes] Pipeline failed for '{query}': {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@router.get("/search", response_model=PipelineResult)
async def search_get(
    query: str = Query(..., description="Research query"),
    refresh: bool = Query(False, description="Bypass cache and force fresh run"),
) -> PipelineResult:
    """
    GET version of /search — convenient for browser and Postman testing.
    Example: GET /api/search?query=AI+startups+in+healthcare
    """
    query = query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query cannot be empty")

    settings = get_settings()
    llm = get_llm_provider(settings)
    extraction_llm = get_extraction_llm_provider(settings)
    search = get_search_provider(settings)

    try:
        return await run_pipeline(
            query=query,
            settings=settings,
            llm=llm,
            search=search,
            extraction_llm=extraction_llm,
            use_cache=not refresh,
        )
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
async def list_providers() -> ProvidersResponse:
    """Return active provider config and available options."""
    settings = get_settings()
    llm = get_llm_provider(settings)
    extraction_llm = get_extraction_llm_provider(settings) or llm
    search = get_search_provider(settings)

    return ProvidersResponse(
        active_llm_provider=llm.provider_name,
        active_llm_model=llm.model_name,
        active_extraction_llm_provider=extraction_llm.provider_name,
        active_extraction_llm_model=extraction_llm.model_name,
        active_search_provider=search.provider_name,
        available_llm_providers=["ollama", "groq", "openai", "anthropic"],
        available_search_providers=["duckduckgo", "brave", "tavily"],
    )