# Narada

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

The pipeline runs 7 steps:

```
Query
  1. Query Analyzer    LLM determines entity type, dynamic column schema, targeted search queries
  2. Search            Runs 2-3 search queries, deduplicates URLs
  3. Scraper           Fetches and cleans all pages concurrently (async)
  4. Extractor         LLM reads each page, pulls structured entity data (sequential)
  5. Aggregator        Deduplicates entities, merges attributes across sources
  6. Validator         LLM filters out noise entities that do not match the query
  7. Cache             Writes result to disk (local dev only)
```

**What makes this different from just asking an LLM:**
- Schema is dynamic per query. "AI startups" gets different columns than "pizza places"
- Entities found across multiple sources get merged into one row
- Every cell value carries a `source_url`. Full traceability at the cell level
- Post-extraction validation filters noise (investors, legacy companies, off-topic entities)
- Per-step LLM configuration - each pipeline step can use a different model

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
Step 1 (Query Analyzer)  QUERY_ANALYZER_LLM_PROVIDER  falls back to  LLM_PROVIDER
Step 4 (Extractor)       EXTRACTION_LLM_PROVIDER       falls back to  LLM_PROVIDER
Step 6 (Validator)       VALIDATOR_LLM_PROVIDER         falls back to  LLM_PROVIDER
```

Per-step model overrides work for all providers (Groq, OpenAI, Anthropic, Ollama). If you assign a different model to each step, each step receives its own model name independently - they do not interfere.

The sidebar's **Per Step** mode configures this at runtime by sending separate `x-query-analyzer-model`, `x-extractor-model`, and `x-validator-model` headers.

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
│   ├── pipeline.py                Orchestrates all steps
│   └── cache.py                   Disk cache (.cache/)
│
├── providers/
│   ├── base.py                    Abstract contracts
│   ├── factory.py                 Per-step provider resolution (all 4 providers)
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
├── api/routes.py                  REST API (search, cache, providers, server-config)
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

```bash
# Provider selection
LLM_PROVIDER=groq             # ollama | groq | openai | anthropic
SEARCH_PROVIDER=tavily        # tavily | brave | duckduckgo

# Per-step LLM overrides (empty = use LLM_PROVIDER for that step)
QUERY_ANALYZER_LLM_PROVIDER=
EXTRACTION_LLM_PROVIDER=
VALIDATOR_LLM_PROVIDER=

# Ollama (local dev only)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:4b
QUERY_ANALYZER_OLLAMA_MODEL=
EXTRACTION_OLLAMA_MODEL=
VALIDATOR_OLLAMA_MODEL=

# Groq - free: 14,400 requests/day
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile

# OpenAI (optional)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Anthropic (optional)
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-haiku-4-5-20251001

# Tavily - free: 1000 searches/month
TAVILY_API_KEY=tvly-...

# Brave (optional)
BRAVE_API_KEY=BSA_...

# Fallback - allow frontend to use server Groq+Tavily keys when user has none
# Only relevant for production. Set to true in Render dashboard to enable.
FALLBACK_ALLOW=false

# Pipeline tuning
SEARCH_RESULTS_PER_QUERY=8
MAX_PAGES_TO_SCRAPE=6
SCRAPE_TIMEOUT_SECONDS=10

# Logging
LOG_LEVEL=INFO
```

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
x-query-analyzer-provider: groq
x-query-analyzer-model: llama-3.3-70b-versatile
x-extractor-provider: groq
x-extractor-model: llama-3.3-70b-versatile
x-validator-provider: groq
x-validator-model: llama-3.3-70b-versatile
```

Omitting a header means the server uses its configured `.env` default for that setting.

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

---

## Known Limitations

**Extraction quality depends on source pages.** Generic listicles that mention many unrelated entities may let some noise through the validator.

**Local model speed.** Full pipeline on Ollama with a 3-4B model takes 3-6 minutes. Groq reduces this to under 15 seconds.

**Attribute completeness varies.** If a page does not mention a founding year, that cell will be empty. The aggregator merges across sources, so entities found on multiple pages tend to have more complete data.

**Free tier cold starts.** The Render free tier sleeps after 15 minutes of inactivity. First request after sleep takes about 30 seconds. UptimeRobot keeps it warm.

**Per-step model isolation.** When using Per Step mode with different providers across steps, the model name for each step is tracked independently. When using the same provider across multiple steps, each step still receives its own model override and they do not interfere.

---

## Adding a New Provider

### LLM provider

1. Create `providers/llm/yourprovider.py` - implement `BaseLLMProvider`
2. Do not raise in `__init__` on empty keys - raise in `complete()` instead
3. Register in `providers/factory.py` in `_build_llm()` and `_get_step_model_override()`
4. Add config fields to `config.py` (api_key, model, and per-step model overrides)
5. Add the provider name to `NEEDS_KEY` in `frontend/src/App.jsx`

### Search provider

1. Create `providers/search/yourprovider.py` - implement `BaseSearchProvider`
2. Do not raise in `__init__` on empty keys - raise in `search()` instead
3. Register in `providers/factory.py` in `get_search_provider()`
4. Add config fields to `config.py`

---

GitHub: https://github.com/vpk-11/narada
Live demo: https://narada-heij.onrender.com
