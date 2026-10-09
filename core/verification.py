"""
core/verification.py

Checks that each cell's source_quote actually appears in the page it cites.

The extractor asks the LLM for an exact quote per value, but nothing forces
the model to comply. A quote the model paraphrased or invented would make the
per-cell provenance claim false, so every LLM-extracted cell is checked
against the scraped text of its own source_url.

Match order: normalized substring, then a fuzzy fallback (longest common
block covering most of the quote) to tolerate whitespace, punctuation and
small wording drift. A cell with no quote, or no match, is marked unverified.
"""

import re
import unicodedata
from difflib import SequenceMatcher

from core.models import Entity, ScrapedPage

# Share of the quote that must appear as one contiguous block in the page.
_FUZZY_MIN_COVERAGE = 0.9
# The quote is LLM output shaped by untrusted page text; cap its length so the
# fuzzy match cost stays bounded (cost grows with quote length x page length).
_MAX_QUOTE_CHARS = 500


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"[\W_]+", " ", text).strip()


def quote_in_text(quote: str, text: str) -> bool:
    """True if quote appears in text (normalized substring, then fuzzy fallback)."""
    return _quote_in_normalized(quote, _normalize(text))


def _quote_in_normalized(quote: str, t: str) -> bool:
    q = _normalize(quote)[:_MAX_QUOTE_CHARS]
    if not q:
        return False
    if q in t:
        return True
    match = SequenceMatcher(None, q, t, autojunk=False).find_longest_match(0, len(q), 0, len(t))
    return match.size / len(q) >= _FUZZY_MIN_COVERAGE


def verify_entities(entities: list[Entity], pages: list[ScrapedPage]) -> None:
    """
    Set CellValue.verified in place. Cells already verified (JSON-LD, built
    from structured page data) are left alone. A cell whose source_url is not
    among pages stays unverified.
    """
    text_by_url = {p.url: _normalize(p.content) for p in pages}
    for entity in entities:
        for cell in entity.attributes.values():
            if cell.verified:
                continue
            text = text_by_url.get(cell.source_url)
            cell.verified = text is not None and _quote_in_normalized(cell.source_quote, text)


def verified_rate(entities: list[Entity]) -> float:
    """Fraction of cells with verified=True; 0.0 for an empty table."""
    cells = [c for e in entities for c in e.attributes.values()]
    return sum(c.verified for c in cells) / len(cells) if cells else 0.0
