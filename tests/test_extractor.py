"""Tests for agents/extractor.py — cell building, junk-value filtering, and schema drift tolerance."""

from agents.extractor import _build_cell, _build_entities, _is_valid_value


def test_is_valid_value_rejects_known_junk():
    for junk in ["none", "N/A", "unknown", "not found", "-", ""]:
        assert not _is_valid_value(junk)


def test_is_valid_value_accepts_real_values():
    assert _is_valid_value("2018")
    assert _is_valid_value("Pittsburgh, PA")


def test_build_cell_parses_full_object_shape():
    raw = {"value": "2018", "source_quote": "founded in 2018", "confidence": 0.95}
    cell = _build_cell(raw, source_url="https://example.com")
    assert cell.value == "2018"
    assert cell.source_quote == "founded in 2018"
    assert cell.confidence == 0.95
    assert cell.source_url == "https://example.com"


def test_build_cell_clamps_out_of_range_confidence():
    cell = _build_cell({"value": "x", "confidence": 5.0}, source_url="u")
    assert cell.confidence == 1.0
    cell = _build_cell({"value": "x", "confidence": -2.0}, source_url="u")
    assert cell.confidence == 0.0


def test_build_cell_rejects_junk_value():
    assert _build_cell({"value": "N/A", "confidence": 0.9}, source_url="u") is None


def test_build_cell_tolerates_flat_string_schema_drift():
    # Model ignored the {value, source_quote, confidence} shape and returned a bare string.
    cell = _build_cell("2018", source_url="https://example.com")
    assert cell.value == "2018"
    assert cell.confidence == 0.5
    assert cell.source_quote == ""


def test_build_entities_drops_entity_with_no_valid_attributes():
    data = {
        "entities": [
            {"name": "Ghost Co", "attributes": {"founded": {"value": "N/A", "confidence": 0.1}}},
        ]
    }
    result = _build_entities(data, source_url="u", valid_attributes=["founded"])
    assert result == []


def test_build_entities_keeps_entity_with_valid_attributes():
    data = {
        "entities": [
            {
                "name": "Abridge",
                "attributes": {
                    "founded": {"value": "2018", "source_quote": "in 2018", "confidence": 0.9},
                    "extra_unrequested_field": {"value": "should be dropped", "confidence": 0.9},
                },
            },
        ]
    }
    result = _build_entities(data, source_url="u", valid_attributes=["founded"])
    assert len(result) == 1
    assert set(result[0].attributes) == {"founded"}
