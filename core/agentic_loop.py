"""
core/agentic_loop.py

Step 6.5 of the Narada pipeline — gap-driven re-search.

After validation, checks how complete the entity table is. If too many
cells are empty, generates targeted follow-up search queries for the
worst gaps, runs one more search+scrape+extract round, and merges the
results back into the table. Capped at a small number of iterations so
a stubbornly sparse query doesn't loop forever, and URLs already visited
are skipped so a follow-up round never re-scrapes a page the first pass
already covered.

This is what makes the pipeline agentic rather than a fixed sequence: it
reasons about its own output quality and takes corrective action instead
of just running once and returning whatever it found.
"""

import logging

from agents.aggregator import aggregate_entities
from agents.extractor import extract_entities
from agents.scraper import scrape_pages
from core.llm_json import parse_llm_json
from core.models import Entity, QueryAnalysis, SearchResult
from providers.base import BaseLLMProvider, BaseSearchProvider

logger = logging.getLogger(__name__)

_MAX_GAPS_CONSIDERED = 5

_GAP_QUERY_SYSTEM_PROMPT = """You are Narada, a research agent deciding how to fill gaps in a data table.
You respond with valid JSON only. No prose, no markdown.
"""

_GAP_QUERY_PROMPT_TEMPLATE = """Original research query: "{query}"
Entity type: {entity_type}

These entities are missing some of the attributes we need:
{gap_list}

Generate 1-3 targeted search queries that would help find the missing information.
Each query should be 3-8 words and include the specific entity name where possible,
so the search returns pages about that entity rather than the topic in general.

Return JSON:
{{"queries": ["query one", "query two"]}}

JSON only. No other text.
"""


def compute_gap_ratio(entities: list[Entity], attributes: list[str]) -> float:
    """
    Fraction of (entity, attribute) cells with no value at all.
    1.0 means every entity is missing every attribute; 0.0 means the
    table is fully populated. Entities are omission-based (a missing
    attribute simply isn't a key in entity.attributes), so this counts
    key presence rather than null values.
    """
    if not entities or not attributes:
        return 0.0
    total_cells = len(entities) * len(attributes)
    filled_cells = sum(len(e.attributes) for e in entities)
    return max(0.0, 1.0 - (filled_cells / total_cells))


def _identify_gaps(entities: list[Entity], attributes: list[str]) -> list[dict]:
    """Build {name, missing} per incomplete entity, worst gaps first, capped."""
    gaps = []
    for entity in entities:
        missing = [a for a in attributes if a not in entity.attributes]
        if missing:
            gaps.append({"name": entity.name, "missing": missing})
    gaps.sort(key=lambda g: len(g["missing"]), reverse=True)
    return gaps[:_MAX_GAPS_CONSIDERED]


async def _generate_gap_queries(
    gaps: list[dict],
    query: str,
    entity_type: str,
    llm: BaseLLMProvider,
) -> list[str]:
    """
    Ask the LLM for targeted follow-up search queries.
    Returns [] on any failure — a broken gap-query round fails closed
    and the loop simply stops, rather than crashing the pipeline.
    """
    if not gaps:
        return []

    gap_list = "\n".join(f"- {g['name']}: missing {', '.join(g['missing'])}" for g in gaps)
    prompt = _GAP_QUERY_PROMPT_TEMPLATE.format(query=query, entity_type=entity_type, gap_list=gap_list)

    try:
        raw = await llm.complete(prompt=prompt, system=_GAP_QUERY_SYSTEM_PROMPT)
        parsed = parse_llm_json(raw)
        queries = parsed.get("queries", []) if isinstance(parsed, dict) else []
        return [str(q).strip() for q in queries if str(q).strip()]
    except Exception as e:
        logger.warning(f"[AgenticLoop] Gap query generation failed: {e}")
        return []


async def run_gap_filling_round(
    entities: list[Entity],
    analysis: QueryAnalysis,
    search: BaseSearchProvider,
    query_llm: BaseLLMProvider,
    extraction_llm: BaseLLMProvider,
    visited_urls: set[str],
    n_results: int,
    scrape_timeout: int,
    max_pages: int,
) -> tuple[list[Entity], int]:
    """
    Run one gap-filling round: identify gaps, generate follow-up queries,
    search + scrape + extract new pages, merge results back in.

    visited_urls is mutated in place so subsequent rounds never re-scrape
    a page an earlier round already covered.

    Returns (updated entity list, number of new pages scraped this round).
    A 0 page count signals the caller to stop iterating — nothing new to
    merge means another round won't help either.
    """
    gaps = _identify_gaps(entities, analysis.attributes)
    if not gaps:
        return entities, 0

    queries = await _generate_gap_queries(
        gaps=gaps,
        query=getattr(analysis, "original_query", ""),
        entity_type=analysis.entity_type,
        llm=query_llm,
    )
    if not queries:
        return entities, 0

    new_results: list[SearchResult] = []
    seen_this_round: set[str] = set()
    for q in queries:
        for r in await search.search(q, n_results=n_results):
            if r.url and r.url not in visited_urls and r.url not in seen_this_round:
                seen_this_round.add(r.url)
                new_results.append(r)

    if not new_results:
        return entities, 0

    visited_urls.update(seen_this_round)

    new_pages = await scrape_pages(results=new_results, timeout=scrape_timeout, max_pages=max_pages)
    if not new_pages:
        return entities, 0

    new_entities = await extract_entities(
        pages=new_pages,
        analysis=analysis,
        llm=extraction_llm,
        extraction_llm=extraction_llm,
    )

    merged = aggregate_entities(entities + new_entities)
    return merged, len(new_pages)
