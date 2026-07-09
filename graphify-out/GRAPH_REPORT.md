# Graph Report - narada  (2026-07-09)

## Corpus Check
- 41 files · ~21,078 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 280 nodes · 533 edges · 19 communities (14 shown, 5 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 46 edges (avg confidence: 0.58)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `213a10bf`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Agent Logic Layer|Agent Logic Layer]]
- [[_COMMUNITY_Provider Contracts and Core Concepts|Provider Contracts and Core Concepts]]
- [[_COMMUNITY_API Routes and Request Handling|API Routes and Request Handling]]
- [[_COMMUNITY_Web Scraping Pipeline|Web Scraping Pipeline]]
- [[_COMMUNITY_Frontend UI Components|Frontend UI Components]]
- [[_COMMUNITY_Frontend Build Config|Frontend Build Config]]
- [[_COMMUNITY_App Config and Security|App Config and Security]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Core Pipeline Orchestration|Core Pipeline Orchestration]]
- [[_COMMUNITY_Search Provider Implementations|Search Provider Implementations]]
- [[_COMMUNITY_Data Models|Data Models]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 31|Community 31]]

## God Nodes (most connected - your core abstractions)
1. `BaseLLMProvider` - 30 edges
2. `BaseSearchProvider` - 25 edges
3. `SearchResult` - 23 edges
4. `Settings` - 22 edges
5. `PipelineResult` - 19 edges
6. `run_pipeline()` - 19 edges
7. `Narada` - 15 edges
8. `Entity` - 13 edges
9. `QueryAnalysis` - 11 edges
10. `DuckDuckGoProvider` - 11 edges

## Surprising Connections (you probably didn't know these)
- `SearchRequest` --uses--> `BaseSearchProvider`  [INFERRED]
  api/routes.py → providers/base.py
- `SearchResponse` --uses--> `BaseSearchProvider`  [INFERRED]
  api/routes.py → providers/base.py
- `CacheClearResponse` --uses--> `BaseSearchProvider`  [INFERRED]
  api/routes.py → providers/base.py
- `ProviderInfo` --uses--> `BaseSearchProvider`  [INFERRED]
  api/routes.py → providers/base.py
- `ProvidersResponse` --uses--> `BaseSearchProvider`  [INFERRED]
  api/routes.py → providers/base.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Pipeline 7-step orchestration** —  [EXTRACTED 1.00]
- **LLM JSON parsing pattern shared across agents** —  [INFERRED 0.85]
- **API key flow: sessionStorage to request headers to Settings** —  [INFERRED 0.95]
- **All LLM providers implement BaseLLMProvider and are instantiated by _build_llm** —  [EXTRACTED 1.00]
- **All search providers implement BaseSearchProvider and are instantiated by get_search_provider** —  [EXTRACTED 1.00]
- **Per-step factory functions all call _build_llm and _get_step_model_override to resolve provider+model** —  [EXTRACTED 1.00]

## Communities (19 total, 5 thin omitted)

### Community 0 - "Agent Logic Layer"
Cohesion: 0.29
Nodes (9): _cache_key(), _cache_path(), get_cached(), core/cache.py  Simple disk-based cache for pipeline results. Keyed on a hash of, Generate a unique cache key from query + provider config.     Different provider, Return a cached PipelineResult if one exists for this query + config.     Return, Write a PipelineResult to disk cache.     Silently skips on any write error — ca, set_cached() (+1 more)

### Community 1 - "Provider Contracts and Core Concepts"
Cohesion: 0.18
Nodes (16): _extract_text(), _extract_title(), _is_blocked(), _is_ssrf_risk(), agents/scraper.py  Step 3 of the Narada pipeline.  Takes a list of URLs from the, Extract page title from HTML. Returns empty string if not found., Fetch and parse a single URL.     Returns None on any failure — caller decides w, Scrape a list of search results concurrently.     Returns only successfully scra (+8 more)

### Community 2 - "API Routes and Request Handling"
Cohesion: 0.18
Nodes (8): api/limiter.py  Shared rate limiter instance. Imported by main.py (to register o, configure_logging(), config.py  Single source of truth for all Narada settings. Every value is read f, Request, main.py  Narada — FastAPI entry point.  In production, serves the React frontend, Catch-all route that serves the React app for any non-API path.         React Ro, security_headers(), serve_frontend()

### Community 3 - "Web Scraping Pipeline"
Cohesion: 0.11
Nodes (41): _build_settings_from_headers(), CacheClearResponse, delete_cache(), get_providers(), get_server_config(), ProviderInfo, ProvidersResponse, Request (+33 more)

### Community 4 - "Frontend UI Components"
Cohesion: 0.12
Nodes (15): ResultsTable(), DEFAULT_CONFIG, DEFAULT_MODELS, IS_LOCAL, SEARCH_PROVIDERS, Sidebar(), STEPS, useSession() (+7 more)

### Community 5 - "Frontend Build Config"
Cohesion: 0.11
Nodes (17): dependencies, react, react-dom, devDependencies, @types/react, @types/react-dom, vite, @vitejs/plugin-react (+9 more)

### Community 6 - "App Config and Security"
Cohesion: 0.10
Nodes (22): ABC, A single result returned by the search provider., SearchResult, Run all search queries and return deduplicated results., _run_searches(), BaseSearchProvider, providers/base.py  Abstract base classes for all Narada providers. The pipeline, Contract every search provider must fulfill. (+14 more)

### Community 7 - "Community 7"
Cohesion: 0.09
Nodes (39): aggregate_entities(), _merge_attributes(), _normalize_name(), agents/aggregator.py  Step 5 of the Narada pipeline.  Takes the flat list of ent, Normalize an entity name for deduplication comparison.     Lowercases, strips pu, Merge two attribute dicts for the same entity.      Strategy per attribute:, Deduplicate and merge a list of entities extracted across multiple pages.      T, _build_entities() (+31 more)

### Community 11 - "Search Provider Implementations"
Cohesion: 0.04
Nodes (46): challenge.md (agentic search challenge spec), 1. Create the Conda environment, 2. Configure environment variables, 3. Pull Ollama models (only if using Ollama), 4. Start the server, 5. Start the frontend (separate terminal), 6. Open Swagger docs, Adding a New Provider (+38 more)

### Community 24 - "Community 24"
Cohesion: 0.33
Nodes (5): Agentic Search Challenge, Guidelines, How we'll evaluate, Minimum Requirements, Submission

## Knowledge Gaps
- **69 isolated node(s):** `name`, `private`, `version`, `type`, `packageManager` (+64 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `BaseLLMProvider` connect `Web Scraping Pipeline` to `Community 31`, `App Config and Security`, `Community 7`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `SearchResult` connect `App Config and Security` to `Provider Contracts and Core Concepts`, `Web Scraping Pipeline`, `Community 7`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Why does `BaseSearchProvider` connect `App Config and Security` to `Web Scraping Pipeline`, `Community 7`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `BaseLLMProvider` (e.g. with `CacheClearResponse` and `ProviderInfo`) actually correct?**
  _`BaseLLMProvider` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `BaseSearchProvider` (e.g. with `CacheClearResponse` and `ProviderInfo`) actually correct?**
  _`BaseSearchProvider` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `SearchResult` (e.g. with `AsyncClient` and `BaseLLMProvider`) actually correct?**
  _`SearchResult` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `Settings` (e.g. with `CacheClearResponse` and `ProviderInfo`) actually correct?**
  _`Settings` has 7 INFERRED edges - model-reasoned connections that need verification._