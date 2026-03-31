"""
providers/llm/ollama.py

Ollama LLM provider.
Talks to a locally running Ollama instance via its REST API.

All config (base URL, model) is injected from settings — never hardcoded.
Requires Ollama to be running: https://ollama.com
"""

import logging

import httpx

from providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 420

# Two context window presets — callers pick based on prompt size.
# Keeping num_ctx as low as needed is the single biggest speed lever
# on local models like Qwen3:4b.
NUM_CTX_DEFAULT = 4096   # query analysis, short prompts
NUM_CTX_LARGE = 8192     # extraction prompts with page content


class OllamaProvider(BaseLLMProvider):

    def __init__(self, model: str, base_url: str) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    async def complete(
        self,
        prompt: str,
        system: str = "",
        num_ctx: int = NUM_CTX_DEFAULT,
        **kwargs,
    ) -> str:
        """
        Send a chat completion request to Ollama.

        Args:
            prompt: user message
            system: optional system prompt
            num_ctx: context window size. Use NUM_CTX_LARGE for extraction
                     prompts that include page content.
        """
        messages: list[dict] = []

        if system:
            messages.append({"role": "system", "content": system})

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_ctx": num_ctx,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{self._base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["message"]["content"]

        except httpx.ReadTimeout:
            logger.error(
                f"Ollama timed out after {_TIMEOUT_SECONDS}s for model '{self._model}'. "
                f"Try running: ollama run {self._model} in a terminal to pre-load the model."
            )
            raise
        except httpx.ConnectError:
            logger.error(
                f"Cannot connect to Ollama at {self._base_url}. "
                "Ensure Ollama is running and OLLAMA_BASE_URL is correct in .env"
            )
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama returned HTTP {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Ollama completion failed: {e}")
            raise