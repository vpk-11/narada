# Narada

Narada takes a research query, searches the web, scrapes relevant pages, and returns a structured table of entities with every attribute value traced to its source URL.

Named after the Hindu divine sage Narada: the first journalist, who traveled all three worlds gathering and delivering structured knowledge.

**Example:** Query `"AI startups in healthcare"` returns a table of companies with columns like `founded`, `funding_raised`, `headquarters`, `what_they_do` — each cell linked to the exact URL it came from.

**Live demo:** https://narada-heij.onrender.com

---

## How It Works

The pipeline runs 7 steps:

```
Query
  1. Query Analyzer    LLM determines entity type, dynamic column schema, targeted search queries
  2. Search            Runs 2-3 search queries, deduplicates URLs
  3. Scraper           Fetches and cleans all pages concurrently (async)
  4. Extractor         LLM reads each page, pulls structured entity data (sequential)
  5. Aggregator        Deduplicates entities, merges attributes across sources
  6. Validator         LLM filters out noise entities that don't match the query
  7. Cache             Writes result to disk — identical queries return instantly
```

**What makes this different from just asking an LLM:**
- Schema is dynamic per query — "AI startups" gets different columns than "pizza places"
- Entities found across multiple sources get merged into one row
- Every cell value carries a `source_url` — full traceability at the cell level
- Post-extraction validation filters noise (investors, legacy companies, off-topic entities)

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
Step 1 (Query Analyzer)  QUERY_ANALYZER_LLM_PROVIDER  →  LLM_PROVIDER
Step 4 (Extractor)       EXTRACTION_LLM_PROVIDER       →  LLM_PROVIDER
Step 6 (Validator)       VALIDATOR_LLM_PROVIDER         →  LLM_PROVIDER
```

### API Key Security

Keys are sent from the browser as custom request headers (`x-groq-api-key`, `x-tavily-api-key`, etc.) — not in the request body. Headers are excluded from server access logs by default.

- Stored in browser `sessionStorage` — cleared when the tab closes
- Used per-request and never stored server-side
- Error logs emit `type(e).__name__` only — key material never appears in logs
- CSP headers prevent XSS from reading sessionStorage
- HTTPS enforced in production

This means the deployed app has no secrets of its own. Users bring their own API keys.

### Project Structure

```
narada/
├── main.py                        FastAPI entry — serves React build in production
├── config.py                      All settings from .env only
├── requirements.txt               Pip deps for Render
├── render.yaml                    Render deployment config
├── .python-version                Pins Python 3.12.3
├── environment.yml                Conda env for local dev
│
├── .github/workflows/
│   └── build-frontend.yml         Auto-builds frontend on push
│
├── core/
│   ├── models.py                  All Pydantic data shapes
│   ├── pipeline.py                Orchestrates all steps
│   └── cache.py                   Disk cache (.cache/)
│
├── providers/
│   ├── base.py                    Abstract contracts
│   ├── factory.py                 Per-step provider resolution
│   ├── llm/                       ollama, groq, openai, anthropic
│   └── search/                    tavily, brave, duckduckgo
│
├── agents/
│   ├── query_analyzer.py          Step 1
│   ├── scraper.py                 Step 3
│   ├── extractor.py               Step 4
│   ├── aggregator.py              Step 5
│   └── validator.py               Step 6
│
├── api/routes.py                  REST API
│
└── frontend/
    └── src/
        ├── App.jsx
        ├── components/
        │   ├── Sidebar.jsx        Settings + key config
        │   └── ResultsTable.jsx   Expandable rows
        └── styles/main.css
