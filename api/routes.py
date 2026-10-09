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

import asyncio
import json
import logging
import os

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from api.free_tier import FreeTierQuota, client_ip
from api.limiter import limiter
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
# Model strings use LiteLLM format: provider/model-name (e.g. groq/llama-3.3-70b-versatile)
_H_QA_MODEL        = "x-query-analyzer-model"
_H_EX_MODEL        = "x-extractor-model"
_H_VA_MODEL        = "x-validator-model"


quota = FreeTierQuota()


# --------------------------------------------------------------------------- #
# Request / Response shapes
# --------------------------------------------------------------------------- #

_MAX_QUERY_LENGTH = 500


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

    # Provider + model selection (full LiteLLM model strings)
    if h.get(_H_SEARCH_PROVIDER):
        overrides["search_provider"] = h[_H_SEARCH_PROVIDER]
    if h.get(_H_QA_MODEL):
        overrides["query_analyzer_model"] = h[_H_QA_MODEL]
    if h.get(_H_EX_MODEL):
        overrides["extraction_model"] = h[_H_EX_MODEL]
    if h.get(_H_VA_MODEL):
        overrides["validator_model"] = h[_H_VA_MODEL]

    if not overrides:
        return base

    return base.model_copy(update=overrides)


def _uses_server_keys(settings: Settings, base: Settings) -> bool:
    """
    True if any LLM step or the search provider resolves to a key the client
    did not override. Provider names map to `<name>_api_key` Settings fields;
    providers without one (ollama, duckduckgo) need no key.
    """
    models = (settings.query_analyzer_model, settings.extraction_model, settings.validator_model)
    names = [(m or settings.llm_model).split("/")[0] for m in models] + [settings.search_provider]
    fields = {f"{n.lower()}_api_key" for n in names} & set(Settings.model_fields)
    return any(getattr(settings, f) == getattr(base, f) for f in fields)


def _enforce_free_tier(request: Request, settings: Settings, base: Settings) -> None:
    """
    In production, a request that would spend server keys needs fallback_allow
    and a free-tier slot. Counts the slot. No-op in development, where .env
    keys are the intended default.
    """
    if settings.environment != "production" or not _uses_server_keys(settings, base):
        return
    if not settings.fallback_allow:
        raise HTTPException(
            status_code=403,
            detail="This server does not provide API keys. Add your own keys in the sidebar.",
        )
    quota.consume(client_ip(request), settings)


def _prepare(request: Request, body: SearchRequest) -> tuple[str, Settings, BaseSearchProvider]:
    """Shared prelude for both search routes: validate, build settings, check the free tier."""
    query = _validated_query(body)
    base = get_settings()
    try:
        settings = _build_settings_from_headers(request, base)
        search_provider = get_search_provider(settings)
    except Exception as e:
        raise _to_http_error(e, query)
    _enforce_free_tier(request, settings, base)
    return query, settings, search_provider


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #

def _validated_query(body: SearchRequest) -> str:
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query cannot be empty")
    if len(query) > _MAX_QUERY_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Query must be {_MAX_QUERY_LENGTH} characters or fewer.",
        )
    return query


def _to_http_error(e: Exception, query: str) -> HTTPException:
    """Map a pipeline exception to a user-facing HTTPException. Logs the error type only."""
    if isinstance(e, ValueError):
        # Config/validation errors (missing key, unknown provider) - safe to expose
        logger.warning(f"[Routes] Config error for '{query[:80]}': {type(e).__name__}")
        return HTTPException(status_code=400, detail=str(e))

    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        logger.error(f"[Routes] HTTP {status} from external API for '{query[:80]}'")
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
        return HTTPException(status_code=502, detail=detail)

    if isinstance(e, httpx.ConnectError):
        logger.error(f"[Routes] Connection error for '{query[:80]}'")
        return HTTPException(
            status_code=502,
            detail=(
                "Could not connect to the provider. "
                "Check your internet connection. "
                "If you are using Ollama, make sure it is running at the configured URL."
            ),
        )

    if isinstance(e, httpx.TimeoutException):
        logger.error(f"[Routes] Timeout for '{query[:80]}'")
        return HTTPException(
            status_code=504,
            detail=(
                "Request timed out while contacting the provider. "
                "Try again, or reduce the scope of your query."
            ),
        )

    # Log the error type only - never log the full message (may contain key material)
    logger.error(f"[Routes] Pipeline failed for '{query[:80]}': {type(e).__name__}")
    return HTTPException(
        status_code=500,
        detail=(
            f"An unexpected error occurred ({type(e).__name__}). "
            "Try again. If this keeps happening, check your provider settings."
        ),
    )


