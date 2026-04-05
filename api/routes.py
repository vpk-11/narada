"""
api/routes.py

Narada API routes.

Security model:
- User API keys are sent as custom request headers, not in the body.
  Headers are excluded from most access logs by default.
- Keys are used for the duration of one request and discarded.
  Nothing is written to disk, database, or logs.
- Request bodies are never logged — only query string and status codes.
- CORS is locked to the configured frontend origin on production.
- CSP headers prevent XSS from stealing keys out of sessionStorage.
"""

import logging
import os

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config import Settings, get_settings
from core.cache import clear_cache
from core.models import PipelineResult
from core.pipeline import run_pipeline
from providers.base import BaseLLMProvider, BaseSearchProvider
from providers.factory import (
    get_extraction_llm,
    get_query_analyzer_llm,
    get_search_provider,
    get_validator_llm,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Header names for per-request key injection
# Using X- prefix signals non-standard headers to proxies and log scrapers
_H_GROQ_KEY        = "x-groq-api-key"
_H_OPENAI_KEY      = "x-openai-api-key"
_H_ANTHROPIC_KEY   = "x-anthropic-api-key"
_H_TAVILY_KEY      = "x-tavily-api-key"
_H_BRAVE_KEY       = "x-brave-api-key"
_H_OLLAMA_URL      = "x-ollama-base-url"
_H_SEARCH_PROVIDER = "x-search-provider"
_H_QA_PROVIDER     = "x-query-analyzer-provider"
_H_QA_MODEL        = "x-query-analyzer-model"
_H_EX_PROVIDER     = "x-extractor-provider"
_H_EX_MODEL        = "x-extractor-model"
_H_VA_PROVIDER     = "x-validator-provider"
_H_VA_MODEL        = "x-validator-model"


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
# Settings builder from headers
# --------------------------------------------------------------------------- #

def _build_settings_from_headers(request: Request, base: Settings) -> Settings:
    """
    Build a Settings instance with per-request overrides from headers.

    Only non-empty header values override the base settings.
    The returned object is used for this request only -- never persisted.

    Keys are read from headers, not logged, not stored.
    """
    h = request.headers
    overrides: dict = {}

    # API keys
    if h.get(_H_GROQ_KEY):
        overrides["groq_api_key"] = h[_H_GROQ_KEY]
    if h.get(_H_OPENAI_KEY):
        overrides["openai_api_key"] = h[_H_OPENAI_KEY]
    if h.get(_H_ANTHROPIC_KEY):
        overrides["anthropic_api_key"] = h[_H_ANTHROPIC_KEY]
    if h.get(_H_TAVILY_KEY):
        overrides["tavily_api_key"] = h[_H_TAVILY_KEY]
    if h.get(_H_BRAVE_KEY):
        overrides["brave_api_key"] = h[_H_BRAVE_KEY]
    if h.get(_H_OLLAMA_URL):
        overrides["ollama_base_url"] = h[_H_OLLAMA_URL]

    # Provider selection
    if h.get(_H_SEARCH_PROVIDER):
        overrides["search_provider"] = h[_H_SEARCH_PROVIDER]
    if h.get(_H_QA_PROVIDER):
        overrides["query_analyzer_llm_provider"] = h[_H_QA_PROVIDER]
    if h.get(_H_QA_MODEL):
        overrides["query_analyzer_ollama_model"] = h[_H_QA_MODEL]
        overrides["query_analyzer_groq_model"] = h[_H_QA_MODEL]
        overrides["query_analyzer_openai_model"] = h[_H_QA_MODEL]
        overrides["query_analyzer_anthropic_model"] = h[_H_QA_MODEL]
    if h.get(_H_EX_PROVIDER):
        overrides["extraction_llm_provider"] = h[_H_EX_PROVIDER]
    if h.get(_H_EX_MODEL):
        overrides["extraction_ollama_model"] = h[_H_EX_MODEL]
        overrides["extraction_groq_model"] = h[_H_EX_MODEL]
        overrides["extraction_openai_model"] = h[_H_EX_MODEL]
        overrides["extraction_anthropic_model"] = h[_H_EX_MODEL]
    if h.get(_H_VA_PROVIDER):
        overrides["validator_llm_provider"] = h[_H_VA_PROVIDER]
    if h.get(_H_VA_MODEL):
        overrides["validator_ollama_model"] = h[_H_VA_MODEL]
        overrides["validator_groq_model"] = h[_H_VA_MODEL]
        overrides["validator_openai_model"] = h[_H_VA_MODEL]
        overrides["validator_anthropic_model"] = h[_H_VA_MODEL]

    if not overrides:
        return base

    return base.model_copy(update=overrides)


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #

@router.post("/search", response_model=SearchResponse)
async def search(body: SearchRequest, request: Request) -> SearchResponse:
    """
    Run the Narada pipeline for a query.

    API keys are read from request headers (x-groq-api-key etc).
    Keys override .env for this call only and are never stored.
    Set refresh=true to bypass cache and force a fresh run.
    """
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query cannot be empty")

    base_settings = get_settings()

    try:
        settings = _build_settings_from_headers(request, base_settings)
        search_provider = get_search_provider(settings)
        result = await run_pipeline(
            query=query,
            settings=settings,
            search=search_provider,
            use_cache=not body.refresh,
        )
        return SearchResponse(result=result)

    except ValueError as e:
        # Config/validation errors (missing key, unknown provider) - safe to expose
        logger.warning(f"[Routes] Config error for '{query}': {type(e).__name__}")
        raise HTTPException(status_code=400, detail=str(e))

    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        logger.error(f"[Routes] HTTP {status} from external API for '{query}'")
        if status == 401:
            detail = (
                "API key rejected (401 Unauthorized). "
                "Your key may be invalid or expired. Check it in the sidebar and try again."
            )
        elif status == 403:
            detail = (
                "Access denied (403 Forbidden). "
                "Your API key may not have permission for this endpoint."
            )
        elif status == 429:
            detail = (
                "Rate limit reached (429). "
                "You have hit your provider's request limit. Wait a moment and try again, "
                "or switch to a different provider."
            )
        elif status >= 500:
            detail = (
                f"The provider's server returned an error ({status}). "
                "This is on their end - try again in a moment."
            )
        else:
            detail = f"External API returned HTTP {status}. Try again or switch providers."
        raise HTTPException(status_code=502, detail=detail)

    except httpx.ConnectError:
        logger.error(f"[Routes] Connection error for '{query}'")
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not connect to the provider. "
                "Check your internet connection. "
                "If you are using Ollama, make sure it is running at the configured URL."
            ),
        )

    except httpx.TimeoutException:
        logger.error(f"[Routes] Timeout for '{query}'")
        raise HTTPException(
            status_code=504,
            detail=(
                "Request timed out while contacting the provider. "
                "Try again, or reduce the scope of your query."
            ),
        )

    except Exception as e:
        # Log the error type only - never log the full message (may contain key material)
        logger.error(f"[Routes] Pipeline failed for '{query}': {type(e).__name__}")
        raise HTTPException(
            status_code=500,
            detail=(
                f"An unexpected error occurred ({type(e).__name__}). "
                "Try again. If this keeps happening, check your provider settings."
            ),
        )


