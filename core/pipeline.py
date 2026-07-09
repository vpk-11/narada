"""
core/pipeline.py

The Narada pipeline orchestrator.

Each step uses its own configured LLM provider.
All steps fall back to the default LLM_PROVIDER if not explicitly configured.

Pipeline steps:
  1. Cache check
  2. Query analysis    — query_analyzer_llm
  3. Search            — no LLM
  4. Scrape            — no LLM
  5. Extract           — extraction_llm
  6. Aggregate         — no LLM
  7. Validate          — validator_llm
  7.5 Gap-fill         — validator_llm (query gen) + extraction_llm (re-extract)
       If the validated table is still missing too many attributes, generates
       targeted follow-up searches and runs another search+scrape+extract
       round, capped at agent_max_iterations. See core/agentic_loop.py.
  8. Cache write
"""

import asyncio
import logging
import time

from agents.aggregator import aggregate_entities
from agents.extractor import extract_entities
from agents.query_analyzer import analyze_query
from agents.scraper import scrape_pages
from agents.validator import validate_entities
from config import Settings
from core.agentic_loop import compute_gap_ratio, run_gap_filling_round
from core.cache import get_cached, set_cached
from core.models import PipelineMetadata, PipelineResult, SearchResult
from providers.base import BaseSearchProvider
from providers.factory import (
    get_extraction_llm,
    get_query_analyzer_llm,
    get_validator_llm,
)

logger = logging.getLogger(__name__)


async def _run_searches(
    search_queries: list[str],
    search_provider: BaseSearchProvider,
    n_results: int,
) -> tuple[list[SearchResult], list[str]]:
    """
    Run all search queries and return deduplicated results plus any
    non-fatal errors encountered (e.g. a fallback being triggered).

    If the configured provider fails on a query (bad key, provider outage,
    rate limit), falls back to DuckDuckGo for that query rather than
    aborting the whole run — DDG needs no key and is always available.
    Only relevant when the configured provider isn't already DuckDuckGo.
    """
    seen_urls: set[str] = set()
    all_results: list[SearchResult] = []
    errors: list[str] = []
    fallback_provider: BaseSearchProvider | None = None

    for query in search_queries:
        try:
            results = await search_provider.search(query, n_results=n_results)
        except Exception as e:
            if search_provider.provider_name == "duckduckgo":
                raise  # already on the free fallback — nothing left to fall back to

            msg = (
                f"{search_provider.provider_name} search failed for '{query}' "
                f"({type(e).__name__}) — fell back to DuckDuckGo"
            )
            logger.warning(f"[Pipeline] {msg}")
            errors.append(msg)
            if fallback_provider is None:
                from providers.search.duckduckgo import DuckDuckGoProvider
                fallback_provider = DuckDuckGoProvider()
            results = await fallback_provider.search(query, n_results=n_results)

        for r in results:
            if r.url and r.url not in seen_urls:
                seen_urls.add(r.url)
                all_results.append(r)

    logger.info(f"[Pipeline] {len(all_results)} unique URLs from {len(search_queries)} queries")
    return all_results, errors


_pipeline_semaphore: asyncio.Semaphore | None = None


def _get_pipeline_semaphore(max_concurrent: int) -> asyncio.Semaphore:
    """
    Lazily create the module-level semaphore that caps concurrent pipeline
    runs server-wide. Lazy because asyncio.Semaphore must be created inside
    a running event loop; module import time isn't guaranteed to have one.
    """
    global _pipeline_semaphore
    if _pipeline_semaphore is None:
        _pipeline_semaphore = asyncio.Semaphore(max_concurrent)
    return _pipeline_semaphore


async def run_pipeline(
    query: str,
    settings: Settings,
    search: BaseSearchProvider,
    use_cache: bool = True,
) -> PipelineResult:
    """
    Run the full Narada pipeline for a given query.

    A cache hit returns immediately without consuming a concurrency slot.
    Everything past the cache check runs under a server-wide semaphore so a
    burst of concurrent requests can't all fire simultaneously against the
    server's own configured LLM/search keys — this is separate from the
    per-IP rate limit in api/routes.py, which throttles one client but not
    total server load.

    Args:
        query: raw user input
        settings: app settings
        search: search provider instance
        use_cache: check cache before running, write result after
    """
    start = time.monotonic()

    # Build step-specific LLM providers from settings
    query_analyzer_llm = get_query_analyzer_llm(settings)
    extraction_llm = get_extraction_llm(settings)
    validator_llm = get_validator_llm(settings)

    # ── Step 1: Cache check ──────────────────────────────────────────────── #
    if use_cache:
        cached = get_cached(
            query=query,
            llm_provider=query_analyzer_llm.provider_name,
            llm_model=query_analyzer_llm.model_name,
            search_provider=search.provider_name,
        )
        if cached is not None:
            logger.info(f"[Pipeline] Cache HIT for '{query}'")
            return cached

    semaphore = _get_pipeline_semaphore(settings.max_concurrent_pipeline_runs)
    async with semaphore:
        return await _run_pipeline_uncached(
            query=query,
            settings=settings,
            search=search,
            use_cache=use_cache,
            start=start,
            query_analyzer_llm=query_analyzer_llm,
            extraction_llm=extraction_llm,
            validator_llm=validator_llm,
        )


