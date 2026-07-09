# Narada

<!-- version: v1.2.0 -->
![Version](https://img.shields.io/badge/version-v1.2.0-blue)

You type a research question. Narada searches the web, reads the relevant pages, and hands you back a structured table with every cell linked to the exact URL it came from.

No copy-pasting across tabs. No manual summarising. Just ask, and get a sourced, structured answer.

**Example:** `"AI startups in healthcare"` returns a table of companies with columns like `founded`, `funding_raised`, `headquarters`, `what_they_do` - each value traced back to its source page.

Named after the Hindu divine sage Narada: the first journalist, who traveled all three worlds gathering and delivering structured knowledge.

**Live demo:** https://narada-heij.onrender.com

---

## Using the App

### What you need

Narada needs two things to run: an **LLM** (reads pages and extracts structured data) and a **search provider** (finds the relevant URLs). You bring your own keys. They are stored only in your browser tab and never sent to or stored on the server.

**LLM providers:**

| Provider | Notes | Sign up |
|---|---|---|
| **Groq** | Recommended. Fast, free tier: 14,400 requests/day | [console.groq.com](https://console.groq.com) |
| **OpenAI** | GPT models. Paid. | [platform.openai.com](https://platform.openai.com) |
| **Anthropic** | Claude models. Paid. | [console.anthropic.com](https://console.anthropic.com) |
| **Ollama** | Run models locally. No API key needed. Local dev only. | [ollama.com](https://ollama.com) |

**Search providers:**

| Provider | Notes | Sign up |
|---|---|---|
| **Tavily** | Recommended. Built for AI agents. Free tier: 1,000 searches/month | [tavily.com](https://tavily.com) |
| **Brave Search** | Privacy-focused. Paid API. Free tier: 2,000 queries/month | [brave.com/search/api](https://brave.com/search/api) |
| **DuckDuckGo** | Free, no key needed. Less reliable for structured research. | - |

**Just want to try it?** Sign up for Groq and Tavily. Both are free and take under a minute.

---

### Step 1 - Get your API keys

Go to [console.groq.com](https://console.groq.com) and grab a free API key. Do the same at [tavily.com](https://tavily.com).

### Step 2 - Configure the sidebar

Open the app. On the left is the settings sidebar. Here is what to fill in.

**Search Provider section:**
- Choose your search provider (Tavily, Brave, or DuckDuckGo)
- If the provider needs a key (Tavily or Brave), paste it into the field below the dropdown
- DuckDuckGo requires no key

**LLM API Keys section:**
- Paste your key into the matching field (e.g. Groq field for a `gsk_...` key)
- Ollama URL is shown only in local dev mode
- You can leave a field empty if you want the server to use its own configured key for that provider

**Pipeline LLM section:**

Choose which AI model powers the pipeline. There are two modes:

- **Unified** - one provider and model handles all three pipeline steps (Query Analyzer, Extractor, Validator). This is the simplest setup and works well for most queries.
- **Per Step** - assign a different provider and model to each pipeline step. Useful when you want a lightweight model for query analysis and a larger, more capable model for extraction.

Recommended model names:

| Provider | Model |
|---|---|
| Groq | `llama-3.3-70b-versatile` |
| OpenAI | `gpt-4o-mini` |
| Anthropic | `claude-haiku-4-5-20251001` |
| Ollama | whatever model you have pulled (e.g. `qwen3:4b`) |

> Keys are stored in `sessionStorage` only. They disappear when you close the tab and are never sent to or stored on the server.

### Step 3 - Run a query

Type what you want to research into the search bar and press **Enter**. Think of it as asking: *"give me a table of X"*.

Good queries describe a **category of things** rather than a single item:

```
AI startups in healthcare
top pizza places in Brooklyn
electric vehicle companies in Europe
Formula 1 drivers in the 2024 season
venture capital firms in Southeast Asia
```

The pipeline takes about 15-20 seconds on Groq. A live step tracker shows progress.

### Reading the results

- Each **row** is one entity (a company, a person, a place, etc.)
- Click **+** on any row to expand it and see every attribute with its source link
- Each value card shows a **source chip** - click it to open the exact page the value came from
- Click **Refresh** to bypass the cache and run a fresh search

### Tips

- **More specific = better results.** `"Series A AI startups in healthcare founded after 2020"` gives tighter results than just `"AI startups"`.
- **If results look thin**, try Refresh. The web search may return different pages the second time.
- **Ollama is slower** - expect 3-6 minutes with a small local model like `qwen3:4b`. Groq is under 20 seconds.

---

## Local vs Production Behaviour

The app detects whether it is running on `localhost` and adjusts automatically.

### Local dev mode

- Ollama appears as a provider option
- A **Cache** toggle is shown in the sidebar. When enabled, identical queries return instantly from disk. When off, every search runs fresh.
- If a key field is empty, the pipeline runs anyway. The server uses its own `.env` key for that provider as a silent fallback. If the server also has no key, you get a provider error in the UI.

### Production mode

- Ollama is hidden (a remote server cannot reach your local Ollama)
- Cache is always bypassed. Every search runs fresh.
- If a key field is empty, a popup appears before the request is made:
  - It tells you which provider's key is missing
  - It offers a **Dismiss** option to go add the key in the sidebar
  - If the server has `FALLBACK_ALLOW=true` configured, a second option appears: **Use Groq + Tavily (server keys)**. This runs the pipeline using the server's own Groq and Tavily keys for that one request only. Your stored sidebar config is not changed.

### Dev sim-prod toggle (local only)

At the bottom of the sidebar, a **Dev Tools** section lets you flip a **Simulate production** toggle. When on:

- The badge in the logo area changes from `DEV` to `SIM PROD`
- Ollama is hidden and cache is suppressed, exactly as in production
- The production key-error popup fires if you run without sidebar keys - so you can test the full fallback flow locally without deploying

---

## Key Fallback Behaviour

The server has its own API keys configured in `.env` (or Render dashboard secrets). These are used when a user does not supply their own key.

| Environment | Sidebar has key | Behaviour |
|---|---|---|
| Local | Yes | Uses your key |
| Local | No | Runs silently with server key; error if server also has none |
| Production | Yes | Uses your key |
| Production | No | Shows key-error popup before running |
| Production (FALLBACK_ALLOW=true) | No | Popup offers to run with server Groq + Tavily keys |

---

## How It Works

The pipeline runs 7 steps, plus a conditional gap-filling loop:

```
Query
  1. Query Analyzer    LLM determines entity type, dynamic column schema, targeted search queries
  2. Search            Runs 2-3 search queries, deduplicates URLs (auto-fallback to DuckDuckGo on provider failure)
  3. Scraper           Fetches and cleans all pages concurrently (async)
  4. Extractor         LLM reads each page in chunks, pulls structured entity data (sequential)
  5. Aggregator        Deduplicates entities (fuzzy name match), merges attributes by confidence
  6. Validator         LLM filters out noise entities that do not match the query
  7. Gap-fill (0-2x)   If too many cells are empty, generates follow-up searches and re-runs 2-4
  8. Cache             Writes result to disk (local dev only)
```

**What makes this different from just asking an LLM:**
- Schema is dynamic per query. "AI startups" gets different columns than "pizza places"
- The pipeline checks its own output and re-searches to fill gaps, capped at a couple of rounds
- Entities found across multiple sources get merged into one row, fuzzy-matched on name
- Every cell value carries a `source_url`, `source_quote`, and `confidence` score - full traceability, not just a link
- Post-extraction validation filters noise (investors, legacy companies, off-topic entities)
- Per-step LLM configuration - each pipeline step can use a different model

---

## Architecture

### Provider Pattern

Every LLM and search dependency sits behind an abstract interface. The pipeline never imports a concrete provider directly. Swapping providers means changing one line in `.env`.

LLM routing goes through a single `LiteLLMProvider` that supports any LiteLLM-compatible backend. The model string prefix determines which API key and base URL are used.

```
BaseLLMProvider             BaseSearchProvider
    LiteLLMProvider             tavily
      groq/...                  brave
      openai/...                duckduckgo
      anthropic/...
      ollama/...
```

### Per-Step LLM Configuration

Each pipeline step can use a different model. All steps fall back to `LLM_MODEL` if not explicitly configured.

```
Step 1 (Query Analyzer)  QUERY_ANALYZER_MODEL  falls back to  LLM_MODEL
Step 4 (Extractor)       EXTRACTION_MODEL       falls back to  LLM_MODEL
Step 6 (Validator)       VALIDATOR_MODEL        falls back to  LLM_MODEL
```

Per-step overrides use the same `provider/model-name` format. Assign a lightweight model for query analysis and a larger one for extraction if needed.

The sidebar's **Per Step** mode configures this at runtime by sending separate `x-query-analyzer-model`, `x-extractor-model`, and `x-validator-model` headers, each carrying a full LiteLLM model string.

### Agentic Gap-Filling

After validation, `core/agentic_loop.py` computes a **gap ratio**: the
fraction of (entity, attribute) cells with no value at all. If it exceeds
`AGENT_GAP_THRESHOLD` (default 0.5), the pipeline:

1. Identifies the 5 entities with the most missing attributes
2. Asks the LLM to generate 1-3 targeted follow-up search queries for those gaps
3. Searches, scrapes, and extracts from new pages only (URLs already visited are skipped)
4. Merges the new entities back in via the same fuzzy aggregator

This repeats until the gap ratio recovers, a round finds no new pages, or
`AGENT_MAX_ITERATIONS` (default 2) is hit. Gap-query generation fails closed
— if the LLM call errors, the loop just stops rather than crashing the run.
`PipelineMetadata.search_iterations` and `.gap_ratio` report how many rounds
ran and how complete the final table is.

### Chunked Extraction

Pages are split into chunks (`core/chunking.py`) instead of truncated. Text
is split on paragraph boundaries first; a paragraph that itself exceeds the
chunk size falls back to sentence-boundary splitting. Each chunk after the
first carries a trailing overlap from the previous one, so a fact split
across a chunk boundary isn't lost to either side. Capped at 3 chunks per
page to bound LLM calls on long pages.

### Fuzzy Matching and Confidence Resolution

`agents/aggregator.py` merges entities whose normalized names match exactly
or score above a similarity threshold (0.75, via stdlib `difflib`) — this
catches punctuation/suffix drift across sources ("Abridge, Inc." vs
"Abridge Inc") that exact matching misses. When two sources provide the same
attribute for the same entity, the merge prefers the non-empty value, then
the one with higher extraction `confidence`. Equal confidence keeps the
existing value.

### JSON Repair

Every LLM-calling agent asks for JSON-only output, but models still
occasionally wrap it in markdown fences or prepend a stray sentence despite
the instruction. `core/llm_json.py` centralizes cleanup (strip `<think>`
blocks and code fences) plus a bracket-slice recovery pass that finds the
first `{`/`[` and matching last `}`/`]` and retries parsing on that slice —
shared across the query analyzer, extractor, and validator instead of each
agent hand-rolling its own parser.

### Automatic Search Failover

If the configured search provider fails on a query (bad key, outage, rate
limit), `core/pipeline.py`'s `_run_searches` falls back to DuckDuckGo for
that query rather than aborting the whole run. DuckDuckGo needs no API key,
so it's always available as a last resort. Not triggered if DuckDuckGo is
already the configured provider.

### JSON-LD Pre-Extraction

Many business/product pages already embed clean structured data for Google's
search snippets (a `<script type="application/ld+json">` block with the
company name, founding date, address, etc.). `core/json_ld.py` parses these
blocks and maps fields onto whichever requested attribute names look like
they're asking for the same fact (e.g. `foundingDate` → an attribute named
`founded` or `established`). Cells built this way get `confidence=1.0` since
it's structured data the page author published, not an LLM inference — they
win merge conflicts against an LLM-extracted value for the same attribute.
This runs before the chunked LLM extraction on every page, not instead of
it: pages with no JSON-LD, or JSON-LD missing the requested attributes,
still go through the normal LLM path.

### Retry with Backoff on Transient LLM Errors

`providers/llm/litellm_provider.py` retries rate limits, timeouts, and
provider-side outages (`RateLimitError`, `Timeout`, `APIConnectionError`,
`ServiceUnavailableError`, `InternalServerError`) up to 3 times with
exponential backoff capped at 10s. Auth and bad-request errors are not
retried — retrying a 401 five times just delays the same failure.

### API Key Security

Keys are sent from the browser as custom request headers (`x-groq-api-key`, `x-tavily-api-key`, etc.) rather than in the request body. Headers are excluded from server access logs by default.

- Stored in browser `sessionStorage` - cleared when the tab closes
- Used per-request and never stored server-side
- Error logs emit `type(e).__name__` only - key material never appears in logs
- CSP headers prevent XSS from reading sessionStorage
- HTTPS enforced in production

### Error Handling

The API returns descriptive errors for common failure modes:

| Scenario | HTTP | Message |
|---|---|---|
| Missing API key | 400 | Provider-specific message (e.g. "Groq API key is missing...") |
| Invalid/expired key | 502 | "API key rejected (401 Unauthorized)..." |
| Rate limit hit | 502 | "Rate limit reached (429)..." |
| Provider server error | 502 | "The provider's server returned an error..." |
| Connection failure | 502 | "Could not connect to the provider..." |
| Request timeout | 504 | "Request timed out while contacting the provider..." |

### Project Structure

```
narada/
├── main.py                        FastAPI entry - serves React build in production
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
│   ├── pipeline.py                Orchestrates all steps + gap-fill loop
│   ├── agentic_loop.py            Gap-ratio computation, follow-up search + merge
│   ├── chunking.py                Paragraph/sentence-boundary chunking with overlap
│   ├── llm_json.py                Shared JSON parsing + repair for LLM output
│   ├── json_ld.py                 schema.org JSON-LD pre-extraction before LLM
│   └── cache.py                   Disk cache (.cache/)
│
├── providers/
│   ├── base.py                    Abstract contracts
│   ├── factory.py                 Per-step provider resolution
│   ├── llm/litellm_provider.py    Single LLM provider (wraps LiteLLM)
│   └── search/                    tavily, brave, duckduckgo
│
├── agents/
│   ├── query_analyzer.py          Step 1
│   ├── scraper.py                 Step 3
│   ├── extractor.py               Step 4 - chunked, confidence-scored
│   ├── aggregator.py              Step 5 - fuzzy match, confidence-based merge
│   └── validator.py               Step 6
│
├── api/routes.py                  REST API (search, cache, providers, server-config)
│
├── tests/                         pytest - aggregator, chunking, extractor, validator, gap-fill
│
└── frontend/
    └── src/
        ├── App.jsx                Search UI, key guard, fallback popup
        ├── components/
        │   ├── Sidebar.jsx        Settings, key config, unified/per-step toggle
        │   └── ResultsTable.jsx   Expandable rows with source chips
        ├── hooks/useSession.js    sessionStorage-backed state with default merging
        └── styles/main.css
```

---

## Setup

### Prerequisites

- [Anaconda](https://www.anaconda.com) or Miniconda
- [Ollama](https://ollama.com) - optional, only if using local models
- A Groq API key - free at [console.groq.com](https://console.groq.com)
- A Tavily API key - free at [tavily.com](https://tavily.com)

### 1. Create the Conda environment

```bash
conda env create -f environment.yml
conda activate narada
```

### 2. Configure environment variables

Create a `.env` file in the project root:

```bash
cp .env.example .env   # or create manually - see Environment Variables section below
```

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
pnpm install
pnpm dev
# Opens at http://localhost:5173
```

### 6. Open Swagger docs

```
http://localhost:8000/docs
```

### 7. Run tests

```bash
pip install -r requirements-dev.txt
pytest
```

---

## Environment Variables

Model strings use LiteLLM format: `provider/model-name` (e.g. `groq/llama-3.3-70b-versatile`).

```bash
# LLM - full LiteLLM model string
LLM_MODEL=groq/llama-3.3-70b-versatile

# Search provider
SEARCH_PROVIDER=tavily        # tavily | brave | duckduckgo

# Per-step LLM overrides (empty = fall back to LLM_MODEL for that step)
QUERY_ANALYZER_MODEL=
EXTRACTION_MODEL=
VALIDATOR_MODEL=

# Ollama (local dev only)
OLLAMA_BASE_URL=http://localhost:11434

# API Keys
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
BRAVE_API_KEY=BSA_...

# Fallback - allow frontend to use server Groq+Tavily keys when user has none
# Only relevant for production. Set to true in Render dashboard to enable.
FALLBACK_ALLOW=false

# Cache admin key (optional) - when set, DELETE /api/cache requires x-admin-key header
CACHE_ADMIN_KEY=

# Pipeline tuning
SEARCH_RESULTS_PER_QUERY=8
MAX_PAGES_TO_SCRAPE=6
SCRAPE_TIMEOUT_SECONDS=10
MAX_CONCURRENT_PIPELINE_RUNS=5   # server-wide cap on simultaneous pipeline runs

# Agentic gap-filling - re-search when too many cells are empty after validation
AGENT_GAP_THRESHOLD=0.5      # 0.0-1.0, fraction of empty cells that triggers a re-search round
AGENT_MAX_ITERATIONS=2       # hard cap on gap-fill rounds, 1 = disabled

# Logging
LOG_LEVEL=INFO
```

LiteLLM model string examples:
- `groq/llama-3.3-70b-versatile`
- `openai/gpt-4o-mini`
- `anthropic/claude-haiku-4-5-20251001`
- `ollama/qwen3:4b`

---

## API Reference

Full interactive docs at `http://localhost:8000/docs` (local only).

### POST /api/search

Run the pipeline for a query.

**Request body:**
```json
{
  "query": "AI startups in healthcare",
  "refresh": false
}
```

**Request headers (all optional - override .env for this request only):**
```
x-groq-api-key: gsk_...
x-openai-api-key: sk-...
x-anthropic-api-key: sk-ant-...
x-tavily-api-key: tvly-...
x-brave-api-key: BSA_...
x-ollama-base-url: http://localhost:11434
x-search-provider: tavily
x-query-analyzer-model: groq/llama-3.3-70b-versatile
x-extractor-model: groq/llama-3.3-70b-versatile
x-validator-model: groq/llama-3.3-70b-versatile
```

Model headers carry a full LiteLLM model string (`provider/model-name`). Omitting a header means the server uses its configured `.env` default for that setting.

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
            "source_url": "https://techcrunch.com/...",
            "source_quote": "Abridge was founded in 2018 by Shiv Rao",
            "confidence": 0.95
          },
          "funding_raised": {
            "value": "$250 million",
            "source_url": "https://fiercehealthcare.com/...",
            "source_quote": "raised a $250 million Series D",
            "confidence": 0.9
          }
        }
      }
    ],
    "metadata": {
      "search_provider": "tavily",
      "llm_provider": "groq",
      "llm_model": "llama-3.3-70b-versatile",
      "pages_scraped": 5,
      "duration_seconds": 13.6,
      "search_iterations": 1,
      "gap_ratio": 0.12
    },
    "errors": []
  }
}
```

`search_iterations` is 1 unless the gap-filling loop ran (see [Agentic Gap-Filling](#agentic-gap-filling)). `errors` lists non-fatal issues encountered during the run (e.g. a search-provider fallback) — a run with errors can still return usable results.

### DELETE /api/cache

Clear all cached pipeline results from disk.

### GET /api/providers

Returns the active provider and model for each pipeline step based on current server config.

### GET /api/server-config

Returns public server flags. Currently exposes only `fallback_allow`.

```json
{ "fallback_allow": false }
```

### GET /health

Liveness check. Returns environment and default provider info.

---

## Deployment on Render (Free)

### Prerequisites

- GitHub repo (public)
- [Render account](https://render.com) connected to GitHub
- Groq API key
- Tavily API key

### Steps

**1. Push your repo**

```bash
git push origin main
```

**2. Create Web Service on Render**

- New -> Web Service -> Connect repo
- Render auto-detects `render.yaml`

**3. Set secret env vars in Render dashboard**

Go to your service -> Environment tab:

| Key | Required | Notes |
|---|---|---|
| `GROQ_API_KEY` | Yes | Server-side LLM key (default provider) |
| `TAVILY_API_KEY` | Yes | Server-side search key (default provider) |
| `OPENAI_API_KEY` | No | Optional fallback for users selecting OpenAI |
| `ANTHROPIC_API_KEY` | No | Optional fallback for users selecting Anthropic |
| `BRAVE_API_KEY` | No | Optional fallback for users selecting Brave Search |
| `FALLBACK_ALLOW` | No | Set `true` to enable the "Use server keys" button for users with no key |

These are the server-side keys used when users run without entering their own in the sidebar.

**4. Deploy**

Click Create Web Service. First deploy takes 3-5 minutes.

**5. Keep it warm (prevents cold starts on free tier)**

- [UptimeRobot](https://uptimerobot.com) -> New Monitor -> HTTP(S)
- URL: `https://your-app.onrender.com/health`
- Interval: 5 minutes

### Auto-deploy

Every `git push origin main` triggers a Render redeploy. If you changed frontend files (`src/`, `index.html`, `package.json`, `vite.config.js`), the GitHub Action rebuilds `frontend/dist/` first, commits it with `[skip ci]`, then Render picks up the commit.

---

## Design Decisions

**Dynamic schema per query.** The query analyzer asks the LLM to determine what columns make sense before anything is searched. "AI startups" gets `founded, funding_raised, headquarters`. "Pizza places" gets `neighborhood, price_range, specialty`. The schema is not hardcoded.

**Source traceability at the cell level.** Every attribute value is a `CellValue(value, source_url)`. It is impossible to store a value without a source - enforced by the data model.

**Primary-subject extraction rule.** The extractor only pulls entities that are the main focus of a page. A page about Abridge that mentions Epic Systems yields only Abridge. This eliminates a large class of noise. Investors, partners, media outlets, and competitors are excluded by the system prompt.

**Per-step LLM configuration.** Query analysis is a short reasoning task - a lightweight model handles it fine. Extraction reads dense content and benefits from a larger model. Per-step configuration lets each stage use the best model for its job. Model overrides are fully independent per step and per provider.

**Provider pattern.** No agent or pipeline code imports a concrete LLM or search implementation. Everything goes through abstract interfaces. Adding a new provider means implementing one class and registering it in `factory.py`.

**Pre-flight key guard.** Before making a search request, the frontend checks whether the selected provider's key exists in the sidebar. If not, and the app is running in production mode, it shows a popup immediately rather than letting the request fail mid-pipeline. This prevents wasted pipeline runs and gives the user a clear, actionable message.

**Disk cache.** Results survive server restarts with no Redis dependency. Cache key is `SHA256(query + provider + model + search_provider)`. Cache is a toggleable option in local dev mode and always bypassed in production.

**Sequential extraction, concurrent scraping.** Scraping is I/O-bound - all pages fetch in parallel. Extraction is compute-bound and LLM-sequential - concurrent extraction calls against a local Ollama instance cause timeouts.

**Aggregation before validation.** Deduplication runs first (pure logic, no LLM cost), then one validation call sees the full merged entity list. Cheaper than validating per-page and produces better results since the validator sees relative context.

**No server-side key storage.** The deployed app has no secrets of its own by default. Users supply their own keys. Optionally, server operators can configure fallback keys for users who do not have their own.

**Agentic gap-fill over a fixed pipeline.** A linear 7-step pipeline that never checks its own output quality isn't meaningfully different from asking an LLM once. Computing a gap ratio and re-searching for specific missing attributes is what makes the system reason about its output rather than just produce it - at the cost of up to 2x the search/scrape/extract work on sparse queries, which is why it's capped and only triggers above a threshold.

**Chunking over truncation.** A flat character cutoff silently drops whatever's past it - a founding date at character 4000 of a long article never reached the model. Paragraph/sentence-boundary chunking with overlap costs more LLM calls per long page, but recovers content that was previously just gone.

**Confidence as the merge tie-breaker, not length.** "Longer value wins" rewards verbose hallucination as much as correctness. Confidence is the model's own signal about a specific extraction, so using it to resolve conflicts is a more honest tie-breaker even though it depends on the model being reasonably calibrated.

**Fuzzy name matching via stdlib `difflib`, not a new dependency.** `SequenceMatcher` is slower than a C-optimized fuzzy-matching library at scale, but at the entity counts this pipeline produces (dozens, not thousands) the difference is not measurable, and it avoids adding a dependency for a problem the standard library already solves.

---

## Known Limitations

**Extraction quality depends on source pages.** Generic listicles that mention many unrelated entities may let some noise through the validator.

**Local model speed.** Full pipeline on Ollama with a 3-4B model takes 3-6 minutes. Groq reduces this to under 15 seconds.

**Attribute completeness varies.** If a page does not mention a founding year, that cell will be empty. The aggregator merges across sources, so entities found on multiple pages tend to have more complete data.

**Free tier cold starts.** The Render free tier sleeps after 15 minutes of inactivity. First request after sleep takes about 30 seconds. UptimeRobot keeps it warm.

**Per-step model isolation.** When using Per Step mode with different providers across steps, the model name for each step is tracked independently. When using the same provider across multiple steps, each step still receives its own model override and they do not interfere.

**Gap-fill adds latency on sparse queries.** A query that triggers the full 2-iteration gap-fill loop roughly doubles the search/scrape/extract work, and therefore the wall-clock time, of a query that doesn't. This is a deliberate completeness-vs-speed tradeoff, tunable via `AGENT_GAP_THRESHOLD` and `AGENT_MAX_ITERATIONS`.

**No anonymous free tier yet.** The live demo currently requires the visitor's own API keys (or `FALLBACK_ALLOW` for a single request). A rate-limited free tier using server keys is scoped in `TODO.md` but not implemented.

---

## Adding a New Provider

### LLM provider

LiteLLM supports hundreds of providers out of the box. Most require no code changes - just use the correct model string in `LLM_MODEL`:

```bash
LLM_MODEL=gemini/gemini-1.5-flash
LLM_MODEL=mistral/mistral-large-latest
LLM_MODEL=cohere/command-r
```

If the new provider needs its own API key field in `config.py`, add it there and wire it up in `providers/factory.py`'s `_build_llm()` prefix check. No new provider file needed.

### Search provider

1. Create `providers/search/yourprovider.py` - implement `BaseSearchProvider`
2. Do not raise in `__init__` on empty keys - raise in `search()` instead
3. Register in `providers/factory.py` in `get_search_provider()`
4. Add config fields to `config.py`

---

## Changelog
- **v1.2.0** (2026-07-08) — minor bump

- **v2.0.0** (2026-07-08) — Architecture rework: added an agentic gap-filling re-search loop, confidence-scored and quote-backed cell provenance, fuzzy entity matching, chunked (non-truncating) extraction, automatic search-provider failover, shared LLM JSON repair, partial-success error reporting, and a pytest suite.
- **v1.1.0** (2026-07-08) — Migrated all LLM providers to a single LiteLLM-backed provider (`provider/model-name` format), replacing separate per-provider client classes. Security hardening pass on error logging and CSP headers.
- **v1.0.0** (initial) — 7-step pipeline (query analyzer, search, scraper, extractor, aggregator, validator, cache), per-request API keys via headers, provider factory pattern, React frontend with sessionStorage key persistence.

---

GitHub: https://github.com/vpk-11/narada
Live demo: https://narada-heij.onrender.com
