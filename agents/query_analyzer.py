"""
agents/query_analyzer.py

Step 1 of the Narada pipeline.

Takes the raw user query and asks the LLM to think before anything
is searched or scraped:
  - What kind of entity are we looking for?
  - What attributes actually matter for this query?
  - What are 2-3 TARGETED search queries that will return pages where
    the entity is the PRIMARY subject, not just mentioned in passing?

This is what makes the output schema dynamic and the search targeted.
"""

import json
import logging
import re

from core.models import QueryAnalysis
from providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are Narada, an intelligent research agent.
Your job is to analyze a user query and prepare a structured research plan.
You always respond with valid JSON only. No prose, no markdown, no explanation.
"""

_PROMPT_TEMPLATE = """Analyze this research query: "{query}"

Respond with a JSON object containing exactly these fields:

{{
  "entity_type": "the type of entity being searched for (e.g. company, restaurant, tool, person)",
  "attributes": ["5 to 8 relevant attribute names"],
  "search_queries": ["2 to 3 targeted search query strings"]
}}

Rules for entity_type:
- Single lowercase noun

Rules for attributes:
- Specific and relevant to this entity type and query
- Never include generic attributes like "name" or "id"

Rules for search_queries — THIS IS CRITICAL:
- Each query must return pages where the {{entity_type}} IS the primary subject
- NOT pages that merely mention the entity in passing
- Use formats like: "list of [entity_type]", "[entity_type] directory", "top [entity_type] [qualifier]"
- Target sources that compile focused lists: YC, Crunchbase, industry directories
- Avoid broad news articles that mix many entity types together
- Queries must be distinct — not the same query rephrased

Examples:

Query: "AI startups in healthcare"
{{
  "entity_type": "company",
  "attributes": ["founded", "funding_raised", "headquarters", "what_they_do", "notable_customers"],
  "search_queries": [
    "site:ycombinator.com AI healthcare startups",
    "crunchbase top AI healthcare companies 2024 list",
    "AI medical startups founded after 2018 funding raised"
  ]
}}

Query: "top pizza places in Brooklyn"
{{
  "entity_type": "restaurant",
  "attributes": ["neighborhood", "price_range", "specialty", "rating", "notable_dish"],
  "search_queries": [
    "best pizza restaurants Brooklyn NYC ranked list",
    "top rated Brooklyn pizza places review guide",
    "Brooklyn pizza spots directory neighborhood guide"
  ]
}}

Query: "open source database tools"
{{
  "entity_type": "tool",
  "attributes": ["language", "license", "use_case", "github_stars", "maintained_by"],
  "search_queries": [
    "open source database tools list comparison 2024",
    "github top open source databases ranked",
    "best open source relational databases developer guide"
  ]
}}
"""


def _parse_llm_json(raw: str) -> dict:
    """
    Parse JSON from LLM output.
    Strips Qwen3 <think> blocks and markdown fences before parsing.
    """
    cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    cleaned = re.sub(r"```(?:json)?\s*", "", cleaned).strip().rstrip("```").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"[QueryAnalyzer] JSON parse failed: {e}\nRaw:\n{raw[:500]}")
        raise ValueError(f"LLM returned invalid JSON: {e}") from e


def _validate_analysis(data: dict, original_query: str) -> QueryAnalysis:
    """
    Validate parsed JSON against the QueryAnalysis schema.
    Raises ValueError with a clear message if required fields are missing.
    """
    required = {"entity_type", "attributes", "search_queries"}
    missing = required - data.keys()

    if missing:
        raise ValueError(f"LLM response missing required fields: {missing}")

    if not isinstance(data["attributes"], list) or len(data["attributes"]) == 0:
        raise ValueError("attributes must be a non-empty list")

    if not isinstance(data["search_queries"], list) or len(data["search_queries"]) == 0:
        raise ValueError("search_queries must be a non-empty list")

    return QueryAnalysis(
        original_query=original_query,
        entity_type=str(data["entity_type"]).strip().lower(),
        attributes=[str(a).strip() for a in data["attributes"]],
        search_queries=[str(q).strip() for q in data["search_queries"]],
    )


async def analyze_query(query: str, llm: BaseLLMProvider) -> QueryAnalysis:
    """
    Analyze a user query and produce a structured research plan.

    Args:
        query: raw user input, e.g. "AI startups in healthcare"
        llm: any BaseLLMProvider implementation

    Returns:
        QueryAnalysis with entity_type, attributes, and search_queries
    """
    prompt = _PROMPT_TEMPLATE.format(query=query)

    logger.info(f"[QueryAnalyzer] Analyzing: '{query}'")

    raw_response = await llm.complete(prompt=prompt, system=_SYSTEM_PROMPT)

    logger.debug(f"[QueryAnalyzer] Raw LLM response:\n{raw_response}")

    parsed = _parse_llm_json(raw_response)
    analysis = _validate_analysis(parsed, original_query=query)

    logger.info(
        f"[QueryAnalyzer] entity_type={analysis.entity_type} | "
        f"attributes={analysis.attributes} | "
        f"search_queries={analysis.search_queries}"
    )

    return analysis