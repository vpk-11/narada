"""
providers/search/duckduckgo.py

DuckDuckGo search provider.
No API key. No account required.
Kept as a free fallback — use Tavily or Brave for production reliability.

Tradeoffs:
- DDG aggressively rate-limits. We handle this with longer delays,
  random jitter, and a fresh session per retry to avoid pattern detection.
- DDGS is synchronous — runs in a thread to avoid blocking the event loop.
"""

import asyncio
import logging
import random
import time

from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import DuckDuckGoSearchException

from core.models import SearchResult
from providers.base import BaseSearchProvider

logger = logging.getLogger(__name__)

_MAX_RETRIES = 4
_BASE_DELAY_SECONDS = 5
_JITTER_SECONDS = 3


def _run_ddg_search(query: str, n_results: int) -> list[SearchResult]:
    """
    Synchronous DDG search with retry, exponential backoff, and jitter.
    Fresh DDGS instance per attempt — gets a new VQD token each time.
    """
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            with DDGS() as ddgs:
                raw = ddgs.text(query, max_results=n_results)
                results = [
                    SearchResult(
                        url=item.get("href", ""),
                        title=item.get("title", ""),
                        snippet=item.get("body", ""),
                    )
                    for item in raw
                    if item.get("href")
                ]
                logger.info(f"[DDG] '{query}' succeeded on attempt {attempt}")
                return results

        except DuckDuckGoSearchException as e:
            if attempt < _MAX_RETRIES:
                wait = (_BASE_DELAY_SECONDS * attempt) + random.uniform(0, _JITTER_SECONDS)
                logger.warning(
                    f"[DDG] Rate limited on attempt {attempt}/{_MAX_RETRIES} "
                    f"for '{query}'. Waiting {wait:.1f}s..."
                )
                time.sleep(wait)
            else:
                logger.error(f"[DDG] All {_MAX_RETRIES} attempts exhausted for '{query}': {e}")

        except Exception as e:
            logger.error(f"[DDG] Unexpected error for '{query}': {e}")
            break

    return []


class DuckDuckGoProvider(BaseSearchProvider):

    @property
    def provider_name(self) -> str:
        return "duckduckgo"

    async def search(self, query: str, n_results: int = 10) -> list[SearchResult]:
        """
        Search DuckDuckGo. Runs synchronous DDGS in a thread.
        """
        results = await asyncio.to_thread(_run_ddg_search, query, n_results)
        logger.info(f"[DDG] '{query}' returned {len(results)} results")
        return results