```

---

## Setup

### Prerequisites

- [Anaconda](https://www.anaconda.com) or Miniconda
- [Ollama](https://ollama.com) (optional — only if using local models)
- A Groq API key — free at [console.groq.com](https://console.groq.com)
- A Tavily API key — free at [tavily.com](https://tavily.com)

### 1. Create the Conda environment

```bash
conda env create -f environment.yml
conda activate narada
```

### 2. Configure environment variables

Create a `.env` file in the project root. Full reference below.

### 3. Pull Ollama models (only if using Ollama)

```bash
ollama pull qwen3:4b
ollama run qwen3:4b   # pre-load, then /bye
```

### 4. Start the server

```bash
uvicorn main:app --reload
```

### 5. Start the frontend (separate terminal)

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

### 6. Open Swagger docs

```
http://localhost:8000/docs
```

---

## Environment Variables

Create a `.env` file at the project root with these values:

```bash
# ── Provider selection ──────────────────────────────────────────────────────
# Default LLM for all steps. Options: ollama | groq | openai | anthropic
LLM_PROVIDER=groq

# Options: tavily | brave | duckduckgo
SEARCH_PROVIDER=tavily

# ── Per-step LLM overrides ──────────────────────────────────────────────────
# Leave empty to fall back to LLM_PROVIDER for that step.
#
# Recommended setup:
#   LLM_PROVIDER=groq + leave all empty = everything on Groq (~10-15s)
#
# Local split:
#   LLM_PROVIDER=ollama, OLLAMA_MODEL=qwen3:4b
#   EXTRACTION_LLM_PROVIDER=groq  (heavy step, benefits from larger model)
#
QUERY_ANALYZER_LLM_PROVIDER=
EXTRACTION_LLM_PROVIDER=
VALIDATOR_LLM_PROVIDER=

# ── Ollama ──────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:4b
QUERY_ANALYZER_OLLAMA_MODEL=
EXTRACTION_OLLAMA_MODEL=
VALIDATOR_OLLAMA_MODEL=

# ── Groq ────────────────────────────────────────────────────────────────────
# Free: 14,400 requests/day. Sign up: https://console.groq.com
# Models: llama-3.3-70b-versatile | llama-3.1-8b-instant | qwen-qwq-32b
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile

# ── OpenAI (optional) ───────────────────────────────────────────────────────
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# ── Anthropic (optional) ────────────────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-haiku-4-5-20251001

# ── Tavily ──────────────────────────────────────────────────────────────────
# Free: 1000 searches/month. Sign up: https://tavily.com
TAVILY_API_KEY=tvly-...

# ── Brave (optional) ────────────────────────────────────────────────────────
BRAVE_API_KEY=BSA_...

# ── Pipeline tuning ─────────────────────────────────────────────────────────
SEARCH_RESULTS_PER_QUERY=8
MAX_PAGES_TO_SCRAPE=6
SCRAPE_TIMEOUT_SECONDS=10

# ── Logging ─────────────────────────────────────────────────────────────────
LOG_LEVEL=INFO
```

---

## API Reference

Full interactive docs at `http://localhost:8000/docs`.

### POST /api/search

Run the pipeline for a query.

**Request body:**
```json
{
  "query": "AI startups in healthcare",
  "refresh": false
}
```

**Request headers (optional — override .env for this request):**
```
x-groq-api-key: gsk_...
x-tavily-api-key: tvly-...
x-search-provider: tavily
x-query-analyzer-provider: groq
x-query-analyzer-model: llama-3.3-70b-versatile
x-extractor-provider: groq
x-extractor-model: llama-3.3-70b-versatile
x-validator-provider: groq
x-validator-model: llama-3.3-70b-versatile
```

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
          "founded": { "value": "2018", "source_url": "https://techcrunch.com/..." },
          "funding_raised": { "value": "$250 million", "source_url": "https://fiercehealthcare.com/..." }
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

Clear all cached pipeline results.

### GET /api/providers

Returns the active provider and model for each pipeline step.

### GET /health

Liveness check.

---

## Design Decisions

**Dynamic schema per query.** The query analyzer asks the LLM to determine what columns make sense before anything is searched. "AI startups" gets `founded, funding_raised, headquarters`. "Pizza places" gets `neighborhood, price_range, specialty`. The schema is not hardcoded.

**Source traceability at the cell level.** Every attribute value is a `CellValue(value, source_url)`. It is impossible to store a value without a source — enforced by the data model.

