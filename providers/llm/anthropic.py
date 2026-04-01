"""
providers/llm/anthropic.py

Anthropic LLM provider.
Uses the /v1/messages endpoint.
Set ANTHROPIC_API_KEY in .env or pass via request headers.
"""

import logging

import httpx

from providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"
_TIMEOUT_SECONDS = 60


class AnthropicProvider(BaseLLMProvider):

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set.")
        self._api_key = api_key
        self._model = model

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model

    async def complete(self, prompt: str, system: str = "", **kwargs) -> str:
        payload: dict = {
            "model": self._model,
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                response = await client.post(_ANTHROPIC_API_URL, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data["content"][0]["text"]
        except httpx.HTTPStatusError as e:
            logger.error(f"[Anthropic] HTTP {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"[Anthropic] Completion failed: {e}")
            raise