@router.post("/search", response_model=SearchResponse)
@limiter.limit(lambda: get_settings().search_rate_limit)
async def search(request: Request, body: SearchRequest) -> SearchResponse:
    """
    Run the Narada pipeline for a query.

    API keys are read from request headers (x-groq-api-key etc).
    Keys override .env for this call only and are never stored.
    Set refresh=true to bypass cache and force a fresh run.
    """
    query, settings, search_provider = _prepare(request, body)

    try:
        result = await run_pipeline(
            query=query,
            settings=settings,
            search=search_provider,
            use_cache=not body.refresh,
        )
        return SearchResponse(result=result)
    except Exception as e:
        raise _to_http_error(e, query)


def _sse(event: dict) -> str:
    return f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"


@router.post("/search/stream")
@limiter.limit(lambda: get_settings().search_rate_limit)
async def search_stream(request: Request, body: SearchRequest) -> StreamingResponse:
    """
    Same pipeline as POST /search, streamed as Server-Sent Events.

    Events: "step" (one per completed step), "rows" (aggregated entities after
    step 6), then exactly one of "result" (same payload as POST /search) or
    "error" (message only). Config errors found before the run starts return a
    normal HTTP error instead of a stream.
    """
    query, settings, search_provider = _prepare(request, body)
    use_cache = not body.refresh

    queue: asyncio.Queue[dict | None] = asyncio.Queue()

    async def on_progress(event: dict) -> None:
        await queue.put(event)

    async def run() -> None:
        try:
            result = await run_pipeline(
                query=query,
                settings=settings,
                search=search_provider,
                use_cache=use_cache,
                on_progress=on_progress,
            )
            await queue.put({"type": "result", **SearchResponse(result=result).model_dump(mode="json")})
        except Exception as e:
            await queue.put({"type": "error", "detail": _to_http_error(e, query).detail})
        finally:
            await queue.put(None)

    async def events():
        task = asyncio.create_task(run())
        try:
            while (event := await queue.get()) is not None:
                yield _sse(event)
        finally:
            task.cancel()

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class ServerConfig(BaseModel):
    fallback_allow: bool
    free_searches_remaining: int


@router.get("/server-config", response_model=ServerConfig)
async def get_server_config(request: Request) -> ServerConfig:
    """
    Public flags for the frontend: whether the server lets keyless requests use
    its own Groq + Tavily keys, and how many free searches this client has left
    today (0 when the free tier is off).
    """
    settings = get_settings()
    remaining = quota.remaining(client_ip(request), settings) if settings.fallback_allow else 0
    return ServerConfig(fallback_allow=settings.fallback_allow, free_searches_remaining=remaining)


@router.delete("/cache", response_model=CacheClearResponse)
async def delete_cache(
    x_admin_key: str | None = Header(default=None, alias="x-admin-key"),
) -> CacheClearResponse:
    """Clear all cached pipeline results. Requires x-admin-key header when CACHE_ADMIN_KEY is set."""
    settings = get_settings()
    if settings.cache_admin_key and x_admin_key != settings.cache_admin_key:
        raise HTTPException(status_code=403, detail="Valid x-admin-key header required.")
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
        available_llm_providers=["groq", "openai", "anthropic", "ollama"],
        available_search_providers=["tavily", "brave", "duckduckgo"],
    )