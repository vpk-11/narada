"""
agents/extractor.py

Step 4 of the Narada pipeline.

For each page, sends content to the LLM and extracts structured entities.
Every attribute value is tagged with its source URL for full traceability.

Key design decisions:
- PRIMARY SUBJECT rule: only extract entities that are the main focus
  of the page, not entities mentioned in passing or as context.
- SEQUENTIAL processing — Ollama handles one request at a time locally.
- Pages are split into chunks (core/chunking.py) rather than truncated, so
  content past the old flat char cutoff still reaches the model.
- Robust JSON parser handles both {"entities":[...]} and bare [...] responses.
- Each attribute value carries a source_quote and confidence score, used by
  the aggregator to resolve conflicts when multiple sources disagree.
- _is_valid_value() filters out "None", "N/A", "unknown" etc before storage.
- Post-extraction filter drops entities with zero valid attributes.
- Accepts optional extraction_llm for multi-model setups.
"""

import logging

from core.chunking import chunk_text
from core.llm_json import parse_llm_json
from core.models import CellValue, Entity, QueryAnalysis, ScrapedPage
from providers.base import BaseLLMProvider
NUM_CTX_LARGE = 8192  # context window for extraction prompts that include page content

logger = logging.getLogger(__name__)

_MIN_ATTRIBUTES_TO_KEEP = 1

# A page is split into chunks rather than truncated, so content past the old
# 2500-char cutoff still reaches the model. Capped at 3 chunks per page to
# bound LLM calls on long pages — most useful content is in the first ~9000
# chars of a cleaned article anyway.
_CHUNK_MAX_CHARS = 3000
_CHUNK_OVERLAP_CHARS = 300
_MAX_CHUNKS_PER_PAGE = 3

_INVALID_VALUES = {
    "none", "n/a", "na", "not available", "not found", "unknown",
    "not mentioned", "no information", "no information provided",
    "not specified", "not stated", "not given", "not provided", "-", "",
    "no", "yes", "true", "false",  # model answering boolean instead of extracting
}

_INVALID_SUBSTRINGS = (
    "no founding date",
    "no information",
    "not provided",
    "not mentioned",
    "not available",
    "not found",
    "not specified",
    "no data",
    "mentioned as",
    "mentioned in",
    "referenced as",
)

_SYSTEM_PROMPT = """You are Narada, a precise data extraction agent.
You extract structured data about entities that are the PRIMARY SUBJECT of a web page.
You respond with valid JSON only. No prose, no markdown, no explanation.
"""

_PROMPT_TEMPLATE = """Extract structured data from this web page.

Original research query: {query}
Entity type we want: {entity_type}
Attributes to extract: {attributes}
Page URL: {url}

Page content:
---
{content}
---

CRITICAL RULES:
1. Only extract {entity_type} entities that ARE THE PRIMARY SUBJECT of this page.
   - A page about "Top AI Healthcare Startups" has startups as primary subjects.
   - A page about Abridge that mentions Epic Systems has ONLY Abridge as primary subject.
2. Do NOT extract entities that are merely:
   - Mentioned in passing or as context
   - Investors, funders, or venture capital firms
   - Customers or partners of the primary entity
   - Competitors mentioned briefly
   - Research firms, consulting companies, or media outlets
   - The publisher or author of this page (e.g. if the page is from "TechCrunch", do not extract "TechCrunch")
   - Blockchain, crypto, or Web3 companies unless the query specifically asks for them
3. For each primary entity, only include attributes with CLEAR evidence. No guessing.
4. If you cannot find a value for an attribute, OMIT it entirely. Never write null, None, or N/A.
5. Each attribute value must be a phrase or sentence, MAX 15 WORDS. Never paste a whole paragraph.
6. source_quote must be the exact sentence or clause from the page content that the value came from —
   copy it verbatim, do not paraphrase. If you cannot point to a specific quote, omit the attribute.
7. confidence is your certainty the value is correct and belongs to this entity, from 0.0 to 1.0.
   Use 0.9+ only when the text states the fact directly and unambiguously about this exact entity.
8. Extract AT MOST 5 entities from this page. If more than 5 are primary subjects, keep the 5 most
   clearly described.
9. If no primary {entity_type} entities are found, return {{"entities": []}}.

Every attribute value is an object with three fields: value, source_quote, confidence. Example shape:
{{
  "entities": [
    {{
      "name": "Abridge",
      "attributes": {{
        "founded": {{
          "value": "2018",
          "source_quote": "Abridge was founded in 2018 by Shiv Rao",
          "confidence": 0.95
        }},
        "headquarters": {{
          "value": "Pittsburgh, PA",
          "source_quote": "based in Pittsburgh, Pennsylvania",
          "confidence": 0.9
        }}
      }}
    }}
  ]
}}

Return this exact JSON shape for {entity_type} entities found on this page. JSON only. No other text.
"""