async def _run_pipeline_uncached(
    query: str,
    settings: Settings,
    search: BaseSearchProvider,
    use_cache: bool,
    start: float,
    query_analyzer_llm,
    extraction_llm,
    validator_llm,
) -> PipelineResult:
    """Steps 2-8, run under the concurrency semaphore. See run_pipeline for step 1."""
    logger.info(f"[Pipeline] Starting fresh run for '{query}'")
    logger.info(
        f"[Pipeline] Providers — "
        f"analyzer: {query_analyzer_llm.provider_name}/{query_analyzer_llm.model_name} | "
        f"extractor: {extraction_llm.provider_name}/{extraction_llm.model_name} | "
        f"validator: {validator_llm.provider_name}/{validator_llm.model_name}"
    )

    # ── Step 2: Query analysis ───────────────────────────────────────────── #
    analysis = await analyze_query(query=query, llm=query_analyzer_llm)

    # ── Step 3: Search ───────────────────────────────────────────────────── #
    search_results, run_errors = await _run_searches(
        search_queries=analysis.search_queries,
        search_provider=search,
        n_results=settings.search_results_per_query,
    )

    if not search_results:
        logger.warning(f"[Pipeline] No search results for '{query}'")
        return PipelineResult(
            query=query,
            entity_type=analysis.entity_type,
            attributes=analysis.attributes,
            entities=[],
            metadata=PipelineMetadata(
                search_provider=search.provider_name,
                llm_provider=query_analyzer_llm.provider_name,
                llm_model=query_analyzer_llm.model_name,
                pages_scraped=0,
                duration_seconds=round(time.monotonic() - start, 2),
            ),
            errors=run_errors + ["No search results found for this query."],
        )

    # ── Step 4: Scrape ───────────────────────────────────────────────────── #
    pages = await scrape_pages(
        results=search_results,
        timeout=settings.scrape_timeout_seconds,
        max_pages=settings.max_pages_to_scrape,
    )

    # ── Step 5: Extract ──────────────────────────────────────────────────── #
    raw_entities = await extract_entities(
        pages=pages,
        analysis=analysis,
        llm=extraction_llm,
    )

    # ── Step 6: Aggregate ────────────────────────────────────────────────── #
    aggregated_entities = aggregate_entities(raw_entities)

    # ── Step 7: Validate ─────────────────────────────────────────────────── #
    final_entities = await validate_entities(
        entities=aggregated_entities,
        analysis=analysis,
        llm=validator_llm,
    )

    # ── Step 7.5: Agentic gap-fill ────────────────────────────────────────── #
    total_pages_scraped = len(pages)
    visited_urls = {r.url for r in search_results}
    iterations = 1
    gap_ratio = compute_gap_ratio(final_entities, analysis.attributes)

    while gap_ratio > settings.agent_gap_threshold and iterations < settings.agent_max_iterations:
        logger.info(
            f"[Pipeline] Gap ratio {gap_ratio:.2f} exceeds threshold "
            f"{settings.agent_gap_threshold} — running gap-fill round {iterations + 1}"
        )
        final_entities, new_pages_count = await run_gap_filling_round(
            entities=final_entities,
            analysis=analysis,
            search=search,
            query_llm=validator_llm,
            extraction_llm=extraction_llm,
            visited_urls=visited_urls,
            n_results=settings.search_results_per_query,
            scrape_timeout=settings.scrape_timeout_seconds,
            max_pages=settings.max_pages_to_scrape,
        )
        iterations += 1
        total_pages_scraped += new_pages_count

        if new_pages_count == 0:
            logger.info("[Pipeline] Gap-fill round found no new pages — stopping")
            break

        new_gap_ratio = compute_gap_ratio(final_entities, analysis.attributes)
        if new_gap_ratio >= gap_ratio:
            logger.info("[Pipeline] Gap-fill round did not improve completeness — stopping")
            gap_ratio = new_gap_ratio
            break
        gap_ratio = new_gap_ratio

    duration = round(time.monotonic() - start, 2)

    result = PipelineResult(
        query=query,
        entity_type=analysis.entity_type,
        attributes=analysis.attributes,
        entities=final_entities,
        metadata=PipelineMetadata(
            search_provider=search.provider_name,
            llm_provider=query_analyzer_llm.provider_name,
            llm_model=extraction_llm.model_name,
            pages_scraped=total_pages_scraped,
            duration_seconds=duration,
            search_iterations=iterations,
            gap_ratio=round(gap_ratio, 3),
        ),
        errors=run_errors,
    )

    # ── Step 8: Cache write ──────────────────────────────────────────────── #
    if use_cache:
        set_cached(
            query=query,
            llm_provider=query_analyzer_llm.provider_name,
            llm_model=query_analyzer_llm.model_name,
            search_provider=search.provider_name,
            result=result,
        )

    logger.info(
        f"[Pipeline] Done in {duration}s — "
        f"{len(final_entities)} entities from {len(pages)} pages"
    )
    return result