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
- Pydantic v2 + pydantic-settings
- httpx for async HTTP
- BeautifulSoup4 + lxml for HTML parsing
- duckduckgo-search for DDG provider

**Frontend**
- React 18 + Vite
- DM Sans + DM Mono (Google Fonts)
- Plain CSS — no framework, no Tailwind
- sessionStorage for API key persistence (cleared on tab close)

**LLM Providers**
- Groq (recommended — free, fast, 14,400 req/day)
- Ollama (local)
- OpenAI
- Anthropic

**Search Providers**
- Tavily (recommended — 1000 free/month)
- Brave Search
- DuckDuckGo (free fallback)

---

## Project Structure

```
narada/
├── main.py                         FastAPI entry point — serves React build in production
├── config.py                       All settings, loaded from .env only
├── requirements.txt                Pip deps for Render deployment
├── environment.yml                 Conda env for local dev (Python 3.12)
├── render.yaml                     Render deployment config
├── .python-version                 Pins Python 3.12.3 for Render
├── .gitignore                      Excludes .env, .cache/, keeps frontend/dist/
├── CLAUDE.md                       This file
│
├── .github/
│   └── workflows/
│       └── build-frontend.yml      Auto-builds frontend on push to frontend/src/** etc.
│
├── core/
│   ├── models.py                   All Pydantic data shapes — read first
│   ├── pipeline.py                 Orchestrates all 7 steps in order
│   └── cache.py                    Disk cache (.cache/ dir, SHA256 keyed)
│
├── providers/
│   ├── base.py                     Abstract contracts: BaseLLMProvider, BaseSearchProvider
│   ├── factory.py                  Per-step provider resolution from settings
│   ├── llm/
│   │   ├── ollama.py               num_ctx configurable per call
│   │   ├── groq.py                 OpenAI-compatible endpoint
│   │   ├── openai.py
│   │   └── anthropic.py
│   └── search/
│       ├── tavily.py               Key validated at search() time, not __init__
│       ├── brave.py
│       └── duckduckgo.py
│
├── agents/
│   ├── query_analyzer.py           Step 1: entity_type, attributes[], search_queries[]
│   ├── scraper.py                  Step 3: async concurrent, _BLOCKED_DOMAINS list
│   ├── extractor.py                Step 4: primary-subject rule, _INVALID_VALUES filter
│   ├── aggregator.py               Step 5: name normalization, attribute merging
│   └── validator.py                Step 6: LLM noise filter, keep-borderline strategy
│
├── api/
│   └── routes.py                   POST /api/search, DELETE /api/cache, GET /api/providers
│                                   Keys read from x- headers, not body
│                                   ValueError → 400, other exceptions → 500
│
└── frontend/
    ├── package.json
    ├── vite.config.js               Dev: proxies /api to localhost:8000
    ├── index.html                   Links favicon.ico from /public/
    └── src/
        ├── main.jsx
        ├── App.jsx                  Search UI, buildHeaders(), step loading tracker
        ├── components/
        │   ├── Sidebar.jsx          Always-visible settings panel, sessionStorage keys
        │   └── ResultsTable.jsx     Expandable rows, source chips per cell
        ├── hooks/
        │   └── useSession.js        useState backed by sessionStorage
        └── styles/
            └── main.css             All styles, CSS variables, no framework
                                     Base font 16px, sidebar 320px wide
```

---

## Pipeline Flow

```
POST /api/search  body: {query, refresh}
  Headers: x-groq-api-key, x-tavily-api-key, x-search-provider,
           x-query-analyzer-provider, x-query-analyzer-model,
           x-extractor-provider, x-extractor-model,
           x-validator-provider, x-validator-model
  ↓
_build_settings_from_headers()   merges request headers into Settings for this request only
  ↓
Step 1  analyze_query()          LLM: entity_type, attributes[], search_queries[]
Step 2  _run_searches()          Search: list[SearchResult], deduplicated by URL
Step 3  scrape_pages()           httpx async concurrent: list[ScrapedPage]
Step 4  extract_entities()       LLM per page sequential: list[Entity]
Step 5  aggregate_entities()     Pure logic: dedup + merge attributes
Step 6  validate_entities()      LLM: filter noise entities
Step 7  cache write              .cache/<sha256>.json
  ↓
SearchResponse { result: PipelineResult }
```

---

## Key Data Models (core/models.py)

```python
CellValue       value: str, source_url: str         # every attribute is traceable
Entity          name: str, attributes: dict[str, CellValue]
QueryAnalysis   original_query, entity_type, attributes[], search_queries[]
ScrapedPage     url, title, content (plain text, capped at 2500 chars)
PipelineResult  query, entity_type, attributes[], entities[], metadata
PipelineMetadata search_provider, llm_provider, llm_model, pages_scraped, duration_seconds
```

---

## Per-Step LLM Configuration