def _is_valid_value(val: str) -> bool:
    """
    Return False for junk values the model writes when it can't find something.
    Checks exact matches and substrings.
    """
    normalized = val.lower().strip()
    if normalized in _INVALID_VALUES:
        return False
    return not any(sub in normalized for sub in _INVALID_SUBSTRINGS)


def _parse_llm_json(raw: str) -> dict:
    """
    Parse JSON from LLM output.
    Handles {"entities":[...]} and bare [...] responses.
    """
    try:
        parsed = parse_llm_json(raw)
    except ValueError as e:
        logger.error(f"[Extractor] JSON parse error: {e}")
        raise

    if isinstance(parsed, list):
        logger.debug("[Extractor] LLM returned bare array — wrapping as entities object")
        return {"entities": parsed}

    if isinstance(parsed, dict):
        return parsed

    return {"entities": []}


def _build_cell(raw_val: object, source_url: str) -> CellValue | None:
    """
    Build a CellValue from one attribute's raw LLM output.

    Expected shape is {"value", "source_quote", "confidence"}. Tolerates a
    model that ignores the schema and returns a flat string instead — the
    LLM will occasionally drift, and rejecting the whole entity over one
    malformed attribute throws away otherwise-good data.
    """
    if isinstance(raw_val, dict):
        value = str(raw_val.get("value", "")).strip()
        if not value or not _is_valid_value(value):
            return None
        quote = str(raw_val.get("source_quote") or "").strip()
        try:
            confidence = float(raw_val.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))
        return CellValue(value=value, source_url=source_url, source_quote=quote, confidence=confidence)

    # Schema drift: model returned a bare string instead of the object shape.
    value = str(raw_val).strip()
    if not value or not _is_valid_value(value):
        return None
    return CellValue(value=value, source_url=source_url, confidence=0.5)


def _build_entities(
    data: dict,
    source_url: str,
    valid_attributes: list[str],
) -> list[Entity]:
    """
    Convert parsed LLM JSON into Entity objects.
    Attaches source_url to every CellValue — the traceability guarantee.
    Filters junk values and drops entities with no valid attributes.
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

        attributes: dict[str, CellValue] = {}
        for key, raw_val in raw_attrs.items():
            if key not in valid_attributes:
                continue
            cell = _build_cell(raw_val, source_url)
            if cell is not None:
                attributes[key] = cell

        if len(attributes) < _MIN_ATTRIBUTES_TO_KEEP:
            logger.debug(f"[Extractor] Dropping '{name}' — no valid attributes")
            continue

        entities.append(Entity(name=name, attributes=attributes))

    return entities


async def _extract_from_chunk(
    content: str,
    url: str,
    analysis: QueryAnalysis,
    llm: BaseLLMProvider,
) -> list[Entity]:
    """Extract entities from a single chunk of page content. Returns [] on failure."""
    prompt = _PROMPT_TEMPLATE.format(
        query=analysis.original_query if hasattr(analysis, "original_query") else "",
        entity_type=analysis.entity_type,
        attributes=", ".join(analysis.attributes),
        url=url,
        content=content,
    )

    try:
        raw = await llm.complete(
            prompt=prompt,
            system=_SYSTEM_PROMPT,
            num_ctx=NUM_CTX_LARGE,
        )
        parsed = _parse_llm_json(raw)
        return _build_entities(
            parsed,
            source_url=url,
            valid_attributes=analysis.attributes,
        )

    except Exception as e:
        logger.warning(f"[Extractor] Skipping chunk of {url[:70]}: {e}")
        return []


async def _extract_from_page(
    page: ScrapedPage,
    analysis: QueryAnalysis,
    llm: BaseLLMProvider,
) -> list[Entity]:
    """
    Extract entities from a page, chunk by chunk. A page longer than one
    chunk yields multiple LLM calls; entities from all chunks are pooled
    here and deduplicated later by the aggregator.
    """
    chunks = chunk_text(
        page.content,
        max_chars=_CHUNK_MAX_CHARS,
        overlap_chars=_CHUNK_OVERLAP_CHARS,
    )[:_MAX_CHUNKS_PER_PAGE]

    entities: list[Entity] = []
    for chunk in chunks:
        entities.extend(await _extract_from_chunk(chunk, page.url, analysis, llm))

    logger.info(
        f"[Extractor] {page.url[:70]} -> {len(entities)} entities from {len(chunks)} chunk(s)"
    )
    return entities


async def extract_entities(
    pages: list[ScrapedPage],
    analysis: QueryAnalysis,
    llm: BaseLLMProvider,
    extraction_llm: BaseLLMProvider | None = None,
) -> list[Entity]:
    """
    Extract entities from all pages sequentially.
    Sequential because Ollama handles one LLM request at a time locally.
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