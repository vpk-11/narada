"""
agents/validator.py

Post-aggregation validation step.

After extraction and deduplication, we have a list of entities that MIGHT
match the original query. Some will be noise — investors, legacy companies,
research firms that got pulled in from listicle pages.

This agent runs a single fast LLM call that:
1. Sees the original query
2. Sees the full entity list
3. Returns only the entities that genuinely match the query intent

Why a separate agent vs fixing the extractor:
- Extraction happens per-page without full list context
- Validation sees ALL entities at once and can make relative judgments
- One cheap call vs N expensive calls
- Keeps extraction and validation concerns separate
"""

import json
import logging
import re

from core.models import Entity, QueryAnalysis
from providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are Narada, a precise research quality filter.
Your job is to filter a list of extracted entities and keep only those
that genuinely match the original research query.
You respond with valid JSON only. No prose, no markdown, no explanation.
"""

_PROMPT_TEMPLATE = """You extracted entities from web pages for this research query:
"{query}"

Entity type being researched: {entity_type}

Here are the extracted entities. Some may be noise — investors, legacy companies,
research firms, or entities mentioned in passing that don't match the query.

Entities:
{entity_list}

Return ONLY the names of entities that genuinely match the research query.
An entity matches if it IS a {entity_type} that the query is actually asking about.

An entity does NOT match if it is:
- A venture capital or investment firm (unless the query is about VCs)
- A large legacy corporation that predates the "startup" qualifier by decades
- A research, consulting, or media company (unless the query asks for those)
- A customer, partner, or investor of another entity on the list
- Something mentioned only in passing as context

Return JSON:
{{
  "valid_names": ["Entity Name 1", "Entity Name 2"]
}}

JSON only. No other text.
"""


def _parse_valid_names(raw: str) -> list[str]:
    """Parse the list of valid entity names from LLM output."""
    cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    cleaned = re.sub(r"```(?:json)?\s*", "", cleaned).strip().rstrip("```").strip()

    try:
        parsed = json.loads(cleaned)
        names = parsed.get("valid_names", [])
        if isinstance(names, list):
            return [str(n).strip() for n in names if str(n).strip()]
        return []
    except json.JSONDecodeError as e:
        logger.error(f"[Validator] JSON parse error: {e}\nRaw:\n{raw[:300]}")
        return []


def _normalize(name: str) -> str:
    """Normalize name for case-insensitive matching."""
    return name.lower().strip()


async def validate_entities(
    entities: list[Entity],
    analysis: QueryAnalysis,
    llm: BaseLLMProvider,
) -> list[Entity]:
    """
    Filter entities to only those that genuinely match the original query.

    Args:
        entities: aggregated entity list from the aggregator
        analysis: original query analysis (entity_type + original query)
        llm: any BaseLLMProvider — use a fast model, this is a lightweight call

    Returns:
        filtered list of Entity objects that match the query intent
    """
    if not entities:
        return entities

    # Build a simple numbered list for the LLM to reason over
    entity_list = "\n".join(
        f"{i+1}. {e.name} — {e.attributes.get('what_they_do', {}).value if 'what_they_do' in e.attributes else 'no description'}"
        for i, e in enumerate(entities)
    )

    original_query = getattr(analysis, "original_query", "") or ""

    prompt = _PROMPT_TEMPLATE.format(
        query=original_query,
        entity_type=analysis.entity_type,
        entity_list=entity_list,
    )

    logger.info(f"[Validator] Validating {len(entities)} entities against query: '{original_query}'")

    try:
        raw = await llm.complete(prompt=prompt, system=_SYSTEM_PROMPT)
        valid_names = _parse_valid_names(raw)

        if not valid_names:
            logger.warning("[Validator] No valid names returned — keeping all entities")
            return entities

        # Match by normalized name — case insensitive
        valid_normalized = {_normalize(n) for n in valid_names}
        filtered = [e for e in entities if _normalize(e.name) in valid_normalized]

        logger.info(
            f"[Validator] {len(entities)} -> {len(filtered)} entities after validation "
            f"(removed {len(entities) - len(filtered)} noise entities)"
        )
        return filtered

    except Exception as e:
        logger.warning(f"[Validator] Validation failed: {e} — returning unfiltered entities")
        return entities