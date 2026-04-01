# NARADA — Claude Code Context

Read this entire file before touching anything.
This is the source of truth for the project state, architecture, and rules.

---

## What This Is

Narada is an agentic search pipeline.
It takes a user query, searches the web, scrapes pages, uses an LLM to extract
structured entity data, deduplicates across sources, validates quality,
and returns a source-traceable table.

Named after the Hindu divine sage Narada: the first journalist,
who traveled all three worlds gathering and delivering structured knowledge.

---

## Stack

**Backend**
- Python 3.12
- FastAPI + uvicorn
- Pydantic v2 + pydantic-settings for all data models and config
- httpx for async HTTP (scraping + LLM API calls)
- BeautifulSoup4 + lxml for HTML parsing
- duckduckgo-search for DDG provider (no API key needed)

**Frontend**
- React 18 + Vite
- DM Sans + DM Mono (Google Fonts)
- Plain CSS (no Tailwind, no CSS framework)
- sessionStorage for API key persistence

**LLM Providers (all swappable via .env)**
- Ollama (local)
- Groq (recommended, free tier 14,400 req/day)
- OpenAI
- Anthropic

**Search Providers (all swappable via .env)**
- Tavily (recommended, 1000 free/month)
- Brave Search
- DuckDuckGo (free fallback, rate limits)

---

## Project Structure

```
narada/
├── main.py                         FastAPI entry point — also serves React build
├── config.py                       All settings, loaded from .env only
├── requirements.txt                Pip deps for Render deployment
├── environment.yml                 Conda env for local dev (Python 3.12)
├── render.yaml                     Render deployment config
├── .gitignore
├── CLAUDE.md                       This file
│
├── core/
│   ├── models.py                   All Pydantic data shapes — read first
│   ├── pipeline.py                 Orchestrates all 7 steps in order
│   └── cache.py                    Disk-based result cache (.cache/ dir)
│
├── providers/
│   ├── base.py                     Abstract contracts: BaseLLMProvider, BaseSearchProvider
│   ├── factory.py                  Builds per-step providers from settings
│   ├── llm/
│   │   ├── ollama.py
│   │   ├── groq.py
│   │   ├── openai.py
│   │   └── anthropic.py
│   └── search/
│       ├── tavily.py
│       ├── brave.py
│       └── duckduckgo.py
│
├── agents/
│   ├── query_analyzer.py           Step 1: schema + targeted search query generation
│   ├── scraper.py                  Step 3: async concurrent page scraping
│   ├── extractor.py                Step 4: LLM entity extraction per page
│   ├── aggregator.py               Step 5: deduplication + attribute merging
│   └── validator.py                Step 6: LLM post-extraction quality filter
│
├── api/
│   └── routes.py                   POST /api/search, DELETE /api/cache, GET /api/providers
│
└── frontend/
    ├── package.json
    ├── vite.config.js               Dev: proxies /api to localhost:8000
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx                  Main layout, search logic, buildHeaders()
        ├── components/
        │   ├── Sidebar.jsx          Settings panel: keys, providers, step config
        │   └── ResultsTable.jsx     Expandable rows table with source chips
        ├── hooks/
        │   └── useSession.js        useState backed by sessionStorage
        └── styles/
            └── main.css             All styles, CSS variables, no framework
```

---

## Pipeline Flow

```
POST /api/search {query, refresh}
  Headers: x-groq-api-key, x-tavily-api-key, x-extractor-provider, etc.
  ↓
_build_settings_from_headers()   merges request headers into Settings
  ↓
Step 1  analyze_query()          LLM: entity_type, attributes[], search_queries[]
Step 2  _run_searches()          Search provider: list[SearchResult], deduplicated by URL
Step 3  scrape_pages()           Async httpx: list[ScrapedPage] (concurrent)
Step 4  extract_entities()       LLM per page: list[Entity] (sequential on Ollama)
Step 5  aggregate_entities()     Pure logic: dedup + merge attributes across sources
Step 6  validate_entities()      LLM: filter noise entities that don't match query
Step 7  cache write              SHA256(query+provider+model+search) → .cache/*.json
  ↓
SearchResponse { result: PipelineResult }
```

---

## Key Data Models (core/models.py)

```python
CellValue       value: str, source_url: str       # every cell is traceable
Entity          name: str, attributes: dict[str, CellValue]
QueryAnalysis   original_query, entity_type, attributes[], search_queries[]
ScrapedPage     url, title, content (plain text, max 2500 chars)
PipelineResult  query, entity_type, attributes[], entities[], metadata
```

---

## Per-Step LLM Configuration

Each step can use a different provider and model.
All steps fall back to LLM_PROVIDER if not explicitly configured.

```
QUERY_ANALYZER_LLM_PROVIDER  + QUERY_ANALYZER_OLLAMA_MODEL
EXTRACTION_LLM_PROVIDER      + EXTRACTION_OLLAMA_MODEL
VALIDATOR_LLM_PROVIDER       + VALIDATOR_OLLAMA_MODEL
```

Factory functions:
- `get_llm_provider(settings)`          default provider
- `get_query_analyzer_llm(settings)`    step 1
- `get_extraction_llm(settings)`        step 4
- `get_validator_llm(settings)`         step 6
- `get_search_provider(settings)`       search

