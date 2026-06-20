"""
providers/llm/litellm_provider.py

Single LLM provider backed by LiteLLM.
Supports any provider LiteLLM supports via a model string like:
  groq/llama-3.3-70b-versatile
  openai/gpt-4o-mini
  anthropic/claude-haiku-4-5-20251001
  ollama/qwen3:4b
"""

import logging

from litellm import acompletion

from providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 120
_OLLAMA_PREFIXES = ("ollama", "ollama_chat")


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
        # num_ctx is Ollama-specific; pass it through when provided
        if "num_ctx" in kwargs and prefix in _OLLAMA_PREFIXES:
            extra["num_ctx"] = kwargs["num_ctx"]

        try:
            response = await acompletion(
                model=self._model,
                messages=messages,
                temperature=0.1,
                **extra,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(
                f"[LiteLLM] Completion failed for '{self._model}': {type(e).__name__}"
            )
            raise
