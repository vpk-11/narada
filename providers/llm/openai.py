"""
providers/llm/openai.py

OpenAI LLM provider.
Uses the /v1/chat/completions endpoint.
Set OPENAI_API_KEY in .env or pass via request headers.
"""

import logging

import httpx

from providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

_OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
_TIMEOUT_SECONDS = 60


class OpenAIProvider(BaseLLMProvider):

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    async def complete(self, prompt: str, system: str = "", **kwargs) -> str:
        if not self._api_key:
            raise ValueError(
                "OpenAI API key is missing. "
                "Add your OpenAI API key in the Settings sidebar."
            )

        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.1,
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                response = await client.post(_OPENAI_API_URL, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error(f"[OpenAI] HTTP {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"[OpenAI] Completion failed: {e}")
            raise
