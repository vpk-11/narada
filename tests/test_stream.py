"""Tests for POST /api/search/stream: event order and parity with POST /api/search."""

import json
import types

import pytest
from fastapi.testclient import TestClient

import api.routes as routes
import core.pipeline as pipeline
from core.models import CellValue, Entity, QueryAnalysis, ScrapedPage, SearchResult
from main import app

ENTITY = Entity(
    name="Abridge",
    attributes={"founded": CellValue(value="2018", source_url="https://e.com", source_quote="founded in 2018")},
)


@pytest.fixture
def client(monkeypatch):
    llm = types.SimpleNamespace(provider_name="fake", model_name="m")
    search = types.SimpleNamespace(provider_name="fake")

    async def analyze(query, llm):
        return QueryAnalysis(entity_type="company", attributes=["founded"], search_queries=["q"])

    async def searches(**kw):
        return [SearchResult(url="https://e.com", title="t", snippet="s")], []

    async def scrape(**kw):
        return [ScrapedPage(url="https://e.com", title="t", content="founded in 2018")]

    async def extract(**kw):
        return [ENTITY.model_copy(deep=True)]

    async def validate(entities, **kw):
        return entities

    monkeypatch.setattr(pipeline, "analyze_query", analyze)
    monkeypatch.setattr(pipeline, "_run_searches", searches)
    monkeypatch.setattr(pipeline, "scrape_pages", scrape)
    monkeypatch.setattr(pipeline, "extract_entities", extract)
    monkeypatch.setattr(pipeline, "validate_entities", validate)
    for name in ("get_query_analyzer_llm", "get_extraction_llm", "get_validator_llm"):
        monkeypatch.setattr(pipeline, name, lambda s, llm=llm: llm)
    monkeypatch.setattr(routes, "get_search_provider", lambda s: search)
    return TestClient(app)


def _parse(text: str) -> list[dict]:
    return [json.loads(line[len("data: "):]) for line in text.splitlines() if line.startswith("data: ")]


def test_event_order_and_final_equals_non_streamed(client):
    body = {"query": "ai startups", "refresh": True}
    events = _parse(client.post("/api/search/stream", json=body).text)

    assert [e["type"] for e in events] == [
        "step", "step", "step", "step", "rows", "step", "result",
    ]
    assert [e["step"] for e in events if e["type"] == "step"] == [
        "analyze", "search", "scrape", "extract", "validate",
    ]

    plain = client.post("/api/search", json=body).json()
    streamed = {"result": events[-1]["result"]}
    for payload in (plain, streamed):
        payload["result"]["metadata"].pop("duration_seconds")
    assert streamed == plain


def test_error_event_carries_message_only(client, monkeypatch):
    async def boom(query, llm):
        raise RuntimeError("secret-key-material")

    monkeypatch.setattr(pipeline, "analyze_query", boom)
    events = _parse(client.post("/api/search/stream", json={"query": "x", "refresh": True}).text)
    assert events[-1]["type"] == "error"
    assert "secret-key-material" not in events[-1]["detail"]
