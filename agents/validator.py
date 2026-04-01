"""
agents/validator.py

Post-aggregation validation step.

After extraction and deduplication, runs a single LLM call to filter out
entities that don't match the original query intent.

This catches noise that slips through extraction:
- Generic unicorn/funding lists that include off-topic companies
- Investors, VCs, research firms
- Companies from completely different sectors
"""

import json
import logging
import re

from core.models import Entity, QueryAnalysis
from providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are Narada, a strict research quality filter.
You receive a list of extracted entities and a research query.
Your ONLY job is to remove entities that do not belong.
You respond with valid JSON only. No prose, no markdown.
"""

_PROMPT_TEMPLATE = """Research query: "{query}"
We are looking for: {entity_type} entities that match this query.

Extracted entities (some may be wrong):
{entity_list}

Your job: return ONLY the names of entities that DIRECTLY match the query.

RULES — remove an entity only if you are CONFIDENT it does not belong:
1. It is clearly from a completely unrelated industry (fintech, defense, retail, logistics, social media, crypto/blockchain) with no healthcare connection
2. It is a VC firm, investment fund, or financial institution
3. It is a research firm, consulting company, or media/news outlet
4. It is a blockchain or crypto company with no healthcare application
5. It appears to be the name of a website or blog, not a company
6. It is a very large legacy corporation (e.g. Google, Microsoft, Amazon) that is not primarily a healthcare AI company

Do NOT remove an entity just because its description is vague or incomplete.
If a company could plausibly be a healthcare AI company based on available info, KEEP it.
It is better to keep a borderline entity than to remove a valid one.

Return JSON:
{{
  "valid_names": ["Names of entities that match or could match the query"]
}}

Aim to keep 70-80% of entities unless they clearly do not belong.
JSON only.
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
    return name.lower().strip()


async def validate_entities(
    entities: list[Entity],
    analysis: QueryAnalysis,
    llm: BaseLLMProvider,
) -> list[Entity]:
    """
    Filter entities to only those that genuinely match the original query.
    Uses strict rules — prefers fewer correct results over many noisy ones.
    Falls back to unfiltered list if validation itself fails.
    """
    if not entities:
        return entities

    entity_list = "\n".join(
        f"{i+1}. {e.name}"
        + (f" — {e.attributes['what_they_do'].value}" if "what_they_do" in e.attributes else "")
        + (f" — {e.attributes['ai_specialization'].value}" if "ai_specialization" in e.attributes else "")
        + (f" — {e.attributes['healthcare_application_area'].value}" if "healthcare_application_area" in e.attributes else "")
        for i, e in enumerate(entities)
    )

    original_query = getattr(analysis, "original_query", "") or ""

    prompt = _PROMPT_TEMPLATE.format(
        query=original_query,
        entity_type=analysis.entity_type,
        entity_list=entity_list,
    )

    logger.info(f"[Validator] Validating {len(entities)} entities against: '{original_query}'")

    try:
        raw = await llm.complete(prompt=prompt, system=_SYSTEM_PROMPT)
        valid_names = _parse_valid_names(raw)

        if not valid_names:
            logger.warning("[Validator] No valid names returned — keeping all entities")
            return entities

        valid_normalized = {_normalize(n) for n in valid_names}
        filtered = [e for e in entities if _normalize(e.name) in valid_normalized]

        logger.info(
            f"[Validator] {len(entities)} -> {len(filtered)} entities "
            f"(removed {len(entities) - len(filtered)})"
        )
        return filtered

    except Exception as e:
        logger.warning(f"[Validator] Failed: {e} — returning unfiltered entities")
        return entities