**Provider pattern.** No agent or pipeline code imports a concrete LLM or search implementation. Everything goes through abstract interfaces. Adding a new provider means implementing one class and registering it in `factory.py`.

**Per-step LLM configuration.** Query analysis is a short reasoning task — a lightweight local model handles it fine. Extraction reads dense content and benefits from a larger model. The architecture lets each step use the best model for its job.

**Sequential extraction, concurrent scraping.** Scraping is I/O-bound — all pages fetch in parallel. Extraction is compute-bound and LLM-sequential — running concurrent extraction calls against a local Ollama instance causes timeouts.

**Aggregation before validation.** Deduplication runs first (pure logic, no LLM), then one validation call sees the full merged entity list. Cheaper than validating per-page and produces better results since the validator sees relative context.

**Disk cache.** Results survive server restarts. No Redis dependency. Cache key is `SHA256(query + provider + model + search_provider)`.

**No server-side key storage.** The deployed app has no secrets of its own. Users supply their own API keys via the frontend settings panel. Keys travel as request headers, are used once, and are discarded.

---

## Known Limitations

**Extraction quality depends on source pages.** If the search returns generic listicles that mention many unrelated companies, some noise entities may slip through the validator.

**Local model speed.** Full pipeline on Ollama with a 3-4B parameter model takes 3-6 minutes. Groq reduces this to under 15 seconds.

**Attribute completeness varies.** If a page doesn't mention a company's founding year, that cell will be empty. The aggregator merges across sources, so entities found on multiple pages tend to have more complete data.

**Free tier cold starts.** The Render free tier sleeps after 15 minutes of inactivity. First request after sleep takes ~30 seconds. Use UptimeRobot to keep it warm.

---

## Deployment on Render (Free)

### Prerequisites

- GitHub repo pushed and set to **Public**
- [Render account](https://render.com) connected to GitHub
- Groq API key
- Tavily API key

### Steps

**1. Push your repo**
```bash
git push origin main
```

**2. Create Web Service on Render**
- New → Web Service → Connect repo
- Render auto-detects `render.yaml`

**3. Set secret env vars in Render dashboard**

Environment tab → add:
| Key | Value |
|---|---|
| `GROQ_API_KEY` | `gsk_...` |
| `TAVILY_API_KEY` | `tvly-...` |

**4. Deploy**

Click Create Web Service. First deploy takes 3-5 minutes.

**5. Keep it warm (prevents cold starts)**
- [UptimeRobot](https://uptimerobot.com) → New Monitor → HTTP(S)
- URL: `https://your-app.onrender.com/health`
- Interval: 5 minutes

### Auto-deploy on push

Every `git push origin main` triggers a Render redeploy automatically.

If you changed frontend files (`src/`, `index.html`, `package.json`, `vite.config.js`), the GitHub Action rebuilds `frontend/dist/` first, commits it, then Render picks up the commit.

### Render environment variables reference

```bash
# Set in dashboard (secrets — never in render.yaml)
GROQ_API_KEY=gsk_...
TAVILY_API_KEY=tvly-...

# Already in render.yaml
ENVIRONMENT=production
FORCE_HTTPS=true
LLM_PROVIDER=groq
SEARCH_PROVIDER=tavily
GROQ_MODEL=llama-3.3-70b-versatile
LOG_LEVEL=WARNING
```

---

## Adding a New Provider

### LLM provider

1. Create `providers/llm/yourprovider.py` — implement `BaseLLMProvider`
2. Do not raise in `__init__` on empty keys — raise in `complete()` instead
3. Register in `providers/factory.py` in `_build_llm()`
4. Add config fields to `config.py`
5. Document in this README

### Search provider

1. Create `providers/search/yourprovider.py` — implement `BaseSearchProvider`
2. Do not raise in `__init__` on empty keys — raise in `search()` instead
3. Register in `providers/factory.py` in `get_search_provider()`
4. Add config fields to `config.py`

---

## Submission

Built for the CIIR Agentic Search Challenge.

GitHub: https://github.com/vpk-11/narada
Live demo: https://narada-heij.onrender.com