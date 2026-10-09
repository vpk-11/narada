"""
providers/llm/litellm_provider.py

Single LLM provider backed by LiteLLM.
Supports any provider LiteLLM supports via a model string like:
  groq/openai/gpt-oss-20b
  openai/gpt-4o-mini
  anthropic/claude-haiku-4-5-20251001
  ollama/qwen3:4b
"""

import asyncio
import logging
import re

import litellm
from litellm import acompletion

from providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 120
_OLLAMA_PREFIXES = ("ollama", "ollama_chat")

# Transient failures worth a retry — rate limits, timeouts, and provider-side
# outages. Auth/bad-request errors are not retried; retrying a 401 five times
# just delays the same failure.
_RETRYABLE_ERRORS = (
    litellm.RateLimitError,
    litellm.Timeout,
    litellm.APIConnectionError,
    litellm.ServiceUnavailableError,
    litellm.InternalServerError,
)
_MAX_RETRIES = 4
# Providers (Groq) say how long to wait on a token-rate-limit; honor it instead
# of retrying inside the same window and burning the attempt.
_RETRY_AFTER_RE = re.compile(r"try again in ([\d.]+)s")
_MAX_RETRY_AFTER_SECONDS = 20.0
# gpt-oss models spend most of their tokens reasoning; low effort cuts both
# latency and the tokens-per-minute they consume on free tiers.
_LOW_REASONING_MODELS = ("gpt-oss",)
_BACKOFF_BASE_SECONDS = 1.0
_BACKOFF_CAP_SECONDS = 10.0


class LiteLLMProvider(BaseLLMProvider):

    def __init__(self, model: str, api_key: str = "", api_base: str = "") -> None:
        self._model = model
        self._api_key = api_key
        self._api_base = api_base

    @property
    def provider_name(self) -> str:
        return self._model.split("/")[0] if "/" in self._model else "litellm"

    @property
    def model_name(self) -> str:
        return self._model

    async def complete(self, prompt: str, system: str = "", **kwargs) -> str:
        prefix = self._model.split("/")[0].lower() if "/" in self._model else ""

        if prefix not in _OLLAMA_PREFIXES and not self._api_key:
            display = prefix.capitalize() if prefix else "LLM"
            raise ValueError(
                f"{display} API key is missing. "
                f"Add your {display} API key in the Settings sidebar."
            )

        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        extra: dict = {"timeout": _TIMEOUT_SECONDS}
        if self._api_key:
            extra["api_key"] = self._api_key
        if self._api_base:
            extra["api_base"] = self._api_base
        if any(m in self._model for m in _LOW_REASONING_MODELS):
            extra["reasoning_effort"] = "low"
        # num_ctx is Ollama-specific; pass it through when provided
        if "num_ctx" in kwargs and prefix in _OLLAMA_PREFIXES:
            extra["num_ctx"] = kwargs["num_ctx"]

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = await acompletion(
                    model=self._model,
                    messages=messages,
                    temperature=0.1,
                    **extra,
                )
                return response.choices[0].message.content
            except _RETRYABLE_ERRORS as e:
                if attempt >= _MAX_RETRIES:
                    logger.error(
                        f"[LiteLLM] Completion failed for '{self._model}' "
                        f"after {_MAX_RETRIES} attempts: {type(e).__name__}"
                    )
                    raise
                wait = min(_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)), _BACKOFF_CAP_SECONDS)
                hinted = _RETRY_AFTER_RE.search(str(e))
                if hinted:
                    wait = min(float(hinted.group(1)) + 0.5, _MAX_RETRY_AFTER_SECONDS)
                logger.warning(
                    f"[LiteLLM] {type(e).__name__} on attempt {attempt}/{_MAX_RETRIES} "
                    f"for '{self._model}' — retrying in {wait:.1f}s"
                )
                await asyncio.sleep(wait)
            except Exception as e:
                logger.error(
                    f"[LiteLLM] Completion failed for '{self._model}': {type(e).__name__}"
                )
                raise
