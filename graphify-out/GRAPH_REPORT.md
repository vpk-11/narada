# Graph Report - narada  (2026-06-20)

## Corpus Check
- 31 files · ~17,339 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 264 nodes · 577 edges · 23 communities (14 shown, 9 thin omitted)
- Extraction: 79% EXTRACTED · 21% INFERRED · 0% AMBIGUOUS · INFERRED: 122 edges (avg confidence: 0.54)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1caa3ca9`
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
- [[_COMMUNITY_LLM Provider Implementations|LLM Provider Implementations]]
- [[_COMMUNITY_Cache Layer|Cache Layer]]
- [[_COMMUNITY_Frontend App Shell|Frontend App Shell]]
- [[_COMMUNITY_Core Pipeline Orchestration|Core Pipeline Orchestration]]
- [[_COMMUNITY_Search Provider Implementations|Search Provider Implementations]]
- [[_COMMUNITY_Data Models|Data Models]]
- [[_COMMUNITY_Environment Config|Environment Config]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]

## God Nodes (most connected - your core abstractions)
1. `BaseSearchProvider` - 33 edges
2. `BaseLLMProvider` - 29 edges
3. `SearchResult` - 27 edges
4. `PipelineResult` - 25 edges
5. `Settings` - 24 edges
6. `run_pipeline()` - 21 edges
7. `Entity` - 18 edges
8. `QueryAnalysis` - 16 edges
9. `TavilyProvider` - 14 edges
10. `Settings` - 13 edges

## Surprising Connections (you probably didn't know these)
- `Dynamic Schema per Query` --rationale_for--> `get_query_analyzer_llm()`  [INFERRED]
  README.md → providers/factory.py
- `Provider Pattern (abstract interface isolation)` --rationale_for--> `BaseLLMProvider`  [EXTRACTED]
  README.md → providers/base.py
- `Source Traceability at Cell Level (CellValue)` --conceptually_related_to--> `TavilyProvider`  [INFERRED]
  README.md → providers/search/tavily.py
- `security_headers()` --conceptually_related_to--> `API Key Security Model (sessionStorage + headers)`  [INFERRED]
  main.py → README.md
- `Provider Pattern (abstract interface isolation)` --rationale_for--> `BaseSearchProvider`  [EXTRACTED]
  README.md → providers/base.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Pipeline 7-step orchestration** —  [EXTRACTED 1.00]
- **LLM JSON parsing pattern shared across agents** —  [INFERRED 0.85]
- **API key flow: sessionStorage to request headers to Settings** —  [INFERRED 0.95]
- **All LLM providers implement BaseLLMProvider and are instantiated by _build_llm** —  [EXTRACTED 1.00]
- **All search providers implement BaseSearchProvider and are instantiated by get_search_provider** —  [EXTRACTED 1.00]
- **Per-step factory functions all call _build_llm and _get_step_model_override to resolve provider+model** —  [EXTRACTED 1.00]

## Communities (23 total, 9 thin omitted)

### Community 0 - "Agent Logic Layer"
Cohesion: 0.08
Nodes (42): _build_entities(), extract_entities(), _extract_from_page(), _is_valid_value(), _parse_llm_json(), BaseLLMProvider, agents/extractor.py  Step 4 of the Narada pipeline.  For each page, sends conten, Return False for junk values the model writes when it can't find something. (+34 more)

### Community 1 - "Provider Contracts and Core Concepts"
Cohesion: 0.25
Nodes (3): BaseLLMProvider, LiteLLMProvider, providers/llm/litellm_provider.py  Single LLM provider backed by LiteLLM. Suppor

### Community 2 - "API Routes and Request Handling"
Cohesion: 0.09
Nodes (46): _build_settings_from_headers(), CacheClearResponse, delete_cache(), get_providers(), get_server_config(), ProviderInfo, ProvidersResponse, Request (+38 more)

### Community 3 - "Web Scraping Pipeline"
Cohesion: 0.07
Nodes (38): ABC, _extract_text(), _extract_title(), _is_blocked(), ScrapedPage, SearchResult, agents/scraper.py  Step 3 of the Narada pipeline.  Takes a list of URLs from the, Scrape a list of search results concurrently.     Returns only successfully scra (+30 more)

### Community 4 - "Frontend UI Components"
Cohesion: 0.11
Nodes (14): DEFAULT_CONFIG, DEFAULT_MODELS, IS_LOCAL, SEARCH_PROVIDERS, Sidebar(), STEPS, useSession(), App() (+6 more)

### Community 5 - "Frontend Build Config"
Cohesion: 0.11
Nodes (17): dependencies, react, react-dom, devDependencies, @types/react, @types/react-dom, vite, @vitejs/plugin-react (+9 more)

### Community 6 - "App Config and Security"
Cohesion: 0.67
Nodes (3): API Key Security Model (sessionStorage + headers), Request, security_headers()

### Community 7 - "LLM Provider Implementations"
Cohesion: 0.24
Nodes (11): aggregate_entities(), _merge_attributes(), _normalize_name(), Entity, agents/aggregator.py  Step 5 of the Narada pipeline.  Takes the flat list of ent, Normalize an entity name for deduplication comparison.     Lowercases, strips pu, Merge two attribute dicts for the same entity.      Strategy per attribute:, Deduplicate and merge a list of entities extracted across multiple pages.      T (+3 more)

### Community 8 - "Cache Layer"
Cohesion: 0.17
Nodes (23): _cache_key(), _cache_path(), get_cached(), PipelineResult, core/cache.py  Simple disk-based cache for pipeline results. Keyed on a hash of, Generate a unique cache key from query + provider config.     Different provider, Return a cached PipelineResult if one exists for this query + config.     Return, Write a PipelineResult to disk cache.     Silently skips on any write error — ca (+15 more)

### Community 9 - "Frontend App Shell"
Cohesion: 1.00
Nodes (3): Detail, ResultsTable, SourceChip

## Knowledge Gaps
- **34 isolated node(s):** `IS_LOCAL`, `NEEDS_KEY`, `STEPS`, `Request`, `name` (+29 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `BaseLLMProvider` connect `Agent Logic Layer` to `API Routes and Request Handling`, `Web Scraping Pipeline`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Why does `SearchResult` connect `Web Scraping Pipeline` to `Cache Layer`, `Agent Logic Layer`, `API Routes and Request Handling`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Why does `BaseSearchProvider` connect `Web Scraping Pipeline` to `Cache Layer`, `API Routes and Request Handling`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Are the 21 inferred relationships involving `BaseSearchProvider` (e.g. with `CacheClearResponse` and `ProviderInfo`) actually correct?**
  _`BaseSearchProvider` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `BaseLLMProvider` (e.g. with `BaseLLMProvider` and `BaseLLMProvider`) actually correct?**
  _`BaseLLMProvider` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `SearchResult` (e.g. with `ScrapedPage` and `SearchResult`) actually correct?**
  _`SearchResult` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `PipelineResult` (e.g. with `CacheClearResponse` and `ProviderInfo`) actually correct?**
  _`PipelineResult` has 14 INFERRED edges - model-reasoned connections that need verification._