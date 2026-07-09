# Graph Report - narada  (2026-07-08)

## Corpus Check
- 39 files · ~19,530 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 372 nodes · 783 edges · 30 communities (24 shown, 6 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 50 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cd99db28`
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
- [[_COMMUNITY_Cache Layer|Cache Layer]]
- [[_COMMUNITY_Frontend App Shell|Frontend App Shell]]
- [[_COMMUNITY_Core Pipeline Orchestration|Core Pipeline Orchestration]]
- [[_COMMUNITY_Search Provider Implementations|Search Provider Implementations]]
- [[_COMMUNITY_Data Models|Data Models]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]

## God Nodes (most connected - your core abstractions)
1. `BaseLLMProvider` - 36 edges
2. `Entity` - 34 edges
3. `BaseSearchProvider` - 27 edges
4. `SearchResult` - 24 edges
5. `Settings` - 22 edges
6. `run_pipeline()` - 21 edges
7. `PipelineResult` - 19 edges
8. `QueryAnalysis` - 17 edges
9. `CellValue` - 16 edges
10. `aggregate_entities()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `BaseLLMProvider` --uses--> `SearchResult`  [INFERRED]
  providers/base.py → core/models.py
- `BaseSearchProvider` --uses--> `SearchResult`  [INFERRED]
  providers/base.py → core/models.py
- `DuckDuckGoProvider` --uses--> `SearchResult`  [INFERRED]
  providers/search/duckduckgo.py → core/models.py
- `_FakeLLM` --uses--> `CellValue`  [INFERRED]
  tests/test_validator.py → core/models.py
- `_FakeLLM` --uses--> `Entity`  [INFERRED]
  tests/test_validator.py → core/models.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Pipeline 7-step orchestration** —  [EXTRACTED 1.00]
- **LLM JSON parsing pattern shared across agents** —  [INFERRED 0.85]
- **API key flow: sessionStorage to request headers to Settings** —  [INFERRED 0.95]
- **All LLM providers implement BaseLLMProvider and are instantiated by _build_llm** —  [EXTRACTED 1.00]
- **All search providers implement BaseSearchProvider and are instantiated by get_search_provider** —  [EXTRACTED 1.00]
- **Per-step factory functions all call _build_llm and _get_step_model_override to resolve provider+model** —  [EXTRACTED 1.00]

## Communities (30 total, 6 thin omitted)

### Community 0 - "Agent Logic Layer"
Cohesion: 0.08
Nodes (46): extract_entities(), _extract_from_chunk(), _extract_from_page(), _parse_llm_json(), agents/extractor.py  Step 4 of the Narada pipeline.  For each page, sends conten, Parse JSON from LLM output.     Handles {"entities":[...]} and bare [...] respon, Extract entities from a single chunk of page content. Returns [] on failure., Extract entities from a page, chunk by chunk. A page longer than one     chunk y (+38 more)

### Community 2 - "API Routes and Request Handling"
Cohesion: 0.19
Nodes (22): aggregate_entities(), _merge_attributes(), _name_similarity(), _normalize_name(), agents/aggregator.py  Step 5 of the Narada pipeline.  Takes the flat list of ent, Normalize an entity name for deduplication comparison.     Lowercases, strips pu, Ratcliff/Obershelp similarity ratio between two normalized names., Merge two attribute dicts for the same entity.      Strategy per attribute: (+14 more)

### Community 3 - "Web Scraping Pipeline"
Cohesion: 0.07
Nodes (67): ABC, api/limiter.py  Shared rate limiter instance. Imported by main.py (to register o, _build_settings_from_headers(), CacheClearResponse, delete_cache(), get_providers(), get_server_config(), ProviderInfo (+59 more)

### Community 4 - "Frontend UI Components"
Cohesion: 0.12
Nodes (15): ResultsTable(), DEFAULT_CONFIG, DEFAULT_MODELS, IS_LOCAL, SEARCH_PROVIDERS, Sidebar(), STEPS, useSession() (+7 more)

### Community 5 - "Frontend Build Config"
Cohesion: 0.11
Nodes (17): dependencies, react, react-dom, devDependencies, @types/react, @types/react-dom, vite, @vitejs/plugin-react (+9 more)

### Community 6 - "App Config and Security"
Cohesion: 0.07
Nodes (29): _extract_text(), _extract_title(), _is_blocked(), _is_ssrf_risk(), agents/scraper.py  Step 3 of the Narada pipeline.  Takes a list of URLs from the, Extract page title from HTML. Returns empty string if not found., Fetch and parse a single URL.     Returns None on any failure — caller decides w, Scrape a list of search results concurrently.     Returns only successfully scra (+21 more)

### Community 7 - "Community 7"
Cohesion: 0.19
Nodes (16): _normalize(), _parse_valid_names(), Parse the list of valid entity names from LLM output., Filter entities to only those that genuinely match the original query.     Uses, validate_entities(), _analysis(), _entity(), _FakeLLM (+8 more)

### Community 8 - "Cache Layer"
Cohesion: 0.22
Nodes (15): _build_cell(), _build_entities(), _is_valid_value(), Return False for junk values the model writes when it can't find something., Build a CellValue from one attribute's raw LLM output.      Expected shape is {", Convert parsed LLM JSON into Entity objects.     Attaches source_url to every Ce, Tests for agents/extractor.py — cell building, junk-value filtering, and schema, test_build_cell_clamps_out_of_range_confidence() (+7 more)

### Community 9 - "Frontend App Shell"
Cohesion: 1.00
Nodes (3): Detail, ResultsTable, SourceChip

### Community 11 - "Search Provider Implementations"
Cohesion: 0.22
Nodes (8): challenge.md (agentic search challenge spec), Changelog, Design Decisions, Environment Variables, How It Works, Key Fallback Behaviour, Known Limitations, Narada

### Community 15 - "Community 15"
Cohesion: 0.29
Nodes (9): chunk_text(), core/chunking.py  Splits scraped page content into LLM-sized chunks without cutt, Split text into chunks of at most max_chars, preferring paragraph     boundaries, Tests for core/chunking.py — paragraph/sentence-boundary-aware chunking with ove, test_consecutive_chunks_share_overlap(), test_empty_text_returns_no_chunks(), test_long_text_splits_on_paragraph_boundaries(), test_oversized_single_paragraph_falls_back_to_sentences() (+1 more)

### Community 19 - "Community 19"
Cohesion: 0.18
Nodes (11): Agentic Gap-Filling, API Key Security, Architecture, Automatic Search Failover, Chunked Extraction, Error Handling, Fuzzy Matching and Confidence Resolution, JSON Repair (+3 more)

### Community 20 - "Community 20"
Cohesion: 0.22
Nodes (9): 1. Create the Conda environment, 2. Configure environment variables, 3. Pull Ollama models (only if using Ollama), 4. Start the server, 5. Start the frontend (separate terminal), 6. Open Swagger docs, 7. Run tests, Prerequisites (+1 more)

### Community 23 - "Community 23"
Cohesion: 0.29
Nodes (7): Reading the results, Step 1 - Get your API keys, Step 2 - Configure the sidebar, Step 3 - Run a query, Tips, Using the App, What you need

### Community 24 - "Community 24"
Cohesion: 0.33
Nodes (5): Agentic Search Challenge, Guidelines, How we'll evaluate, Minimum Requirements, Submission

### Community 25 - "Community 25"
Cohesion: 0.33
Nodes (6): API Reference, DELETE /api/cache, GET /api/providers, GET /api/server-config, GET /health, POST /api/search

### Community 26 - "Community 26"
Cohesion: 0.50
Nodes (4): Auto-deploy, Deployment on Render (Free), Prerequisites, Steps

### Community 27 - "Community 27"
Cohesion: 0.50
Nodes (4): Dev sim-prod toggle (local only), Local dev mode, Local vs Production Behaviour, Production mode

### Community 28 - "Community 28"
Cohesion: 0.67
Nodes (3): Adding a New Provider, LLM provider, Search provider

## Knowledge Gaps
- **76 isolated node(s):** `name`, `private`, `version`, `type`, `packageManager` (+71 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `BaseLLMProvider` connect `Web Scraping Pipeline` to `Agent Logic Layer`, `Provider Contracts and Core Concepts`, `App Config and Security`, `Community 7`?**
  _High betweenness centrality (0.086) - this node is a cross-community bridge._
- **Why does `Entity` connect `Agent Logic Layer` to `Cache Layer`, `API Routes and Request Handling`, `Web Scraping Pipeline`, `Community 7`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Why does `SearchResult` connect `App Config and Security` to `Agent Logic Layer`, `Web Scraping Pipeline`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `BaseLLMProvider` (e.g. with `CacheClearResponse` and `ProviderInfo`) actually correct?**
  _`BaseLLMProvider` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `BaseSearchProvider` (e.g. with `CacheClearResponse` and `ProviderInfo`) actually correct?**
  _`BaseSearchProvider` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `SearchResult` (e.g. with `AsyncClient` and `BaseLLMProvider`) actually correct?**
  _`SearchResult` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `Settings` (e.g. with `CacheClearResponse` and `ProviderInfo`) actually correct?**
  _`Settings` has 7 INFERRED edges - model-reasoned connections that need verification._