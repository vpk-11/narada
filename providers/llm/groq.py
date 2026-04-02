"""
providers/llm/groq.py

Groq LLM provider.
Groq runs inference on custom LPU hardware — dramatically faster than
GPU-based APIs. Free tier: 14,400 requests/day.

Recommended models for Narada:
  llama-3.3-70b-versatile   — best quality, still very fast on Groq
  llama-3.1-8b-instant      — fastest, good for lightweight tasks
  qwen-qwq-32b              — strong reasoning, good for query analysis

Sign up: https://console.groq.com
Set GROQ_API_KEY in .env to use.
"""

import logging

import httpx

from providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

_GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
_TIMEOUT_SECONDS = 60  # Groq is fast — 60s is generous


class GroqProvider(BaseLLMProvider):

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def model_name(self) -> str:
        return self._model

    async def complete(self, prompt: str, system: str = "", **kwargs) -> str:
        """
        Send a chat completion request to Groq.
        Uses the OpenAI-compatible /v1/chat/completions endpoint.
        kwargs are accepted but ignored — Groq manages its own context.
        """
        if not self._api_key:
            raise ValueError(
                "Groq API key is missing. "
                "Add your Groq API key in the Settings sidebar."
            )

        messages: list[dict] = []

        if system:
            messages.append({"role": "system", "content": system})

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.1,  # low temperature for consistent structured output
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    _GROQ_API_URL,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]

        except httpx.HTTPStatusError as e:
            logger.error(
                f"[Groq] HTTP {e.response.status_code} for model '{self._model}': "
                f"{e.response.text}"
            )
            raise
        except httpx.TimeoutException:
            logger.error(f"[Groq] Timeout after {_TIMEOUT_SECONDS}s for model '{self._model}'")
            raise
        except Exception as e:
            logger.error(f"[Groq] Completion failed: {e}")
            raise