"""
core/pipeline.py

The Narada pipeline orchestrator.

Wires all agents together in order and returns a PipelineResult.
This is the single function the API calls — it knows nothing about
HTTP, FastAPI, or request handling.

Pipeline steps:
  1. Cache check — return immediately if result exists
  2. Query analysis — LLM determines entity type, schema, search queries
  3. Search — run all search queries, deduplicate URLs
  4. Scrape — fetch and clean all pages concurrently
  5. Extract — LLM pulls structured entities from each page sequentially
  6. Aggregate — deduplicate and merge entities across sources
  7. Cache write — store result for future identical queries
  8. Return PipelineResult
"""

import logging
import time

from agents.aggregator import aggregate_entities
from agents.extractor import extract_entities
from agents.query_analyzer import analyze_query
from agents.scraper import scrape_pages
from config import Settings
from core.cache import get_cached, set_cached
from core.models import PipelineMetadata, PipelineResult, SearchResult
from providers.base import BaseLLMProvider, BaseSearchProvider

logger = logging.getLogger(__name__)


async def _run_searches(
    search_queries: list[str],
    search_provider: BaseSearchProvider,
    n_results: int,
) -> list[SearchResult]:
    """
    Run all search queries sequentially and return deduplicated results.
    Deduplicates by URL so the same page is never scraped twice.
    """
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
    llm: BaseLLMProvider,
    search: BaseSearchProvider,
    extraction_llm: BaseLLMProvider | None = None,
    use_cache: bool = True,
) -> PipelineResult:
    """
    Run the full Narada pipeline for a given query.

    Args:
        query: raw user input, e.g. "AI startups in healthcare"
        settings: app settings (pipeline tuning params)
        llm: primary LLM provider (query analysis + fallback for extraction)
        search: search provider
        extraction_llm: optional separate LLM just for extraction step.
                        Enables multi-model setups (e.g. Ollama for analysis,
                        Groq for extraction).
        use_cache: if True, check cache before running and write after.
                   Set to False to force a fresh run.

    Returns:
        PipelineResult with entities, attributes, sources, and metadata
    """
    start = time.monotonic()
    active_extraction_llm = extraction_llm if extraction_llm is not None else llm

    # ── Step 1: Cache check ──────────────────────────────────────────────── #
    if use_cache:
        cached = get_cached(
            query=query,
            llm_provider=llm.provider_name,
            llm_model=llm.model_name,
            search_provider=search.provider_name,
        )
        if cached is not None:
            logger.info(f"[Pipeline] Cache HIT for '{query}'")
            return cached

    logger.info(f"[Pipeline] Starting fresh run for '{query}'")

    # ── Step 2: Query analysis ───────────────────────────────────────────── #
    analysis = await analyze_query(query=query, llm=llm)

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
                llm_provider=llm.provider_name,
                llm_model=llm.model_name,
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
        llm=llm,
        extraction_llm=active_extraction_llm,
    )

    # ── Step 6: Aggregate ────────────────────────────────────────────────── #
    final_entities = aggregate_entities(raw_entities)

    duration = round(time.monotonic() - start, 2)

    result = PipelineResult(
        query=query,
        entity_type=analysis.entity_type,
        attributes=analysis.attributes,
        entities=final_entities,
        metadata=PipelineMetadata(
            search_provider=search.provider_name,
            llm_provider=llm.provider_name,
            llm_model=active_extraction_llm.model_name,
            pages_scraped=len(pages),
            duration_seconds=duration,
        ),
    )

    # ── Step 7: Cache write ──────────────────────────────────────────────── #
    if use_cache:
        set_cached(
            query=query,
            llm_provider=llm.provider_name,
            llm_model=llm.model_name,
            search_provider=search.provider_name,
            result=result,
        )

    logger.info(
        f"[Pipeline] Done in {duration}s — "
        f"{len(final_entities)} entities from {len(pages)} pages"
    )
    return result