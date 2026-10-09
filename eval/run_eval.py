"""
eval/run_eval.py

Runs every query in eval/queries.txt RUNS times with the gap-fill loop on
(AGENT_MAX_ITERATIONS=2) and off (=1, no re-search), cache
off, and prints per-mode means of verified-cell rate, completeness (1 - gap_ratio)
and latency. Model, search provider and keys come from .env, held constant.

Usage: python -m eval.run_eval
"""

import asyncio
import statistics
from pathlib import Path

from config import get_settings
from core.pipeline import run_pipeline
from providers.factory import get_search_provider

QUERIES_FILE = Path(__file__).parent / "queries.txt"
RUNS = 3
ITERATIONS = {"loop on": 2, "loop off": 1}


async def run_mode(queries: list[str], max_iterations: int, runs: int) -> dict[str, float]:
    settings = get_settings().model_copy(update={"agent_max_iterations": max_iterations})
    search = get_search_provider(settings)
    per_query: list[tuple[float, float, float]] = []
    failed = 0
    for q in queries:
        samples = []
        for _ in range(runs):
            try:
                r = await run_pipeline(q, settings, search, use_cache=False)
            except Exception as e:
                failed += 1
                print(f"  FAILED {q!r}: {type(e).__name__}")
                continue
            m = r.metadata
            samples.append((m.verified_rate, 1 - m.gap_ratio, m.duration_seconds))
        if samples:
            per_query.append(tuple(statistics.mean(col) for col in zip(*samples)))
        print(f"  iterations={max_iterations} {q!r}: {len(samples)}/{runs} ok")
    verified, completeness, latency = (statistics.mean(col) for col in zip(*per_query))
    return {"verified_rate": verified, "completeness": completeness, "latency_s": latency, "failed_runs": failed}


async def main() -> None:
    settings = get_settings()
    queries = [l.strip() for l in QUERIES_FILE.read_text().splitlines() if l.strip()]
    results = {mode: await run_mode(queries, n, RUNS) for mode, n in ITERATIONS.items()}
    print(f"\nmodel={settings.llm_model} search={settings.search_provider} "
          f"queries={len(queries)} runs={RUNS}")
    print(f"{'mode':<10}{'verified':>10}{'complete':>10}{'latency_s':>11}{'failed':>8}")
    for mode, r in results.items():
        print(f"{mode:<10}{r['verified_rate']:>10.3f}{r['completeness']:>10.3f}"
              f"{r['latency_s']:>11.1f}{r['failed_runs']:>8}")


if __name__ == "__main__":
    asyncio.run(main())
