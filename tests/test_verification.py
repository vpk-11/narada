"""Tests for core/verification.py: quote-in-page checks and the verified-cell rate."""

from core.models import CellValue, Entity, ScrapedPage
from core.verification import quote_in_text, verified_rate, verify_entities

PAGE = ScrapedPage(
    url="https://example.com/a",
    title="A",
    content="Abridge was founded in 2018 by Shiv Rao.\n\nIt is based in Pittsburgh, Pennsylvania.",
)


def _entity(quote: str, url: str = PAGE.url) -> Entity:
    return Entity(name="Abridge", attributes={"founded": CellValue(value="2018", source_url=url, source_quote=quote)})


def test_exact_quote_verified():
    assert quote_in_text("founded in 2018 by Shiv Rao", PAGE.content)


def test_whitespace_punctuation_and_case_ignored():
    assert quote_in_text("ABRIDGE was   founded in 2018, by Shiv Rao", PAGE.content)


def test_fuzzy_tolerates_small_drift():
    assert quote_in_text("Abridge was founded in 2018 by Shiv Rao Jr", PAGE.content)


def test_invented_quote_rejected():
    assert not quote_in_text("Abridge raised 500 million dollars last year", PAGE.content)


def test_empty_quote_rejected():
    assert not quote_in_text("", PAGE.content)


def test_verify_entities_marks_cells():
    good, bad = _entity("founded in 2018"), _entity("made up sentence about nothing")
    verify_entities([good, bad], [PAGE])
    assert good.attributes["founded"].verified
    assert not bad.attributes["founded"].verified


def test_cell_with_unknown_source_url_unverified():
    e = _entity("founded in 2018", url="https://other.com")
    verify_entities([e], [PAGE])
    assert not e.attributes["founded"].verified


def test_prior_verified_cell_untouched():
    cell = CellValue(value="x", source_url="https://other.com", source_quote="JSON-LD name: x", verified=True)
    e = Entity(name="E", attributes={"a": cell})
    verify_entities([e], [PAGE])
    assert cell.verified


def test_verified_rate():
    a, b = _entity("founded in 2018"), _entity("nope nope nope")
    verify_entities([a, b], [PAGE])
    assert verified_rate([a, b]) == 0.5
    assert verified_rate([]) == 0.0


def test_overlong_quote_is_capped():
    # Only the first 500 normalized chars of a quote are compared.
    assert quote_in_text("word " * 1000, "word " * 300)
