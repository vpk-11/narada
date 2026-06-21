# Graph Report - narada  (2026-06-21)

## Corpus Check
- 30 files · ~14,803 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 305 nodes · 614 edges · 21 communities (14 shown, 7 thin omitted)
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 112 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b5a14962`
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
- [[_COMMUNITY_Cache Layer|Cache Layer]]
- [[_COMMUNITY_Frontend App Shell|Frontend App Shell]]
- [[_COMMUNITY_Core Pipeline Orchestration|Core Pipeline Orchestration]]
- [[_COMMUNITY_Search Provider Implementations|Search Provider Implementations]]
- [[_COMMUNITY_Data Models|Data Models]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]

## God Nodes (most connected - your core abstractions)
1. `BaseSearchProvider` - 31 edges
2. `BaseLLMProvider` - 27 edges
3. `SearchResult` - 25 edges
4. `Settings` - 24 edges
5. `PipelineResult` - 24 edges
6. `run_pipeline()` - 21 edges
7. `Entity` - 18 edges
8. `QueryAnalysis` - 16 edges
9. `Narada` - 14 edges
10. `Settings` - 13 edges

## Surprising Connections (you probably didn't know these)
- `Narada` --references--> `challenge.md (agentic search challenge spec)`  [INFERRED]
  README.md → challenge.md
- `AsyncClient` --uses--> `SearchResult`  [INFERRED]
  agents/scraper.py → core/models.py
- `SearchRequest` --uses--> `BaseLLMProvider`  [INFERRED]
  api/routes.py → providers/base.py
- `SearchRequest` --uses--> `BaseSearchProvider`  [INFERRED]
  api/routes.py → providers/base.py
- `SearchResponse` --uses--> `Settings`  [INFERRED]
  api/routes.py → config.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Pipeline 7-step orchestration** —  [EXTRACTED 1.00]
- **LLM JSON parsing pattern shared across agents** —  [INFERRED 0.85]
- **API key flow: sessionStorage to request headers to Settings** —  [INFERRED 0.95]
- **All LLM providers implement BaseLLMProvider and are instantiated by _build_llm** —  [EXTRACTED 1.00]
- **All search providers implement BaseSearchProvider and are instantiated by get_search_provider** —  [EXTRACTED 1.00]
- **Per-step factory functions all call _build_llm and _get_step_model_override to resolve provider+model** —  [EXTRACTED 1.00]

## Communities (21 total, 7 thin omitted)

### Community 0 - "Agent Logic Layer"
Cohesion: 0.10
Nodes (34): aggregate_entities(), _merge_attributes(), _normalize_name(), Entity, agents/aggregator.py  Step 5 of the Narada pipeline.  Takes the flat list of ent, Normalize an entity name for deduplication comparison.     Lowercases, strips pu, Merge two attribute dicts for the same entity.      Strategy per attribute:, Deduplicate and merge a list of entities extracted across multiple pages.      T (+26 more)

### Community 1 - "Provider Contracts and Core Concepts"
Cohesion: 0.25
Nodes (3): BaseLLMProvider, LiteLLMProvider, providers/llm/litellm_provider.py  Single LLM provider backed by LiteLLM. Suppor

### Community 2 - "API Routes and Request Handling"
Cohesion: 0.10
Nodes (18): api/limiter.py  Shared rate limiter instance. Imported by main.py (to register o, CacheClearResponse, delete_cache(), get_server_config(), Returns public server configuration flags for the frontend.     Currently expose, Clear all cached pipeline results. Requires x-admin-key header when CACHE_ADMIN_, ServerConfig, BaseModel (+10 more)

### Community 3 - "Web Scraping Pipeline"
Cohesion: 0.07
Nodes (44): ABC, get_providers(), ProviderInfo, ProvidersResponse, api/routes.py  Narada API routes.  Security model: - User API keys are sent as c, Return active provider config per pipeline step., SearchResponse, BaseSearchProvider (+36 more)

### Community 4 - "Frontend UI Components"
Cohesion: 0.11
Nodes (14): DEFAULT_CONFIG, DEFAULT_MODELS, IS_LOCAL, SEARCH_PROVIDERS, Sidebar(), STEPS, useSession(), App() (+6 more)

### Community 5 - "Frontend Build Config"
Cohesion: 0.11
Nodes (17): dependencies, react, react-dom, devDependencies, @types/react, @types/react-dom, vite, @vitejs/plugin-react (+9 more)

### Community 6 - "App Config and Security"
Cohesion: 0.10
Nodes (32): _build_entities(), extract_entities(), _extract_from_page(), _is_valid_value(), _parse_llm_json(), BaseLLMProvider, agents/extractor.py  Step 4 of the Narada pipeline.  For each page, sends conten, Return False for junk values the model writes when it can't find something. (+24 more)

### Community 8 - "Cache Layer"
Cohesion: 0.13
Nodes (32): _build_settings_from_headers(), Request, Run the Narada pipeline for a query.      API keys are read from request headers, Build a Settings instance with per-request overrides from headers.      Only non, search(), SearchRequest, BaseSettings, Settings (+24 more)

### Community 9 - "Frontend App Shell"
Cohesion: 1.00
Nodes (3): Detail, ResultsTable, SourceChip

### Community 11 - "Search Provider Implementations"
Cohesion: 0.04
Nodes (45): challenge.md (agentic search challenge spec), 1. Create the Conda environment, 2. Configure environment variables, 3. Pull Ollama models (only if using Ollama), 4. Start the server, 5. Start the frontend (separate terminal), 6. Open Swagger docs, Adding a New Provider (+37 more)

## Knowledge Gaps
- **68 isolated node(s):** `What you need`, `Step 1 - Get your API keys`, `Step 2 - Configure the sidebar`, `Step 3 - Run a query`, `Reading the results` (+63 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `BaseLLMProvider` connect `Web Scraping Pipeline` to `Agent Logic Layer`, `Cache Layer`, `API Routes and Request Handling`, `App Config and Security`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._
- **Why does `SearchResult` connect `Web Scraping Pipeline` to `Agent Logic Layer`, `Cache Layer`, `API Routes and Request Handling`, `App Config and Security`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Why does `BaseSearchProvider` connect `Web Scraping Pipeline` to `Cache Layer`, `API Routes and Request Handling`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Are the 20 inferred relationships involving `BaseSearchProvider` (e.g. with `CacheClearResponse` and `ProviderInfo`) actually correct?**
  _`BaseSearchProvider` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `BaseLLMProvider` (e.g. with `BaseLLMProvider` and `BaseLLMProvider`) actually correct?**
  _`BaseLLMProvider` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `SearchResult` (e.g. with `AsyncClient` and `BaseSearchProvider`) actually correct?**
  _`SearchResult` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `Settings` (e.g. with `CacheClearResponse` and `ProviderInfo`) actually correct?**
  _`Settings` has 15 INFERRED edges - model-reasoned connections that need verification._