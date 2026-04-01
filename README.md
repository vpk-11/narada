# Narada

Narada takes a research query, searches the web, scrapes relevant pages, and returns a structured table of entities with every attribute value traced to its source URL.

Named after the Hindu divine sage Narada: the first journalist, who traveled all three worlds gathering and delivering structured knowledge.

**Example:** Query `"AI startups in healthcare"` returns a table of companies with columns like `founded`, `funding_raised`, `headquarters`, `what_they_do` -- each cell linked to the exact URL it came from.

---

## How It Works

The pipeline runs 7 steps:

```
Query
  1. Query Analyzer    LLM determines entity type, dynamic column schema, targeted search queries
  2. Search            Runs 2-3 search queries, deduplicates URLs
  3. Scraper           Fetches and cleans all pages concurrently (async)
  4. Extractor         LLM reads each page, pulls structured entity data (sequential)
  5. Aggregator        Deduplicates entities across sources, merges attributes
  6. Validator         LLM filters out noise entities that don't match the query
  7. Cache             Writes result to disk -- identical queries return instantly
```

**What makes this different from just asking an LLM:**
- The schema is dynamic: "AI startups" gets different columns than "pizza places"
- Entities found across multiple sources get merged into one row
- Every cell value carries a `source_url` -- full traceability
- The output is a structured table, not a prose answer

---

## Architecture

### Provider Pattern

Every LLM and search dependency sits behind an abstract interface. The pipeline never imports a concrete provider directly. Swapping providers means changing one line in `.env`.

```
BaseLLMProvider         BaseSearchProvider
    ollama                  tavily
    groq                    brave
    openai                  duckduckgo
    anthropic
```

### Per-Step LLM Configuration

Each pipeline step can use a different LLM provider and model. All steps fall back to `LLM_PROVIDER` if not explicitly configured.

```
Step 1 (Query Analyzer)  QUERY_ANALYZER_LLM_PROVIDER  fallback: LLM_PROVIDER
Step 4 (Extractor)       EXTRACTION_LLM_PROVIDER       fallback: LLM_PROVIDER
Step 6 (Validator)       VALIDATOR_LLM_PROVIDER         fallback: LLM_PROVIDER
```

This enables setups like:
- Full local: all steps on Ollama with different models per step
- Hybrid: Ollama for lightweight steps, Groq for heavy extraction
- Full cloud: all steps on Groq or OpenAI

### Project Structure

```
narada/
├── main.py                        FastAPI entry point
├── config.py                      All settings, loaded from .env
├── environment.yml                Conda environment (Python 3.12)
├── CLAUDE.md                      Context file for Claude Code
│
├── core/
│   ├── models.py                  All Pydantic data shapes
│   ├── pipeline.py                Orchestrates all agents in order
│   └── cache.py                   Disk-based result cache
│
├── providers/
│   ├── base.py                    Abstract base classes
│   ├── factory.py                 Builds providers from settings
│   ├── llm/
│   │   ├── ollama.py
│   │   ├── groq.py
│   │   ├── openai.py              (stub -- implement as needed)
│   │   └── anthropic.py           (stub -- implement as needed)
│   └── search/
│       ├── tavily.py
│       ├── brave.py
│       └── duckduckgo.py
│
├── agents/
│   ├── query_analyzer.py          Step 1: schema + search query generation
│   ├── scraper.py                 Step 3: async concurrent page fetching
│   ├── extractor.py               Step 4: LLM entity extraction per page
│   ├── aggregator.py              Step 5: deduplication + attribute merging
│   └── validator.py               Step 6: post-extraction quality filter
│
└── api/
    └── routes.py                  FastAPI route definitions
```

---

## Setup

### Prerequisites