```
LLM_PROVIDER                    default fallback for all steps

QUERY_ANALYZER_LLM_PROVIDER  +  QUERY_ANALYZER_OLLAMA_MODEL
EXTRACTION_LLM_PROVIDER      +  EXTRACTION_OLLAMA_MODEL
VALIDATOR_LLM_PROVIDER       +  VALIDATOR_OLLAMA_MODEL
```

Factory functions (providers/factory.py):
- `get_llm_provider(settings)`          default
- `get_query_analyzer_llm(settings)`    step 1
- `get_extraction_llm(settings)`        step 4
- `get_validator_llm(settings)`         step 6
- `get_search_provider(settings)`       search

---

## API Key Security Model

Keys sent as custom request headers — excluded from server access logs by default:
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

- Override .env for that request only — never stored server-side
- Error logs emit `type(e).__name__` only — never key material
- ValueError (missing/invalid key) → HTTP 400 with user-friendly message
- sessionStorage in browser — cleared on tab close
- CSP headers block XSS from reading sessionStorage

---

## Environment Variables

```bash
# Core
LLM_PROVIDER=groq
SEARCH_PROVIDER=tavily
ENVIRONMENT=development             # development | production

# Per-step LLM overrides (empty = fall back to LLM_PROVIDER)
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
ALLOWED_ORIGIN=https://your-app.onrender.com
LOG_LEVEL=WARNING
```

---

## Local Development

```bash
# 1. Create Conda env
conda env create -f environment.yml
conda activate narada

# 2. Configure
cp .env.example .env   # or create .env manually — see env vars above

# 3. Backend
uvicorn main:app --reload
# http://localhost:8000  |  Swagger: http://localhost:8000/docs

# 4. Frontend (separate terminal)
cd frontend
npm install
npm run dev
# http://localhost:5173  (proxies /api to localhost:8000)
```

## Production Build (test locally)

```bash
cd frontend && npm run build && cd ..
uvicorn main:app --host 0.0.0.0 --port 8000
# http://localhost:8000 serves both frontend and API
```

---

## Deployment (Render)

- `render.yaml` at repo root handles all config
- `requirements.txt` for pip deps
- `.python-version` pins Python 3.12.3
- Frontend is pre-built and committed to `frontend/dist/`
- GitHub Action (`.github/workflows/build-frontend.yml`) auto-rebuilds
  `frontend/dist/` on any push that touches `frontend/src/**` etc.
- Render redeploys automatically on every push to main

Secret env vars to set in Render dashboard (not in render.yaml):
- `GROQ_API_KEY`
- `TAVILY_API_KEY`

---

## CI/CD

`.github/workflows/build-frontend.yml` triggers on push to main when
these paths change: `frontend/src/**`, `frontend/index.html`,
`frontend/package.json`, `frontend/vite.config.js`

It installs, builds, and commits `frontend/dist/` back with `[skip ci]`
to prevent infinite loops. Requires repo **Read and write permissions**
under Settings → Actions → General → Workflow permissions.

---

## Invariant Rules — Never Break

1. No hardcoded values. Every URL, key, model name lives in .env / config.py.
2. Never import a concrete provider in agents or pipeline. Use factory.py.
3. All structured data uses Pydantic models. No raw dicts between agents.
4. Every LLM call must include a system prompt. Never send a bare user message.
5. Every Entity attribute must have a source_url set on the CellValue.
6. Async throughout. Use httpx.AsyncClient, never requests.
7. Error logs must never contain key material. Log type(e).__name__ only.
8. Provider __init__ must not raise on empty keys — raise in the method that uses the key.
9. ValueError from missing/bad config returns HTTP 400, not 500.
10. The .cache/ directory is gitignored. Never commit cached results.
11. frontend/dist/ is committed and kept in sync by the GitHub Action.
12. Keys go in sessionStorage only. Never localStorage, never cookies.

---

## What's Complete

- [x] core/models.py
- [x] core/pipeline.py — 7-step orchestration with disk cache
- [x] core/cache.py
- [x] providers/base.py
- [x] providers/factory.py — per-step provider resolution
- [x] providers/llm/ollama.py
- [x] providers/llm/groq.py
- [x] providers/llm/openai.py
- [x] providers/llm/anthropic.py
- [x] providers/search/tavily.py
- [x] providers/search/brave.py
- [x] providers/search/duckduckgo.py
- [x] agents/query_analyzer.py
- [x] agents/scraper.py
- [x] agents/extractor.py
- [x] agents/aggregator.py
- [x] agents/validator.py
- [x] api/routes.py — header-based key injection, 400 for config errors
- [x] main.py — security middleware, serves React build
- [x] frontend — sidebar, results table, sessionStorage, buildHeaders()
- [x] requirements.txt + render.yaml + .python-version
- [x] .github/workflows/build-frontend.yml
- [x] README.md