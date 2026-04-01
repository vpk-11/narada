"""
agents/scraper.py

Step 3 of the Narada pipeline.

Takes a list of URLs from the search provider and returns clean
plain-text content from each page — ready for the extraction agent.

Key design decisions:
- All pages are scraped concurrently (asyncio.gather), not sequentially.
  Scraping 8 pages one-by-one vs all at once is the difference between
  40 seconds and 5 seconds.
- Timeout is enforced per request — one slow page never blocks the rest.
- Failed pages are skipped with a warning, not raised. Partial results
  are better than a full crash.
- Content is capped at a max character limit before being passed to the
  LLM. Sending an entire 80k-character page wastes tokens and degrades
  extraction quality. We take the first N chars which contain the most
  relevant content in most articles.
"""

import asyncio
import logging

import httpx
from bs4 import BeautifulSoup

from core.models import ScrapedPage, SearchResult

logger = logging.getLogger(__name__)

# Domains known to produce low-quality or off-topic results.
# These aggregate many unrelated companies under misleading category names.
_BLOCKED_DOMAINS = {
    "seedtable.com",          # mixes blockchain/crypto with legit startups
    "crunchbase.com/unicorn-company-list",  # generic multi-sector list
}

def _is_blocked(url: str) -> bool:
    """Return True if the URL matches a known low-quality source."""
    return any(blocked in url for blocked in _BLOCKED_DOMAINS)

# Max characters of page content to pass to the LLM.
# Most useful content is in the first ~6000 chars.
# Raising this improves recall but increases LLM latency and cost.
_MAX_CONTENT_CHARS = 6000

# Tags that carry no useful content — strip before extracting text
_NOISE_TAGS = [
    "script", "style", "nav", "footer", "header",
    "aside", "form", "noscript", "iframe",
]

# Browser-like headers to avoid bot detection on basic sites
_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _extract_text(html: str) -> str:
    """
    Strip HTML and return clean plain text.
    Removes noise tags first, then extracts visible text.
    """
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(set(_NOISE_TAGS)):
        tag.decompose()

    # get_text with separator gives us readable lines instead of a wall of text
    text = soup.get_text(separator="\n", strip=True)

    # Collapse excessive blank lines
    lines = [line for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def _extract_title(html: str) -> str:
    """Extract page title from HTML. Returns empty string if not found."""
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("title")
    return tag.get_text(strip=True) if tag else ""


async def _scrape_one(
    client: httpx.AsyncClient,
    result: SearchResult,
    timeout: int,
) -> ScrapedPage | None:
    """
    Fetch and parse a single URL.
    Returns None on any failure — caller decides what to do with it.
    """
    if _is_blocked(result.url):
        logger.info(f"[Scraper] Skipping blocked domain: {result.url[:70]}")
        return None

    try:
        response = await client.get(
            result.url,
            headers=_REQUEST_HEADERS,
            timeout=timeout,
            follow_redirects=True,
        )
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type:
            logger.debug(f"[Scraper] Skipping non-HTML content at {result.url}")
            return None

        html = response.text
        text = _extract_text(html)
        title = _extract_title(html) or result.title

        if not text.strip():
            logger.warning(f"[Scraper] Empty content after extraction: {result.url}")
            return None

        return ScrapedPage(
            url=result.url,
            title=title,
            content=text[:_MAX_CONTENT_CHARS],
        )

    except httpx.TimeoutException:
        logger.warning(f"[Scraper] Timeout scraping {result.url}")
        return None
    except httpx.HTTPStatusError as e:
        logger.warning(f"[Scraper] HTTP {e.response.status_code} for {result.url}")
        return None
    except Exception as e:
        logger.warning(f"[Scraper] Failed to scrape {result.url}: {e}")
        return None


async def scrape_pages(
    results: list[SearchResult],
    timeout: int,
    max_pages: int,
) -> list[ScrapedPage]:
    """
    Scrape a list of search results concurrently.
    Returns only successfully scraped pages, up to max_pages.

    Args:
        results: search results to scrape
        timeout: per-request timeout in seconds
        max_pages: hard cap on number of pages to scrape

    Returns:
        list of ScrapedPage with clean plain-text content
    """
    # Cap how many we attempt — no point scraping 20 pages
    targets = results[:max_pages]

    logger.info(f"[Scraper] Scraping {len(targets)} pages concurrently")

    async with httpx.AsyncClient() as client:
        tasks = [_scrape_one(client, result, timeout) for result in targets]
        raw_results = await asyncio.gather(*tasks)

    # Filter out failed scrapes
    pages = [page for page in raw_results if page is not None]

    logger.info(f"[Scraper] Successfully scraped {len(pages)}/{len(targets)} pages")

    return pages