class ServerConfig(BaseModel):
    fallback_allow: bool


@router.get("/server-config", response_model=ServerConfig)
async def get_server_config() -> ServerConfig:
    """
    Returns public server configuration flags for the frontend.
    Currently exposes only fallback_allow — whether the server permits
    the frontend to use the server's own Groq + Tavily keys as a last-resort
    fallback when the user has not supplied their own keys.
    """
    settings = get_settings()
    return ServerConfig(fallback_allow=settings.fallback_allow)


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
    """Return active provider config per pipeline step."""
    settings = get_settings()
    from providers.factory import get_llm_provider
    default_llm = get_llm_provider(settings)
    analyzer = get_query_analyzer_llm(settings)
    extractor = get_extraction_llm(settings)
    validator = get_validator_llm(settings)
    search = get_search_provider(settings)

    return ProvidersResponse(
        default=ProviderInfo(provider=default_llm.provider_name, model=default_llm.model_name),
        query_analyzer=ProviderInfo(provider=analyzer.provider_name, model=analyzer.model_name),
        extractor=ProviderInfo(provider=extractor.provider_name, model=extractor.model_name),
        validator=ProviderInfo(provider=validator.provider_name, model=validator.model_name),
        search=search.provider_name,
        available_llm_providers=["ollama", "groq", "openai", "anthropic"],
        available_search_providers=["tavily", "brave", "duckduckgo"],
    )