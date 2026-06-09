# Graph Report - .  (2026-06-09)

## Corpus Check
- Corpus is ~15,612 words - fits in a single context window. You may not need a graph.

## Summary
- 303 nodes · 677 edges · 18 communities (15 shown, 3 thin omitted)
- Extraction: 76% EXTRACTED · 24% INFERRED · 0% AMBIGUOUS · INFERRED: 161 edges (avg confidence: 0.55)
- Token cost: 19,000 input · 4,900 output

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

## God Nodes (most connected - your core abstractions)
1. `BaseLLMProvider` - 41 edges
2. `BaseSearchProvider` - 34 edges
3. `SearchResult` - 27 edges
4. `PipelineResult` - 25 edges
5. `Settings` - 24 edges
6. `Entity` - 21 edges
7. `run_pipeline()` - 21 edges
8. `QueryAnalysis` - 19 edges
9. `Settings` - 17 edges
10. `ScrapedPage` - 15 edges

## Surprising Connections (you probably didn't know these)
- `Provider Pattern (abstract interface isolation)` --rationale_for--> `BaseSearchProvider`  [EXTRACTED]
  README.md → providers/base.py
- `Dynamic Schema per Query` --rationale_for--> `get_query_analyzer_llm()`  [INFERRED]
  README.md → providers/factory.py
- `Source Traceability at Cell Level (CellValue)` --conceptually_related_to--> `TavilyProvider`  [INFERRED]
  README.md → providers/search/tavily.py
- `environment.yml (Conda dev environment)` --references--> `main.py (FastAPI entry point)`  [INFERRED]
  environment.yml → main.py
- `build-frontend.yaml (GitHub Actions CI)` --references--> `main.py (FastAPI entry point)`  [INFERRED]
  .github/workflows/build-frontend.yaml → main.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Pipeline 7-step orchestration** —  [EXTRACTED 1.00]
- **LLM JSON parsing pattern shared across agents** —  [INFERRED 0.85]
- **API key flow: sessionStorage to request headers to Settings** —  [INFERRED 0.95]
- **All LLM providers implement BaseLLMProvider and are instantiated by _build_llm** —  [EXTRACTED 1.00]
- **All search providers implement BaseSearchProvider and are instantiated by get_search_provider** —  [EXTRACTED 1.00]
- **Per-step factory functions all call _build_llm and _get_step_model_override to resolve provider+model** —  [EXTRACTED 1.00]

## Communities (18 total, 3 thin omitted)

### Community 0 - "Agent Logic Layer"
Cohesion: 0.07
Nodes (56): aggregate_entities(), _merge_attributes(), _normalize_name(), Entity, agents/aggregator.py  Step 5 of the Narada pipeline.  Takes the flat list of ent, Normalize an entity name for deduplication comparison.     Lowercases, strips pu, Merge two attribute dicts for the same entity.      Strategy per attribute:, Deduplicate and merge a list of entities extracted across multiple pages.      T (+48 more)

### Community 1 - "Provider Contracts and Core Concepts"
Cohesion: 0.08
Nodes (30): BaseLLMProvider, BaseSearchProvider, Source Traceability at Cell Level (CellValue), Dynamic Schema per Query, Per-Step LLM Configuration, AnthropicProvider, GroqProvider, Send a chat completion request to Groq.         Uses the OpenAI-compatible /v1/c (+22 more)

### Community 2 - "API Routes and Request Handling"
Cohesion: 0.12
Nodes (42): _build_settings_from_headers(), CacheClearResponse, delete_cache(), get_providers(), get_server_config(), ProviderInfo, ProvidersResponse, Request (+34 more)

### Community 3 - "Web Scraping Pipeline"
Cohesion: 0.09
Nodes (29): _extract_text(), _extract_title(), _is_blocked(), ScrapedPage, SearchResult, agents/scraper.py  Step 3 of the Narada pipeline.  Takes a list of URLs from the, Scrape a list of search results concurrently.     Returns only successfully scra, Return True if the URL matches a known low-quality source. (+21 more)

