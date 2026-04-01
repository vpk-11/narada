"""
providers/search/brave.py

Brave Search provider.
Clean results, no tracking, built for developers.
Free tier: 2000 queries/month. No rate limiting.

Sign up: https://brave.com/search/api
Set BRAVE_API_KEY in .env to use.
"""

import logging

import httpx

from core.models import SearchResult
from providers.base import BaseSearchProvider

logger = logging.getLogger(__name__)

_BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
_TIMEOUT_SECONDS = 30


class BraveProvider(BaseSearchProvider):

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError(
                "BRAVE_API_KEY is not set in .env. "
                "Sign up at brave.com/search/api for a free API key."
            )
        self._api_key = api_key

    @property
    def provider_name(self) -> str:
        return "brave"

    async def search(self, query: str, n_results: int = 10) -> list[SearchResult]:
        """
        Search via Brave Search API and return structured results.
        Uses the web search endpoint with freshness=none for broadest coverage.
        """
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self._api_key,
        }

        params = {
            "q": query,
            "count": min(n_results, 20),  # Brave max is 20 per request
            "text_decorations": False,
            "search_lang": "en",
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                response = await client.get(
                    _BRAVE_SEARCH_URL,
                    headers=headers,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

            web_results = data.get("web", {}).get("results", [])
            results = [
                SearchResult(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    snippet=item.get("description", ""),
                )
                for item in web_results
                if item.get("url")
            ]

            logger.info(f"[Brave] '{query}' returned {len(results)} results")
            return results

        except httpx.HTTPStatusError as e:
            logger.error(
                f"[Brave] HTTP {e.response.status_code} for '{query}': {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"[Brave] Search failed for '{query}': {e}")
            raise