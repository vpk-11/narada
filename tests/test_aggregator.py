"""
Tests for agents/aggregator.py — fuzzy name matching and attribute
conflict resolution. These are the two things a competing project's
merge logic did that Narada's exact-match-only version didn't.
"""

from agents.aggregator import _merge_attributes, _name_similarity, _normalize_name, aggregate_entities
from core.models import CellValue, Entity


def _cell(value: str, confidence: float = 0.5, url: str = "https://example.com") -> CellValue:
    return CellValue(value=value, source_url=url, confidence=confidence)


def test_normalize_name_strips_punctuation_and_case():
    assert _normalize_name("OpenAI, Inc.") == _normalize_name("openai inc")


def test_exact_name_match_merges():
    entities = [
        Entity(name="Abridge", attributes={"founded": _cell("2018")}),
        Entity(name="Abridge", attributes={"headquarters": _cell("Pittsburgh")}),
    ]
    result = aggregate_entities(entities)
    assert len(result) == 1
    assert set(result[0].attributes) == {"founded", "headquarters"}


def test_fuzzy_name_match_merges_punctuation_drift():
    entities = [
        Entity(name="Abridge, Inc.", attributes={"founded": _cell("2018")}),
        Entity(name="Abridge Inc", attributes={"headquarters": _cell("Pittsburgh")}),
    ]
    assert _name_similarity(_normalize_name("Abridge, Inc."), _normalize_name("Abridge Inc")) >= 0.75
    result = aggregate_entities(entities)
    assert len(result) == 1


def test_dissimilar_names_stay_separate():
    entities = [
        Entity(name="Abridge", attributes={"founded": _cell("2018")}),
        Entity(name="Nabla", attributes={"founded": _cell("2019")}),
    ]
    result = aggregate_entities(entities)
    assert len(result) == 2


def test_merge_attributes_unions_disjoint_keys():
    existing = {"founded": _cell("2018")}
    incoming = {"headquarters": _cell("Pittsburgh")}
    merged = _merge_attributes(existing, incoming)
    assert set(merged) == {"founded", "headquarters"}


def test_merge_attributes_prefers_non_empty_value():
    existing = {"founded": _cell("", confidence=0.9)}
    incoming = {"founded": _cell("2018", confidence=0.1)}
    merged = _merge_attributes(existing, incoming)
    assert merged["founded"].value == "2018"


def test_merge_attributes_prefers_higher_confidence_on_conflict():
    existing = {"founded": _cell("2017", confidence=0.4)}
    incoming = {"founded": _cell("2018", confidence=0.9)}
    merged = _merge_attributes(existing, incoming)
    assert merged["founded"].value == "2018"


def test_merge_attributes_keeps_existing_on_equal_confidence():
    existing = {"founded": _cell("2017", confidence=0.5)}
    incoming = {"founded": _cell("2018", confidence=0.5)}
    merged = _merge_attributes(existing, incoming)
    assert merged["founded"].value == "2017"


def test_aggregate_sorts_most_complete_first():
    entities = [
        Entity(name="A", attributes={"x": _cell("1")}),
        Entity(name="B", attributes={"x": _cell("1"), "y": _cell("2"), "z": _cell("3")}),
    ]
    result = aggregate_entities(entities)
    assert result[0].name == "B"
    assert result[1].name == "A"