- [Anaconda](https://www.anaconda.com) or Miniconda
- [Ollama](https://ollama.com) (if using local models)
- A Groq API key (free, recommended) or other LLM provider
- A Tavily API key (free, recommended) or other search provider

### 1. Create the Conda environment

```bash
conda env create -f environment.yml
conda activate narada
```

### 2. Configure environment variables

Create a `.env` file in the project root. All variables are listed below.

### 3. Pull Ollama models (if using Ollama)

```bash
ollama pull qwen3:4b
ollama pull llama3.2:3b
```

Pre-load the model before first use to avoid cold-start timeouts:

```bash
ollama run qwen3:4b
# wait for it to load, then type /bye
```

### 4. Start the server

```bash
uvicorn main:app --reload
```

### 5. Open API docs

```
http://localhost:8000/docs
```

---

## Environment Variables

Copy the block below into a `.env` file at your project root. This file is the only place secrets and config live. It is gitignored -- never commit it.

```bash
# ============================================================
# PROVIDER SELECTION
# ============================================================

# Default LLM provider -- fallback for all steps not explicitly configured.
# Options: ollama | groq | openai | anthropic
LLM_PROVIDER=groq

# Search provider
# Options: tavily | brave | duckduckgo
SEARCH_PROVIDER=tavily


# ============================================================
# PER-STEP LLM OVERRIDES
# Leave empty to fall back to LLM_PROVIDER for that step.
# ============================================================

# Step 1: query analysis (short reasoning, schema + search query generation)
# Recommended: ollama with qwen3:4b (fast local, good at structured JSON)
QUERY_ANALYZER_LLM_PROVIDER=
QUERY_ANALYZER_OLLAMA_MODEL=

# Step 4: entity extraction (reading dense content, structured output)
# Recommended: groq with llama-3.3-70b-versatile (fast, high quality)
EXTRACTION_LLM_PROVIDER=
EXTRACTION_OLLAMA_MODEL=

# Step 6: post-extraction validation (filtering noise entities)
# Recommended: groq (same model as extraction, cheap call)
VALIDATOR_LLM_PROVIDER=
VALIDATOR_OLLAMA_MODEL=


# ============================================================
# OLLAMA
# No API key required. Ollama must be running locally.
# https://ollama.com
# ============================================================

OLLAMA_BASE_URL=http://localhost:11434

# Default model -- used by all Ollama steps unless overridden above
OLLAMA_MODEL=qwen3:4b


# ============================================================
# GROQ
# Free tier: 14,400 requests/day. No rate limiting. Extremely fast.
# Sign up: https://console.groq.com
#
# Recommended models:
#   llama-3.3-70b-versatile   best quality, still fast
#   llama-3.1-8b-instant      fastest, good for lightweight steps
#   qwen-qwq-32b              strong reasoning
# ============================================================

GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile


# ============================================================
# OPENAI (optional)
# ============================================================

OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini


# ============================================================
# ANTHROPIC (optional)
# ============================================================

ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-haiku-4-5-20251001


# ============================================================
# TAVILY
# Free tier: 1000 searches/month. Built for AI agents.
# Sign up: https://tavily.com
# ============================================================

TAVILY_API_KEY=


# ============================================================
# BRAVE SEARCH (optional)
# Free tier: 2000 queries/month. High quality results.
# Sign up: https://brave.com/search/api
# ============================================================

BRAVE_API_KEY=


# ============================================================
# PIPELINE TUNING
# ============================================================

# Number of search results to fetch per search query
# More results = more pages scraped = better coverage but slower
SEARCH_RESULTS_PER_QUERY=8

# Maximum pages to scrape per pipeline run
# Increase for better entity coverage, decrease for speed
MAX_PAGES_TO_SCRAPE=6

# Per-page scrape timeout in seconds
SCRAPE_TIMEOUT_SECONDS=10


# ============================================================
# LOGGING
# Options: DEBUG | INFO | WARNING | ERROR
# ============================================================

LOG_LEVEL=INFO
```

### Recommended setups

**Full Groq (fastest, best quality):**
```bash
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_xxx
GROQ_MODEL=llama-3.3-70b-versatile
# leave all step overrides empty
```

**Hybrid: local analysis, Groq extraction:**
```bash
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen3:4b
EXTRACTION_LLM_PROVIDER=groq
VALIDATOR_LLM_PROVIDER=groq
GROQ_API_KEY=gsk_xxx
GROQ_MODEL=llama-3.3-70b-versatile
```

**Full local, two models:**
```bash
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen3:4b
EXTRACTION_LLM_PROVIDER=ollama
EXTRACTION_OLLAMA_MODEL=llama3.2:3b
```

**Full local, one model:**
```bash
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen3:4b
# leave all overrides empty
```

---

## API Reference

The full interactive API is available at `http://localhost:8000/docs` (Swagger UI).

### POST /api/search

Run the pipeline for a query.

**Request body:**
```json
{
  "query": "AI startups in healthcare",
  "refresh": false
}
```

Set `refresh: true` to bypass the cache and force a fresh run.

**Response:**
```json
{
  "result": {
    "query": "AI startups in healthcare",
    "entity_type": "company",
    "attributes": ["founded", "funding_raised", "headquarters", "what_they_do"],
    "entities": [
      {
        "name": "Abridge",
        "attributes": {
          "founded": {
            "value": "2018",
            "source_url": "https://techcrunch.com/..."
          },
          "funding_raised": {
            "value": "$250 million",
            "source_url": "https://fiercehealthcare.com/..."
          }
        }
      }
    ],
    "metadata": {
      "search_provider": "tavily",
      "llm_provider": "groq",
      "llm_model": "llama-3.3-70b-versatile",
      "pages_scraped": 5,
      "duration_seconds": 13.6
    }
  }
}
```

### DELETE /api/cache

Clear all cached results.

### GET /api/providers

Returns the active provider and model for each pipeline step. Useful for confirming your config loaded correctly.

### GET /health

Liveness check. Returns `{"status": "ok"}` with active provider info.

---

## Design Decisions

**Dynamic schema per query.** The query analyzer asks the LLM to determine what columns make sense for the query before anything is searched. "AI startups" gets `founded, funding_raised, headquarters`. "Pizza places" gets `neighborhood, price_range, specialty`. The schema is not hardcoded.

**Source traceability at the cell level.** Every attribute value is a `CellValue(value, source_url)`. Every cell in the output table knows exactly which page it came from. This is enforced in the data model -- it is impossible to store a value without a source.

**Provider pattern over direct imports.** No agent or pipeline code imports a concrete LLM or search implementation. Everything goes through `BaseLLMProvider` and `BaseSearchProvider`. Adding a new provider means implementing one class and registering it in `factory.py`.

**Per-step LLM configuration.** Different pipeline steps have different requirements. Query analysis is a short reasoning task -- a lightweight local model handles it well. Extraction reads dense content and needs higher quality. The architecture allows each step to use the best model for its job without changing any pipeline logic.

**Sequential extraction, concurrent scraping.** Scraping is I/O-bound -- all pages fetch in parallel with `asyncio.gather`. Extraction is compute-bound and LLM-sequential -- especially on Ollama, which handles one request at a time. Running extraction in parallel against a local model causes timeouts.

**Aggregation before validation.** Deduplication runs first (pure logic, no LLM), then a single validation call sees the full merged entity list. This is cheaper than validating per-page extractions and produces better results because the validator sees relative context across all entities at once.

**Disk cache over memory cache.** Results survive server restarts. No Redis dependency. Cache entries are plain JSON files in `.cache/` -- easy to inspect or delete manually. Cache key is a SHA256 hash of `query + provider + model + search_provider`.

---

## Known Limitations

**Extraction quality depends on source pages.** If Tavily returns a generic listicle that mentions 40 companies in passing, the extractor will pull noise entities. The validator catches most of these but not all. Queries targeting specific domains (e.g. "YC-backed AI healthcare startups") produce cleaner results than broad queries.

**Local model speed.** On an M2 MacBook Air with 8GB RAM, full local runs take 3-6 minutes with Qwen3:4b. Groq reduces this to under 15 seconds. The pipeline architecture is the same in both cases -- the bottleneck is inference speed.

**Attribute completeness varies.** If a page doesn't mention a company's founding year, that cell will be empty in the output. The aggregator merges attributes across sources, so entities found on multiple pages tend to have more complete data.

**Domain blocking is manual.** `agents/scraper.py` has a `_BLOCKED_DOMAINS` set of known low-quality sources. This is a manual list -- new bad sources need to be added manually as discovered.

**Search query quality affects everything.** The query analyzer generates search queries from the user's input. A vague input produces vague queries which return off-topic pages. More specific queries produce more accurate results.

---

## Adding a New Provider

### LLM provider

1. Create `providers/llm/yourprovider.py`
2. Implement `BaseLLMProvider` (see `providers/base.py` for the contract)
3. Add the provider name to `providers/factory.py` in `_build_llm()`
4. Add the API key and model config fields to `config.py`
5. Document in this README

### Search provider

1. Create `providers/search/yourprovider.py`
2. Implement `BaseSearchProvider`
3. Register in `providers/factory.py` in `get_search_provider()`
4. Add config fields to `config.py`

---

## Running Tests

```bash
# Liveness check
curl http://localhost:8000/health

# Check active providers
curl http://localhost:8000/api/providers

# Run a search (replace with your Groq/Tavily keys)
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "AI startups in healthcare", "refresh": true}'

# Clear cache
curl -X DELETE http://localhost:8000/api/cache
```

---

## Submission Notes

This project was built for the CIIR Agentic Search Challenge.

The core research question: can a structured entity extraction pipeline outperform a simple "LLM + web search" approach by combining targeted search query generation, concurrent scraping, structured extraction, cross-source aggregation, and post-extraction validation -- all with full source traceability?

The answer is yes, with the expected tradeoffs between quality and speed documented above.