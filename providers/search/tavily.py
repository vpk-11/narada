"""
providers/search/tavily.py

Tavily search provider.
Built specifically for AI agents. 1000 free searches/month, no rate limiting.

Key advantage: Tavily returns pre-extracted page content in the search
response itself. We store this in snippet so the extractor can use it
directly — avoiding a full scrape + LLM read cycle on most pages.

API docs: https://docs.tavily.com
Set TAVILY_API_KEY in .env to use.
"""

import logging

import httpx

from core.models import SearchResult
from providers.base import BaseSearchProvider

logger = logging.getLogger(__name__)

_TAVILY_SEARCH_URL = "https://api.tavily.com/search"
_TIMEOUT_SECONDS = 30


class TavilyProvider(BaseSearchProvider):

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError(
                "TAVILY_API_KEY is not set in .env. "
                "Sign up at tavily.com to get a free API key."
            )
        self._api_key = api_key

    @property
    def provider_name(self) -> str:
        return "tavily"

    async def search(self, query: str, n_results: int = 10) -> list[SearchResult]:
        """
        Search via Tavily API.

        search_depth="advanced" returns richer content snippets — up to
        ~500 chars of pre-extracted page content per result. This is stored
        in snippet and used by the extractor before falling back to full scrape.
        """
        payload = {
            "api_key": self._api_key,
            "query": query,
            "max_results": n_results,
            "search_depth": "advanced",
            "include_answer": False,
            "include_raw_content": False,
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                response = await client.post(_TAVILY_SEARCH_URL, json=payload)
                response.raise_for_status()
                data = response.json()

            results = [
                SearchResult(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    # Tavily's "content" field is pre-extracted page text —
                    # much richer than a typical search snippet
                    snippet=item.get("content", ""),
                )
                for item in data.get("results", [])
                if item.get("url")
            ]

            logger.info(f"[Tavily] '{query}' returned {len(results)} results")
            return results

        except httpx.HTTPStatusError as e:
            logger.error(
                f"[Tavily] HTTP {e.response.status_code} for '{query}': {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"[Tavily] Search failed for '{query}': {e}")
            raise