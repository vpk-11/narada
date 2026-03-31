"""
core/cache.py

Simple disk-based cache for pipeline results.
Keyed on a hash of the query + provider config so the same query
with different providers generates different cache entries.

Why disk over memory:
- Survives server restarts — dev loop doesn't re-run the full pipeline
- No external dependency (no Redis, no Memcached)
- Simple to inspect, clear, or disable

Cache files are stored in .cache/ at the project root.
Add .cache/ to .gitignore — never commit cached results.
"""

import hashlib
import json
import logging
from pathlib import Path

from core.models import PipelineResult

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(".cache")


def _cache_key(query: str, llm_provider: str, llm_model: str, search_provider: str) -> str:
    """
    Generate a unique cache key from query + provider config.
    Different providers = different cache entries for the same query.
    """
    raw = f"{query}|{llm_provider}|{llm_model}|{search_provider}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _cache_path(key: str) -> Path:
    return _CACHE_DIR / f"{key}.json"


def get_cached(
    query: str,
    llm_provider: str,
    llm_model: str,
    search_provider: str,
) -> PipelineResult | None:
    """
    Return a cached PipelineResult if one exists for this query + config.
    Returns None if no cache entry found.
    """
    key = _cache_key(query, llm_provider, llm_model, search_provider)
    path = _cache_path(key)

    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        result = PipelineResult.model_validate(data)
        logger.info(f"[Cache] HIT for '{query}' (key={key})")
        return result
    except Exception as e:
        logger.warning(f"[Cache] Failed to load cache entry {key}: {e} — ignoring")
        return None


def set_cached(
    query: str,
    llm_provider: str,
    llm_model: str,
    search_provider: str,
    result: PipelineResult,
) -> None:
    """
    Write a PipelineResult to disk cache.
    Silently skips on any write error — cache failure is never fatal.
    """
    key = _cache_key(query, llm_provider, llm_model, search_provider)
    path = _cache_path(key)

    try:
        _CACHE_DIR.mkdir(exist_ok=True)
        path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        logger.info(f"[Cache] WRITE for '{query}' (key={key})")
    except Exception as e:
        logger.warning(f"[Cache] Failed to write cache entry {key}: {e}")


def clear_cache() -> int:
    """
    Delete all cache entries. Returns number of files deleted.
    Called via the DELETE /cache API endpoint.
    """
    if not _CACHE_DIR.exists():
        return 0

    deleted = 0
    for f in _CACHE_DIR.glob("*.json"):
        try:
            f.unlink()
            deleted += 1
        except Exception as e:
            logger.warning(f"[Cache] Could not delete {f}: {e}")

    logger.info(f"[Cache] Cleared {deleted} entries")
    return deleted