---

## API Key Security Model

Keys are passed from the browser as custom request headers:
```
x-groq-api-key
x-openai-api-key
x-anthropic-api-key
x-tavily-api-key
x-brave-api-key
x-ollama-base-url
x-search-provider
x-query-analyzer-provider / x-query-analyzer-model
x-extractor-provider / x-extractor-model
x-validator-provider / x-validator-model
```

- Keys override .env for that request only
- Never stored server-side
- Never logged (error logs emit type(e).__name__ only)
- sessionStorage in browser: cleared on tab close
- CSP headers block XSS from reading sessionStorage
- HTTPS enforced in production via FORCE_HTTPS=true

---

## Environment Variables (.env)

```bash
# Core
LLM_PROVIDER=groq                   # ollama | groq | openai | anthropic
SEARCH_PROVIDER=tavily              # tavily | brave | duckduckgo
ENVIRONMENT=development             # development | production

# Per-step overrides (leave empty to fall back to LLM_PROVIDER)
QUERY_ANALYZER_LLM_PROVIDER=
EXTRACTION_LLM_PROVIDER=
VALIDATOR_LLM_PROVIDER=

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:4b
QUERY_ANALYZER_OLLAMA_MODEL=
EXTRACTION_OLLAMA_MODEL=
VALIDATOR_OLLAMA_MODEL=

# Groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile

# OpenAI (optional)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Anthropic (optional)
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-haiku-4-5-20251001

# Tavily
TAVILY_API_KEY=tvly-...

# Brave (optional)
BRAVE_API_KEY=BSA_...

# Pipeline tuning
SEARCH_RESULTS_PER_QUERY=8
MAX_PAGES_TO_SCRAPE=6
SCRAPE_TIMEOUT_SECONDS=10

# Production only
FORCE_HTTPS=true
ALLOWED_ORIGIN=https://narada.onrender.com
LOG_LEVEL=WARNING
```

---

## Local Development Setup

```bash
# 1. Create and activate Conda env
conda env create -f environment.yml
conda activate narada

# 2. Set up environment
cp .env.example .env
# Edit .env — set at minimum GROQ_API_KEY and TAVILY_API_KEY

# 3. Start backend
uvicorn main:app --reload
# API available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs

# 4. Start frontend (separate terminal)
cd frontend
npm install
npm run dev
# UI available at http://localhost:5173
# /api requests proxied to localhost:8000 via vite.config.js
```

---

## Production Build (test before deploying)

```bash
# Build React to static files
cd frontend && npm run build && cd ..

# Run FastAPI — it will serve the React build automatically
uvicorn main:app --host 0.0.0.0 --port 8000
# Now http://localhost:8000 serves the full app (frontend + API)
```

---

## Deployment (Render)

See README.md for full step-by-step instructions.
render.yaml handles everything automatically once connected to GitHub.

Key env vars to set in Render dashboard (not in render.yaml):
- GROQ_API_KEY
- TAVILY_API_KEY

---

## Invariant Rules — Never Break

1. No hardcoded values anywhere. Every URL, key, model name lives in .env / config.py.
2. Never import a concrete provider in agents or pipeline. Always use factory.py functions.
3. All structured data uses Pydantic models. No raw dicts between agents.
4. Every LLM call must include a system prompt. Never send a bare user message.
5. Every Entity attribute must have a source_url set on the CellValue.
6. Async throughout. Use httpx.AsyncClient, never requests.
7. Error logs must never contain key material. Log type(e).__name__ only.
8. _build_settings_from_headers() in routes.py is the only place keys touch the server.
9. The .cache/ directory is gitignored. Never commit cached results.
10. Frontend keys go in sessionStorage only. Never localStorage, never cookies.

---

## What's Complete

- [x] core/models.py — all data shapes
- [x] core/pipeline.py — 7-step orchestration with cache
- [x] core/cache.py — disk cache, SHA256 keyed
- [x] providers/base.py — abstract contracts
- [x] providers/factory.py — per-step provider resolution
- [x] providers/llm/ollama.py — configurable num_ctx per call
- [x] providers/llm/groq.py — OpenAI-compatible endpoint
- [x] providers/llm/openai.py
- [x] providers/llm/anthropic.py
- [x] providers/search/tavily.py — primary, recommended
- [x] providers/search/brave.py
- [x] providers/search/duckduckgo.py — free fallback
- [x] agents/query_analyzer.py — dynamic schema + targeted search queries
- [x] agents/scraper.py — async concurrent, domain blocklist
- [x] agents/extractor.py — primary-subject rule, invalid value filter
- [x] agents/aggregator.py — name normalization, attribute merging
- [x] agents/validator.py — post-aggregation LLM quality filter
- [x] api/routes.py — keys via headers, never body
- [x] main.py — security middleware, serves React build in production
- [x] frontend/src/App.jsx — search UI, buildHeaders()
- [x] frontend/src/components/Sidebar.jsx — sessionStorage key config
- [x] frontend/src/components/ResultsTable.jsx — expandable rows
- [x] frontend/src/hooks/useSession.js
- [x] requirements.txt — for Render
- [x] render.yaml — Render deployment config
- [x] README.md — full setup + deployment docs