### Community 4 - "Frontend UI Components"
Cohesion: 0.11
Nodes (14): DEFAULT_CONFIG, DEFAULT_MODELS, IS_LOCAL, SEARCH_PROVIDERS, Sidebar(), STEPS, useSession(), App() (+6 more)

### Community 5 - "Frontend Build Config"
Cohesion: 0.11
Nodes (17): dependencies, react, react-dom, devDependencies, @types/react, @types/react-dom, vite, @vitejs/plugin-react (+9 more)

### Community 6 - "App Config and Security"
Cohesion: 0.14
Nodes (15): FALLBACK_ALLOW (server key sharing option), API Key Security Model (sessionStorage + headers), configure_logging(), config.py  Single source of truth for all Narada settings. Every value is read f, environment.yml (Conda dev environment), vite.config.js (dev proxy /api -> :8000), main.py (FastAPI entry point), health() (+7 more)

### Community 7 - "LLM Provider Implementations"
Cohesion: 0.13
Nodes (8): ABC, providers/llm/anthropic.py  Anthropic LLM provider. Uses the /v1/messages endpoi, providers/llm/groq.py  Groq LLM provider. Groq runs inference on custom LPU hard, providers/llm/ollama.py  Ollama LLM provider. Talks to a locally running Ollama, providers/llm/openai.py  OpenAI LLM provider. Uses the /v1/chat/completions endp, providers/base.py  Abstract base classes for all Narada providers. The pipeline, providers/search/brave.py  Brave Search provider. Clean results, no tracking, bu, providers/search/tavily.py  Tavily search provider. Built specifically for AI ag

### Community 8 - "Cache Layer"
Cohesion: 0.27
Nodes (10): _cache_key(), _cache_path(), get_cached(), PipelineResult, core/cache.py  Simple disk-based cache for pipeline results. Keyed on a hash of, Generate a unique cache key from query + provider config.     Different provider, Return a cached PipelineResult if one exists for this query + config.     Return, Write a PipelineResult to disk cache.     Silently skips on any write error — ca (+2 more)

### Community 9 - "Frontend App Shell"
Cohesion: 0.32
Nodes (8): App, Detail, ResultsTable, SourceChip, DEFAULT_CONFIG, DEFAULT_MODELS, Sidebar, useSession

### Community 10 - "Core Pipeline Orchestration"
Cohesion: 0.50
Nodes (4): buildHeaders, execute, run, runWithFallback

## Knowledge Gaps
- **34 isolated node(s):** `name`, `private`, `version`, `type`, `packageManager` (+29 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `BaseLLMProvider` connect `Agent Logic Layer` to `Provider Contracts and Core Concepts`, `API Routes and Request Handling`, `Web Scraping Pipeline`, `LLM Provider Implementations`?**
  _High betweenness centrality (0.147) - this node is a cross-community bridge._
- **Why does `SearchResult` connect `Web Scraping Pipeline` to `Agent Logic Layer`, `Provider Contracts and Core Concepts`, `API Routes and Request Handling`, `LLM Provider Implementations`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Why does `BaseSearchProvider` connect `API Routes and Request Handling` to `Agent Logic Layer`, `Provider Contracts and Core Concepts`, `Web Scraping Pipeline`, `LLM Provider Implementations`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Are the 25 inferred relationships involving `BaseLLMProvider` (e.g. with `BaseLLMProvider` and `Entity`) actually correct?**
  _`BaseLLMProvider` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `BaseSearchProvider` (e.g. with `CacheClearResponse` and `ProviderInfo`) actually correct?**
  _`BaseSearchProvider` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `SearchResult` (e.g. with `ScrapedPage` and `SearchResult`) actually correct?**
  _`SearchResult` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `PipelineResult` (e.g. with `CacheClearResponse` and `ProviderInfo`) actually correct?**
  _`PipelineResult` has 14 INFERRED edges - model-reasoned connections that need verification._