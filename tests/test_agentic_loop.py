"""Tests for core/agentic_loop.py — gap-ratio computation and gap identification."""

from core.agentic_loop import _identify_gaps, compute_gap_ratio
from core.models import CellValue, Entity


def _cell(value: str = "x") -> CellValue:
    return CellValue(value=value, source_url="https://example.com")


def test_gap_ratio_zero_when_fully_populated():
    entities = [Entity(name="A", attributes={"founded": _cell(), "hq": _cell()})]
    assert compute_gap_ratio(entities, ["founded", "hq"]) == 0.0


def test_gap_ratio_one_when_no_attributes_present():
    entities = [Entity(name="A", attributes={})]
    assert compute_gap_ratio(entities, ["founded", "hq"]) == 1.0


def test_gap_ratio_partial():
    entities = [
        Entity(name="A", attributes={"founded": _cell()}),   # 1/2 filled
        Entity(name="B", attributes={}),                      # 0/2 filled
    ]
    # 1 filled cell out of 4 total -> gap ratio 0.75
    assert compute_gap_ratio(entities, ["founded", "hq"]) == 0.75


def test_gap_ratio_empty_inputs_are_zero_not_error():
    assert compute_gap_ratio([], ["founded"]) == 0.0
    assert compute_gap_ratio([Entity(name="A", attributes={})], []) == 0.0


def test_identify_gaps_skips_complete_entities():
    entities = [
        Entity(name="Complete", attributes={"founded": _cell(), "hq": _cell()}),
        Entity(name="Incomplete", attributes={"founded": _cell()}),
    ]
    gaps = _identify_gaps(entities, ["founded", "hq"])
    names = [g["name"] for g in gaps]
    assert "Complete" not in names
    assert "Incomplete" in names


def test_identify_gaps_worst_first():
    entities = [
        Entity(name="OneMissing", attributes={"founded": _cell(), "hq": _cell()}),
        Entity(name="AllMissing", attributes={}),
    ]
    gaps = _identify_gaps(entities, ["founded", "hq", "revenue"])
    assert gaps[0]["name"] == "AllMissing"


def test_identify_gaps_caps_at_five():
    entities = [Entity(name=f"E{i}", attributes={}) for i in range(10)]
    gaps = _identify_gaps(entities, ["founded"])
    assert len(gaps) == 5
