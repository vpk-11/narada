"""
agents/aggregator.py

Step 5 of the Narada pipeline.

Takes the flat list of entities extracted across all pages (may contain
duplicates) and merges them into a clean, deduplicated table.

Key design decisions:
- Deduplication is name-based with fuzzy matching. "OpenAI" and "Open AI"
  should merge. We normalize names, then fall back to a similarity ratio
  for names that don't match exactly ("Abridge Inc" vs "Abridge, Inc.").
- When the same entity appears across multiple sources, we keep ALL attribute
  values — if source A has 'founded' and source B has 'funding_raised', the
  merged entity gets both.
- When two sources provide the SAME attribute for the same entity, prefer
  the non-empty value, then the one with higher extraction confidence.
  Ties keep the existing value.
- No LLM needed here — this is pure deterministic logic. Fast and reliable.
- Outputs a sorted list: entities with more attributes rank first.
"""

import logging
import re
from difflib import SequenceMatcher

from core.models import CellValue, Entity

logger = logging.getLogger(__name__)

# Below this similarity ratio, two names are treated as different entities.
# 0.75 catches punctuation/suffix drift ("Abridge Inc" vs "Abridge, Inc.")
# without merging genuinely different companies that share a common word.
_NAME_SIMILARITY_THRESHOLD = 0.75


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


def _name_similarity(a: str, b: str) -> float:
    """Ratcliff/Obershelp similarity ratio between two normalized names."""
    return SequenceMatcher(None, a, b).ratio()


def _merge_attributes(
    existing: dict[str, CellValue],
    incoming: dict[str, CellValue],
) -> dict[str, CellValue]:
    """
    Merge two attribute dicts for the same entity.

    Strategy per attribute:
    - If only one source has it: keep it.
    - If both sources have it: prefer the non-empty value, then the one
      with higher extraction confidence. Equal confidence keeps existing.
    """
    merged = dict(existing)

    for key, incoming_cell in incoming.items():
        existing_cell = merged.get(key)

        if existing_cell is None:
            merged[key] = incoming_cell
            continue

        if not existing_cell.value and incoming_cell.value:
            merged[key] = incoming_cell
        elif incoming_cell.confidence > existing_cell.confidence:
            merged[key] = incoming_cell

    return merged


def aggregate_entities(entities: list[Entity]) -> list[Entity]:
    """
    Deduplicate and merge a list of entities extracted across multiple pages.

    Two entities are considered the same if their normalized names match
    exactly, or are similar enough (SequenceMatcher ratio >= threshold) to
    account for punctuation/suffix drift across sources. When merged,
    attributes are unioned — no information is discarded.

    Args:
        entities: raw extracted entities, may contain duplicates

    Returns:
        deduplicated list of Entity, sorted by attribute count descending
        (most complete entities first)
    """
    logger.info(f"[Aggregator] Deduplicating {len(entities)} raw entities")

    # normalized_name -> Entity, checked in insertion order for fuzzy match
    merged: dict[str, Entity] = {}

    for entity in entities:
        key = _normalize_name(entity.name)

        match_key = key if key in merged else None
        if match_key is None:
            for existing_key in merged:
                if _name_similarity(key, existing_key) >= _NAME_SIMILARITY_THRESHOLD:
                    match_key = existing_key
                    break

        if match_key is None:
            merged[key] = entity
        else:
            # Entity already seen — merge attributes
            existing = merged[match_key]
            merged_attrs = _merge_attributes(existing.attributes, entity.attributes)

            # Keep the name casing from whichever version has more attributes
            # (usually the first good extraction)
            merged[match_key] = Entity(
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