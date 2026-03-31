"""
agents/extractor.py

Step 4 of the Narada pipeline.

For each page, sends content to the LLM and extracts structured entities.
Every attribute value is tagged with its source URL for full traceability.

Key design decisions:
- SEQUENTIAL processing — Ollama handles one request at a time locally.
- Robust JSON parser handles both {"entities":[...]} and bare [...] responses.
- _is_valid_value() filters out "None", "N/A", "unknown" etc before storage.
- Content capped at _MAX_CONTENT_CHARS — enough for llama3.2 to find attributes.
- Explicit prompt rules prevent extracting investors, report titles, or concepts.
- Post-extraction filter drops entities with zero valid attributes.
- Accepts optional extraction_llm for multi-model setups.
"""

import json
import logging
import re

from core.models import CellValue, Entity, QueryAnalysis, ScrapedPage
from providers.base import BaseLLMProvider
from providers.llm.ollama import NUM_CTX_LARGE

logger = logging.getLogger(__name__)

_MAX_CONTENT_CHARS = 2500
_MIN_ATTRIBUTES_TO_KEEP = 1

# Exact-match junk values the model writes when it can't find something
_INVALID_VALUES = {
    "none", "n/a", "na", "not available", "not found", "unknown",
    "not mentioned", "no information", "no information provided",
    "not specified", "not stated", "not given", "not provided", "-", "",
}

# Substrings that indicate the model is describing absence rather than a value
_INVALID_SUBSTRINGS = (
    "no founding date",
    "no information",
    "not provided",
    "not mentioned",
    "not available",
    "not found",
    "not specified",
    "no data",
)

_SYSTEM_PROMPT = """You are Narada, a precise data extraction agent.
Your job is to extract real, named entities from web content and their attributes.
You respond with valid JSON only. No prose, no markdown, no explanation.
"""

_PROMPT_TEMPLATE = """Extract structured data from this web page.

Entity type we want: {entity_type}
Attributes to extract per entity: {attributes}
Page URL: {url}

Page content:
---
{content}
---

IMPORTANT RULES:
1. Only extract real, named {entity_type} entities — actual proper names of specific {entity_type}s.
2. Do NOT extract: generic concepts, investor names, report titles, article authors, or category names.
3. For each entity, only include attributes you found CLEAR evidence for. No guessing.
4. If you cannot find a value for an attribute, OMIT that attribute entirely. Do not write null, None, or N/A.
5. Attribute values must be concise — one phrase or sentence maximum.
6. If you find no valid {entity_type} entities, return {{"entities": []}}.

Return this exact JSON:
{{
  "entities": [
    {{
      "name": "Actual {entity_type} Name",
      "attributes": {{
        "attribute_name": "value clearly stated in the content"
      }}
    }}
  ]
}}

JSON only. No other text.
"""


def _is_valid_value(val: str) -> bool:
    """
    Return False for values the model writes when it cannot find something.
    Checks exact matches against _INVALID_VALUES and substring matches
    against _INVALID_SUBSTRINGS — catches phrases like "No founding date provided".
    """
    normalized = val.lower().strip()
    if normalized in _INVALID_VALUES:
        return False
    return not any(sub in normalized for sub in _INVALID_SUBSTRINGS)


def _parse_llm_json(raw: str) -> dict:
    """
    Parse JSON from LLM output.
    Handles two common response patterns:
    - Correct:        {"entities": [...]}
    - Common mistake: [...] — bare array, wrapped automatically

    Also strips Qwen3 <think> blocks and markdown fences.
    """
    cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    cleaned = re.sub(r"```(?:json)?\s*", "", cleaned).strip().rstrip("```").strip()

    try:
        parsed = json.loads(cleaned)

        if isinstance(parsed, list):
            logger.debug("[Extractor] LLM returned bare array — wrapping as entities object")
            return {"entities": parsed}

        if isinstance(parsed, dict):
            return parsed

        logger.error(f"[Extractor] Unexpected JSON root type: {type(parsed)}")
        return {"entities": []}

    except json.JSONDecodeError as e:
        logger.error(f"[Extractor] JSON parse error: {e}\nRaw (first 400 chars):\n{raw[:400]}")
        raise ValueError(f"Invalid JSON from LLM: {e}") from e


def _build_entities(
    data: dict,
    source_url: str,
    valid_attributes: list[str],
) -> list[Entity]:
    """
    Convert parsed LLM JSON into Entity objects.
    Attaches source_url to every CellValue — the traceability guarantee.
    Filters out None/N/A values and drops entities with no valid attributes.
    """
    entities: list[Entity] = []
    raw_entities = data.get("entities", [])

    if not isinstance(raw_entities, list):
        return entities

    for item in raw_entities:
        if not isinstance(item, dict):
            continue

        name = str(item.get("name", "")).strip()
        if not name:
            continue

        raw_attrs = item.get("attributes", {})
        if not isinstance(raw_attrs, dict):
            raw_attrs = {}

        attributes: dict[str, CellValue] = {
            key: CellValue(value=str(val).strip(), source_url=source_url)
            for key, val in raw_attrs.items()
            if key in valid_attributes and _is_valid_value(str(val).strip())
        }

        if len(attributes) < _MIN_ATTRIBUTES_TO_KEEP:
            logger.debug(f"[Extractor] Dropping '{name}' — no valid attributes found")
            continue

        entities.append(Entity(name=name, attributes=attributes))

    return entities


async def _extract_from_page(
    page: ScrapedPage,
    analysis: QueryAnalysis,
    llm: BaseLLMProvider,
) -> list[Entity]:
    """
    Extract entities from a single page.
    Returns empty list on any failure.
    """
    content = page.content[:_MAX_CONTENT_CHARS]

    prompt = _PROMPT_TEMPLATE.format(
        entity_type=analysis.entity_type,
        attributes=", ".join(analysis.attributes),
        url=page.url,
        content=content,
    )

    try:
        raw = await llm.complete(
            prompt=prompt,
            system=_SYSTEM_PROMPT,
            num_ctx=NUM_CTX_LARGE,
        )
        parsed = _parse_llm_json(raw)
        entities = _build_entities(
            parsed,
            source_url=page.url,
            valid_attributes=analysis.attributes,
        )
        logger.info(f"[Extractor] {page.url[:70]} -> {len(entities)} entities")
        return entities

    except Exception as e:
        logger.warning(f"[Extractor] Skipping {page.url[:70]}: {e}")
        return []


async def extract_entities(
    pages: list[ScrapedPage],
    analysis: QueryAnalysis,
    llm: BaseLLMProvider,
    extraction_llm: BaseLLMProvider | None = None,
) -> list[Entity]:
    """
    Extract entities from all pages sequentially.

    Args:
        pages: scraped pages
        analysis: schema from query analyzer (entity_type + attributes)
        llm: default LLM provider
        extraction_llm: optional separate model for extraction.
                        Pass a different OllamaProvider to use a different
                        model just for this step.

    Returns:
        flat list of all entities across all pages (duplicates included —
        aggregator deduplicates in the next step)
    """
    active_llm = extraction_llm if extraction_llm is not None else llm

    logger.info(
        f"[Extractor] Processing {len(pages)} pages sequentially "
        f"using {active_llm.provider_name}/{active_llm.model_name}"
    )

    all_entities: list[Entity] = []

    for i, page in enumerate(pages, 1):
        logger.info(f"[Extractor] Page {i}/{len(pages)}: {page.url[:70]}")
        entities = await _extract_from_page(page, analysis, active_llm)
        all_entities.extend(entities)

    logger.info(f"[Extractor] Done — {len(all_entities)} total entities")
    return all_entities