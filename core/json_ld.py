"""
core/json_ld.py

Parses schema.org JSON-LD blocks embedded in a page's HTML and maps them
directly to narada's dynamic attribute schema where possible.

Many business/product pages already embed clean structured data for Google's
search snippets — reading it directly is faster and more accurate than asking
an LLM to re-derive facts that are already sitting there as data. This is a
pre-LLM step, not a replacement: pages with no JSON-LD, or JSON-LD missing
the requested attributes, still go through the normal LLM extraction path in
agents/extractor.py.
"""

import json
import logging

from bs4 import BeautifulSoup

from core.models import CellValue, Entity

logger = logging.getLogger(__name__)

# schema.org @type values worth treating as a candidate entity. Not exhaustive —
# schema.org has hundreds of types (Article, BreadcrumbList, WebPage, ...) that
# don't represent a searchable entity and are deliberately excluded.
_RELEVANT_TYPE_KEYWORDS = (
    "organization", "localbusiness", "corporation", "product",
    "person", "restaurant", "store", "software",
)

# Maps schema.org property names to keywords that likely appear in a
# dynamically-generated attribute name asking for the same fact.
_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "foundingDate": ("founded", "founding", "established", "since"),
    "telephone": ("phone", "telephone", "contact"),
    "email": ("email",),
    "address": ("address", "location", "headquarters", "hq"),
    "description": ("description", "about", "summary", "overview", "what"),
    "priceRange": ("price", "pricing", "cost"),
    "url": ("website", "url"),
}


def _flatten_json_ld(raw: object) -> list[dict]:
    """schema.org JSON-LD can be a single object, a list, or use @graph nesting."""
    items: list[dict] = []
    if isinstance(raw, dict):
        if isinstance(raw.get("@graph"), list):
            items.extend(i for i in raw["@graph"] if isinstance(i, dict))
        else:
            items.append(raw)
    elif isinstance(raw, list):
        for entry in raw:
            items.extend(_flatten_json_ld(entry))
    return items


def _is_relevant_type(item: dict) -> bool:
    type_value = item.get("@type", "")
    types = type_value if isinstance(type_value, list) else [type_value]
    joined = " ".join(str(t) for t in types).lower()
    return any(keyword in joined for keyword in _RELEVANT_TYPE_KEYWORDS)


def _stringify(value: object) -> str:
    if isinstance(value, dict):
        # Common case: a PostalAddress object — join the readable parts.
        parts = [
            str(value.get(k, "")).strip()
            for k in ("streetAddress", "addressLocality", "addressRegion", "postalCode", "addressCountry")
            if value.get(k)
        ]
        return ", ".join(parts) if parts else ""
    if isinstance(value, list):
        return ", ".join(_stringify(v) for v in value[:3] if _stringify(v))
    return str(value).strip()


def parse_json_ld_blocks(html: str) -> list[dict]:
    """Extract and parse every <script type="application/ld+json"> block on the page."""
    soup = BeautifulSoup(html, "lxml")
    items: list[dict] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            raw = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        items.extend(_flatten_json_ld(raw))
    return [i for i in items if _is_relevant_type(i)]


def _build_entity(item: dict, url: str, valid_attributes: list[str]) -> Entity | None:
    """
    Build an Entity directly from a JSON-LD item, mapping schema.org fields to
    whichever requested attribute names look like they're asking for the same
    fact. Cells built this way get confidence=1.0 — it's structured data the
    page author published, not an LLM inference, so it wins merge conflicts
    against an LLM-extracted value for the same attribute (see
    agents/aggregator.py's confidence-based tie-break).
    """
    name = str(item.get("name", "")).strip()
    if not name:
        return None

    attributes: dict[str, CellValue] = {}
    for field, aliases in _FIELD_ALIASES.items():
        raw_value = item.get(field)
        if not raw_value:
            continue
        value = _stringify(raw_value)
        if not value:
            continue
        for attr in valid_attributes:
            if attr in attributes:
                continue
            attr_norm = attr.lower().replace("_", " ")
            if any(alias in attr_norm for alias in aliases):
                attributes[attr] = CellValue(
                    value=value,
                    source_url=url,
                    source_quote=f"JSON-LD {field}: {value}",
                    confidence=1.0,
                )

    if not attributes:
        return None

    return Entity(name=name, attributes=attributes)


def build_entities(items: list[dict], url: str, valid_attributes: list[str]) -> list[Entity]:
    """
    Build Entities from already-parsed JSON-LD items (see parse_json_ld_blocks).
    Returns [] if none of the items are a relevant @type or none of their
    fields map onto any requested attribute — the normal LLM extraction path
    in agents/extractor.py handles those cases.
    """
    entities = []
    for item in items:
        entity = _build_entity(item, url, valid_attributes)
        if entity is not None:
            entities.append(entity)
    if entities:
        logger.info(f"[JSON-LD] {url[:70]} -> {len(entities)} entities from structured data")
    return entities
