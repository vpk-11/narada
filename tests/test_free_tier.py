"""Tests for the production free tier: quota caps, day rollover, and route enforcement."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import api.free_tier as free_tier
import api.routes as routes
from api.free_tier import FreeTierQuota
from config import Settings
from core.models import PipelineMetadata, PipelineResult
from main import app

BODY = {"query": "ai startups", "refresh": True}


def test_per_ip_cap_then_other_ip_still_served():
    q = FreeTierQuota()
    q.consume("a", 1, 10)
    with pytest.raises(HTTPException) as e:
        q.consume("a", 1, 10)
    assert e.value.status_code == 429 and "free searches" in e.value.detail
    q.consume("b", 1, 10)


def test_global_cap_blocks_all_ips_with_distinct_message():
    q = FreeTierQuota()
    q.consume("a", 5, 1)
    with pytest.raises(HTTPException) as e:
        q.consume("b", 5, 1)
    assert e.value.status_code == 429 and "capacity" in e.value.detail


def test_day_rollover_resets(monkeypatch):
    q = FreeTierQuota()
    q.consume("a", 1, 1)
    monkeypatch.setattr(free_tier, "_today", lambda: "2999-01-01")
    assert q.remaining("a", 1, 1) == 1
    q.consume("a", 1, 1)


def _prod_settings(**kw) -> Settings:
    base = dict(
        environment="production", fallback_allow=True, free_tier_per_ip_daily=1,
        free_tier_global_daily=5, llm_model="groq/m", search_provider="tavily",
        query_analyzer_model="", extraction_model="", validator_model="",
    )
    return Settings(**{**base, **kw})


@pytest.fixture
def client(monkeypatch):
    async def fake_pipeline(**kw):
        return PipelineResult(
            query="q", entity_type="company", attributes=[], entities=[],
            metadata=PipelineMetadata(
                search_provider="fake", llm_provider="fake", llm_model="m",
                pages_scraped=0, duration_seconds=0.0,
            ),
        )

    monkeypatch.setattr(routes, "run_pipeline", fake_pipeline)
    monkeypatch.setattr(routes, "get_search_provider", lambda s: object())
    monkeypatch.setattr(routes, "quota", FreeTierQuota())
    monkeypatch.setattr(routes, "get_settings", lambda: _prod_settings())
    return TestClient(app)


def test_keyless_request_uses_then_exhausts_free_tier(client):
    assert client.post("/api/search", json=BODY).status_code == 200
    r = client.post("/api/search", json=BODY)
    assert r.status_code == 429 and "free searches" in r.json()["detail"]


def test_stream_route_shares_the_same_quota(client):
    assert client.post("/api/search/stream", json=BODY).status_code == 200
    assert client.post("/api/search/stream", json=BODY).status_code == 429


def test_own_keys_bypass_quota(client):
    headers = {"x-groq-api-key": "g", "x-tavily-api-key": "t"}
    for _ in range(3):
        assert client.post("/api/search", json=BODY, headers=headers).status_code == 200


def test_one_missing_key_still_counts(client):
    headers = {"x-groq-api-key": "g"}  # no tavily key
    assert client.post("/api/search", json=BODY, headers=headers).status_code == 200
    assert client.post("/api/search", json=BODY, headers=headers).status_code == 429


def test_fallback_off_in_production_rejects_keyless(client, monkeypatch):
    monkeypatch.setattr(routes, "get_settings", lambda: _prod_settings(fallback_allow=False))
    assert client.post("/api/search", json=BODY).status_code == 403


def test_development_is_not_enforced(client, monkeypatch):
    monkeypatch.setattr(routes, "get_settings", lambda: _prod_settings(environment="development"))
    for _ in range(3):
        assert client.post("/api/search", json=BODY).status_code == 200


def test_server_config_reports_remaining(client):
    assert client.get("/api/server-config").json()["free_searches_remaining"] == 1
    client.post("/api/search", json=BODY)
    assert client.get("/api/server-config").json()["free_searches_remaining"] == 0


def test_client_ip_uses_trusted_hop_not_spoofable_left_entry(client):
    # Spoofed left entry must not buy a fresh quota bucket.
    h1 = {"x-forwarded-for": "1.1.1.1, 9.9.9.9"}
    h2 = {"x-forwarded-for": "2.2.2.2, 9.9.9.9"}
    assert client.post("/api/search", json=BODY, headers=h1).status_code == 200
    assert client.post("/api/search", json=BODY, headers=h2).status_code == 429
