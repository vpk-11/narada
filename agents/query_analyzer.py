"""
agents/query_analyzer.py

Step 1 of the Narada pipeline.

Takes the raw user query and asks the LLM to think before anything
is searched or scraped:
  - What kind of entity are we looking for?
  - What attributes actually matter for this query?
  - What are 2-3 smart search queries to run?

This is what makes the output schema dynamic.
"AI startups in healthcare" gets different columns than "pizza places in Brooklyn".
"""

import json
import logging
import re

from core.models import QueryAnalysis
from providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

# System prompt is fixed — defines Narada's role for this step
_SYSTEM_PROMPT = """You are Narada, an intelligent research agent.
Your job is to analyze a user query and prepare a structured research plan.
You always respond with valid JSON only. No prose, no markdown, no explanation.
"""

# The instruction template — query is injected at runtime
_PROMPT_TEMPLATE = """Analyze this research query: "{query}"

Respond with a JSON object containing exactly these fields:

{{
  "entity_type": "the type of entity being searched for (e.g. company, restaurant, tool, person, university)",
  "attributes": ["list", "of", "5 to 8", "relevant", "attribute", "names"],
  "search_queries": ["2 to 3", "targeted", "search query strings"]
}}

Rules:
- entity_type must be a single lowercase noun
- attributes must be specific and relevant to this entity type and query
- search_queries must be distinct and targeted, not the same query rephrased
- Never include generic attributes like "name" or "id" — those are implicit
- Respond with JSON only. No other text.

Examples:

Query: "AI startups in healthcare"
{{
  "entity_type": "company",
  "attributes": ["founded", "funding_raised", "headquarters", "what_they_do", "notable_customers"],
  "search_queries": [
    "AI healthcare startups 2024",
    "top artificial intelligence medical startups funding",
    "healthcare AI companies series A B funding"
  ]
}}

Query: "top pizza places in Brooklyn"
{{
  "entity_type": "restaurant",
  "attributes": ["neighborhood", "price_range", "specialty", "rating", "notable_dish"],
  "search_queries": [
    "best pizza Brooklyn NYC 2024",
    "top rated Brooklyn pizza restaurants",
    "must try pizza places Brooklyn New York"
  ]
}}
"""


def _parse_llm_json(raw: str) -> dict:
    """
    Extract and parse JSON from LLM output.
    LLMs sometimes wrap JSON in markdown fences even when told not to.
    Also strips <think> tags that Qwen3 outputs before the JSON.
    """
    # Strip <think>...</think> blocks — Qwen3 outputs these before responding
    cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", cleaned).strip().rstrip("```").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON: {e}\nRaw output:\n{raw}")
        raise ValueError(f"LLM returned invalid JSON: {e}") from e


def _validate_analysis(data: dict) -> QueryAnalysis:
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

    Raises:
        ValueError: if the LLM returns unparseable or invalid output
    """
    prompt = _PROMPT_TEMPLATE.format(query=query)

    logger.info(f"[QueryAnalyzer] Analyzing: '{query}'")

    raw_response = await llm.complete(prompt=prompt, system=_SYSTEM_PROMPT)

    logger.debug(f"[QueryAnalyzer] Raw LLM response:\n{raw_response}")

    parsed = _parse_llm_json(raw_response)
    analysis = _validate_analysis(parsed)

    logger.info(
        f"[QueryAnalyzer] Done — entity_type={analysis.entity_type} | "
        f"attributes={analysis.attributes} | "
        f"search_queries={analysis.search_queries}"
    )

    return analysis