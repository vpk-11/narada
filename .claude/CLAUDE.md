# NARADA — Claude Code Context

This file tells Claude Code everything it needs to work on this project.
Read this before touching any file.

---

## What This Is

Narada is an agentic search pipeline.
It takes a user query, searches the web, scrapes pages, uses an LLM to extract
structured entity data, deduplicates across sources, and returns a traceable table.

Named after the Hindu divine sage Narada — the first journalist,
who traveled all three worlds gathering and delivering structured knowledge.

---

## Stack

- Python 3.12
- FastAPI + uvicorn
- Pydantic v2 + pydantic-settings for all data models and config
- httpx for async HTTP (scraping + Ollama API calls)
- duckduckgo-search for web search (no API key)
- BeautifulSoup4 + lxml for HTML parsing
- Ollama for local LLM inference (primary)
- OpenAI / Anthropic as optional swappable providers

---

## Project Structure

```
narada/
├── main.py                        # FastAPI app entry point
├── config.py                      # All settings, read from .env only
├── environment.yml                # Conda env (use this, not pip directly)
├── .env.example                   # Copy to .env and fill in values
├── .gitignore
├── core/
│   ├── __init__.py
│   └── models.py                  # All Pydantic data shapes — start here
├── providers/
│   ├── __init__.py
│   ├── base.py                    # Abstract contracts: BaseLLMProvider, BaseSearchProvider
│   ├── factory.py                 # Builds correct provider from settings
│   ├── llm/
│   │   ├── __init__.py
│   │   └── ollama.py              # Ollama implementation
│   └── search/
│       ├── __init__.py
│       └── duckduckgo.py          # DuckDuckGo implementation
├── agents/
│   ├── __init__.py
│   ├── query_analyzer.py          # TODO: Step 1 — analyze query, produce schema + search queries
│   ├── scraper.py                 # TODO: Step 3 — async scrape URLs, return clean text
│   ├── extractor.py               # TODO: Step 4 — LLM extracts entities per page
│   └── aggregator.py              # TODO: Step 5 — merge entities across sources
├── core/
│   └── pipeline.py                # TODO: Orchestrates all agents end to end
└── api/
    ├── __init__.py
    └── routes.py                  # TODO: FastAPI route definitions
```

---

## Core Design Principles

**Provider pattern:** The pipeline never imports concrete providers.
It calls `get_llm_provider(settings)` and `get_search_provider(settings)` from
`providers/factory.py`. Swapping providers = changing one value in .env.

**No hardcoding:** Every URL, API key, model name, and config value
lives in `.env`. `config.py` reads them via pydantic-settings.
If you see a raw string where a setting should be — fix it.

**Interfaces first:** `core/models.py` defines all data shapes.
Read it before writing any agent logic.

**One thing per function:** Early returns, no deep nesting.
Type hints on every function signature.
Docstrings on anything non-obvious.

---

## Data Flow

```
User query
  → QueryAnalysisAgent     produces: QueryAnalysis (entity_type, attributes, search_queries)
  → SearchProvider         produces: list[SearchResult]
  → Scraper                produces: list[ScrapedPage]
  → ExtractionAgent        produces: list[Entity] per page (with CellValue.source_url per attribute)
  → Aggregator             produces: deduplicated list[Entity]
  → PipelineResult         returned by API
```

---

## Key Models (core/models.py)

- `SearchResult` — url, title, snippet from search provider
- `ScrapedPage` — url, title, clean plain-text content
- `CellValue` — value + source_url (every cell is traceable)
- `Entity` — name + dict[attribute_name, CellValue]
- `QueryAnalysis` — entity_type, attributes[], search_queries[]
- `PipelineResult` — full output: query, entity_type, attributes, entities, metadata

---

## Setup

```bash
conda env create -f environment.yml
conda activate narada
cp .env.example .env
# Fill in .env values — at minimum set OLLAMA_BASE_URL and OLLAMA_MODEL
uvicorn main:app --reload
# GET http://localhost:8000/health should return {"status": "ok", ...}
```

---

## What's Built

- [x] environment.yml
- [x] .env.example + .gitignore
- [x] core/models.py — all data shapes
- [x] providers/base.py — abstract contracts
- [x] providers/llm/ollama.py — Ollama implementation
- [x] providers/search/duckduckgo.py — DDG implementation
- [x] providers/factory.py — provider instantiation
- [x] config.py — settings from env
- [x] main.py — FastAPI skeleton with /health

## What's Next (in order)

- [ ] agents/query_analyzer.py
- [ ] agents/scraper.py
- [ ] agents/extractor.py
- [ ] agents/aggregator.py
- [ ] core/pipeline.py
- [ ] api/routes.py
- [ ] providers/llm/openai.py
- [ ] providers/llm/anthropic.py
- [ ] providers/search/brave.py
- [ ] providers/search/tavily.py

---

## Rules — Never Break These

1. No hardcoded values. No URLs, keys, or model names outside .env + config.py.
2. Never import a concrete provider directly in agents or pipeline. Use factory.py.
3. All structured data uses Pydantic models — no raw dicts passed between agents.
4. Every LLM call includes a system prompt. Never send a bare user message.
5. Every attribute value in Entity.attributes must have a source_url set.
6. Async throughout — use httpx.AsyncClient, not requests.
