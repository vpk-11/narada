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
  8. Cache write
"""

import logging
import time

from agents.aggregator import aggregate_entities
from agents.extractor import extract_entities
from agents.query_analyzer import analyze_query
from agents.scraper import scrape_pages
from agents.validator import validate_entities
from config import Settings
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
) -> list[SearchResult]:
    """Run all search queries and return deduplicated results."""
    seen_urls: set[str] = set()
    all_results: list[SearchResult] = []

    for query in search_queries:
        results = await search_provider.search(query, n_results=n_results)
        for r in results:
            if r.url and r.url not in seen_urls:
                seen_urls.add(r.url)
                all_results.append(r)

    logger.info(f"[Pipeline] {len(all_results)} unique URLs from {len(search_queries)} queries")
    return all_results


async def run_pipeline(
    query: str,
    settings: Settings,
    search: BaseSearchProvider,
    use_cache: bool = True,
) -> PipelineResult:
    """
    Run the full Narada pipeline for a given query.

    Provider selection is handled entirely by the factory using settings.
    Each step gets its own LLM — all fall back to LLM_PROVIDER if not configured.

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
    search_results = await _run_searches(
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
            pages_scraped=len(pages),
            duration_seconds=duration,
        ),
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