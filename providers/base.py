"""
providers/base.py

Abstract base classes for all Narada providers.
The pipeline never imports a concrete provider directly.
Swapping providers = changing one value in .env. Nothing else changes.
"""

from abc import ABC, abstractmethod

from core.models import SearchResult


class BaseSearchProvider(ABC):
    """Contract every search provider must fulfill."""

    @abstractmethod
    async def search(self, query: str, n_results: int = 10) -> list[SearchResult]:
        """
        Run a search and return results.

        Args:
            query: search string
            n_results: max results to return

        Returns:
            list of SearchResult(url, title, snippet)
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identifier used in metadata and logs. e.g. 'duckduckgo'"""
        ...


class BaseLLMProvider(ABC):
    """Contract every LLM provider must fulfill."""

    @abstractmethod
    async def complete(self, prompt: str, system: str = "", **kwargs) -> str:
        """
        Send a prompt and return the full model response.

        Args:
            prompt: user message
            system: optional system prompt
            **kwargs: provider-specific options (e.g. num_ctx for Ollama)

        Returns:
            model response as plain string
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """e.g. 'ollama', 'openai', 'anthropic'"""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """e.g. 'qwen3:4b', 'gpt-4o-mini'"""
        ...