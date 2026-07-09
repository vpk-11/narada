"""Tests for agents/validator.py — noise filtering and fail-open behavior."""

import pytest

from agents.validator import _normalize, _parse_valid_names, validate_entities
from core.models import CellValue, Entity, QueryAnalysis
from providers.base import BaseLLMProvider


class _FakeLLM(BaseLLMProvider):
    def __init__(self, response: str = "", raises: bool = False):
        self._response = response
        self._raises = raises

    async def complete(self, prompt: str, system: str = "", **kwargs) -> str:
        if self._raises:
            raise RuntimeError("provider unavailable")
        return self._response

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return "fake-model"


def _entity(name: str) -> Entity:
    return Entity(name=name, attributes={"founded": CellValue(value="2018", source_url="u")})


def _analysis() -> QueryAnalysis:
    return QueryAnalysis(
        original_query="AI startups in healthcare",
        entity_type="company",
        attributes=["founded"],
        search_queries=["q"],
    )


def test_parse_valid_names_extracts_list():
    raw = '{"valid_names": ["Abridge", "Nabla"]}'
    assert _parse_valid_names(raw) == ["Abridge", "Nabla"]


def test_parse_valid_names_handles_malformed_json():
    assert _parse_valid_names("not json at all") == []


def test_normalize_lowercases_and_strips():
    assert _normalize("  Abridge  ") == "abridge"


async def test_validate_entities_filters_to_valid_names():
    entities = [_entity("Abridge"), _entity("Random Fintech Co")]
    llm = _FakeLLM(response='{"valid_names": ["Abridge"]}')
    result = await validate_entities(entities, _analysis(), llm)
    assert [e.name for e in result] == ["Abridge"]


async def test_validate_entities_keeps_all_when_llm_returns_no_names():
    entities = [_entity("Abridge"), _entity("Nabla")]
    llm = _FakeLLM(response='{"valid_names": []}')
    result = await validate_entities(entities, _analysis(), llm)
    assert len(result) == 2


async def test_validate_entities_fails_open_on_llm_error():
    entities = [_entity("Abridge"), _entity("Nabla")]
    llm = _FakeLLM(raises=True)
    result = await validate_entities(entities, _analysis(), llm)
    assert len(result) == 2


async def test_validate_entities_short_circuits_on_empty_input():
    llm = _FakeLLM(response='{"valid_names": []}')
    result = await validate_entities([], _analysis(), llm)
    assert result == []
