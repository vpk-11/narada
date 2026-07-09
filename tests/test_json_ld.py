"""Tests for core/json_ld.py — schema.org structured data extraction."""

from core.json_ld import build_entities, parse_json_ld_blocks

_ORG_HTML = """
<html><head>
<script type="application/ld+json">
{"@context": "https://schema.org", "@type": "Organization", "name": "Abridge",
 "foundingDate": "2018", "description": "AI medical scribe for clinicians.",
 "address": {"@type": "PostalAddress", "streetAddress": "123 Main St",
             "addressLocality": "Pittsburgh", "addressRegion": "PA"}}
</script>
</head><body></body></html>
"""

_IRRELEVANT_HTML = """
<html><head>
<script type="application/ld+json">
{"@context": "https://schema.org", "@type": "BreadcrumbList", "name": "nav"}
</script>
</head></html>
"""

_GRAPH_HTML = """
<html><head>
<script type="application/ld+json">
{"@context": "https://schema.org", "@graph": [
  {"@type": "WebPage", "name": "Home"},
  {"@type": "LocalBusiness", "name": "Nabla", "telephone": "555-1234"}
]}
</script>
</head></html>
"""

_MALFORMED_HTML = """
<html><head>
<script type="application/ld+json">{not valid json</script>
</head></html>
"""


def test_parses_relevant_organization_block():
    items = parse_json_ld_blocks(_ORG_HTML)
    assert len(items) == 1
    assert items[0]["name"] == "Abridge"


def test_filters_out_irrelevant_types():
    assert parse_json_ld_blocks(_IRRELEVANT_HTML) == []


def test_flattens_at_graph_and_filters_within_it():
    items = parse_json_ld_blocks(_GRAPH_HTML)
    assert len(items) == 1
    assert items[0]["name"] == "Nabla"


def test_malformed_json_is_skipped_not_raised():
    assert parse_json_ld_blocks(_MALFORMED_HTML) == []


def test_build_entities_maps_fields_to_matching_attributes():
    items = parse_json_ld_blocks(_ORG_HTML)
    entities = build_entities(items, url="https://example.com", valid_attributes=["founded", "headquarters", "what_they_do"])
    assert len(entities) == 1
    entity = entities[0]
    assert entity.name == "Abridge"
    assert entity.attributes["founded"].value == "2018"
    assert entity.attributes["founded"].confidence == 1.0
    assert "Pittsburgh" in entity.attributes["headquarters"].value
    assert "clinicians" in entity.attributes["what_they_do"].value.lower()


def test_build_entities_skips_when_no_attribute_overlap():
    items = parse_json_ld_blocks(_ORG_HTML)
    entities = build_entities(items, url="u", valid_attributes=["stock_ticker", "employee_count"])
    assert entities == []


def test_build_entities_skips_item_with_no_name():
    items = [{"@type": "Organization", "foundingDate": "2018"}]
    entities = build_entities(items, url="u", valid_attributes=["founded"])
    assert entities == []
