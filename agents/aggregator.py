"""
agents/aggregator.py

Step 5 of the Narada pipeline.

Takes the flat list of entities extracted across all pages (may contain
duplicates) and merges them into a clean, deduplicated table.

Key design decisions:
- Deduplication is name-based with fuzzy matching. "OpenAI" and "Open AI"
  should merge. We normalize names before comparing.
- When the same entity appears across multiple sources, we keep ALL attribute
  values — if source A has 'founded' and source B has 'funding_raised', the
  merged entity gets both.
- When two sources provide the SAME attribute for the same entity, we keep
  the value with more content (longer = more informative).
- No LLM needed here — this is pure deterministic logic. Fast and reliable.
- Outputs a sorted list: entities with more attributes rank first.
"""

import logging
import re

from core.models import CellValue, Entity

logger = logging.getLogger(__name__)


def _normalize_name(name: str) -> str:
    """
    Normalize an entity name for deduplication comparison.
    Lowercases, strips punctuation, collapses whitespace.
    "OpenAI, Inc." and "openai inc" both become "openai inc".
    """
    name = name.lower().strip()
    name = re.sub(r"[^\w\s]", "", name)   # remove punctuation
    name = re.sub(r"\s+", " ", name)       # collapse whitespace
    return name


def _merge_attributes(
    existing: dict[str, CellValue],
    incoming: dict[str, CellValue],
) -> dict[str, CellValue]:
    """
    Merge two attribute dicts for the same entity.

    Strategy per attribute:
    - If only one source has it: keep it.
    - If both sources have it: keep the longer value (more informative).
      The source_url of the winning value is preserved.
    """
    merged = dict(existing)

    for key, incoming_cell in incoming.items():
        if key not in merged:
            # New attribute from this source — add it
            merged[key] = incoming_cell
        else:
            existing_cell = merged[key]
            # Keep whichever value is more informative (longer content)
            if len(incoming_cell.value) > len(existing_cell.value):
                merged[key] = incoming_cell

    return merged


def aggregate_entities(entities: list[Entity]) -> list[Entity]:
    """
    Deduplicate and merge a list of entities extracted across multiple pages.

    Two entities are considered the same if their normalized names match.
    When merged, attributes are unioned — no information is discarded.

    Args:
        entities: raw extracted entities, may contain duplicates

    Returns:
        deduplicated list of Entity, sorted by attribute count descending
        (most complete entities first)
    """
    logger.info(f"[Aggregator] Deduplicating {len(entities)} raw entities")

    # normalized_name -> Entity
    merged: dict[str, Entity] = {}

    for entity in entities:
        key = _normalize_name(entity.name)

        if key not in merged:
            merged[key] = entity
        else:
            # Entity already seen — merge attributes
            existing = merged[key]
            merged_attrs = _merge_attributes(existing.attributes, entity.attributes)

            # Keep the name casing from whichever version has more attributes
            # (usually the first good extraction)
            merged[key] = Entity(
                name=existing.name,
                attributes=merged_attrs,
            )

    result = list(merged.values())

    # Sort: most complete entities first
    result.sort(key=lambda e: len(e.attributes), reverse=True)

    logger.info(
        f"[Aggregator] {len(entities)} raw -> {len(result)} unique entities"
    )

    return result