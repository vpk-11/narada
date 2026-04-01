import { useState } from 'react'
import Sidebar, { DEFAULT_CONFIG } from './components/Sidebar.jsx'
import ResultsTable from './components/ResultsTable.jsx'
import { useSession } from './hooks/useSession.js'

const API_BASE = import.meta.env.VITE_API_URL || ''

function buildHeaders(config) {
  const h = { 'Content-Type': 'application/json' }
  if (config.groq_api_key) h['x-groq-api-key'] = config.groq_api_key
  if (config.openai_api_key) h['x-openai-api-key'] = config.openai_api_key
  if (config.anthropic_api_key) h['x-anthropic-api-key'] = config.anthropic_api_key
  if (config.tavily_api_key) h['x-tavily-api-key'] = config.tavily_api_key
  if (config.brave_api_key) h['x-brave-api-key'] = config.brave_api_key
  if (config.ollama_base_url) h['x-ollama-base-url'] = config.ollama_base_url
  if (config.search_provider) h['x-search-provider'] = config.search_provider
  if (config.query_analyzer?.provider) h['x-query-analyzer-provider'] = config.query_analyzer.provider
  if (config.query_analyzer?.model) h['x-query-analyzer-model'] = config.query_analyzer.model
  if (config.extractor?.provider) h['x-extractor-provider'] = config.extractor.provider
  if (config.extractor?.model) h['x-extractor-model'] = config.extractor.model
  if (config.validator?.provider) h['x-validator-provider'] = config.validator.provider
  if (config.validator?.model) h['x-validator-model'] = config.validator.model
  return h
}

const STEPS = [
  'Analyzing query',
  'Searching the web',
  'Scraping pages',
  'Extracting entities',
  'Validating results',
]

export default function App() {
  const [config] = useSession('narada_config', DEFAULT_CONFIG)
  const [query, setQuery]   = useState('')
  const [loading, setLoading] = useState(false)
  const [stepIdx, setStepIdx] = useState(0)
  const [result, setResult]   = useState(null)
  const [error, setError]     = useState(null)
  const [meta, setMeta]       = useState(null)

  async function run(refresh = false) {
    const q = query.trim()
    if (!q || loading) return

    setLoading(true)
    setError(null)
    setResult(null)
    setMeta(null)
    setStepIdx(0)

    const iv = setInterval(() => setStepIdx(i => Math.min(i + 1, STEPS.length - 1)), 3500)

    try {
      const res = await fetch(`${API_BASE}/api/search`, {
        method: 'POST',
        headers: buildHeaders(config),
        body: JSON.stringify({ query: q, refresh }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
      setResult(data.result)
      setMeta(data.result.metadata)
    } catch (e) {
      // Parse the error message — 400s from the server are user-facing config errors
      const msg = e.message || 'Unknown error'
      if (msg.includes('API key') || msg.includes('api key')) {
        setError(msg + ' — open Settings in the sidebar to add your keys.')
      } else {
        setError(msg)
      }
    } finally {
      clearInterval(iv)
      setLoading(false)
    }
  }

  return (
    <div className="layout">
      <Sidebar />

      <main className="main">
        {/* Header */}
        <div className="search-header">
          <div className="breadcrumb">Narada / Search</div>
          <h1 className="page-title">What are you researching?</h1>
          <div className="search-row">
            <div className="search-wrap">
              <svg className="search-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                <circle cx="7" cy="7" r="4.5"/><path d="m10.5 10.5 2.5 2.5"/>
              </svg>
              <input
                className="search-input"
                type="text"
                placeholder='"AI startups in healthcare" or "top pizza places in Brooklyn"'
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && run(false)}
                disabled={loading}
              />
            </div>
            <button className="btn btn-primary" onClick={() => run(false)} disabled={loading || !query.trim()}>
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6">
                <circle cx="7" cy="7" r="4.5"/><path d="m10.5 10.5 2.5 2.5"/>
              </svg>
              {loading ? 'Searching…' : 'Search'}
            </button>
            {result && !loading && (
              <button className="btn btn-ghost" onClick={() => run(true)}>
                Refresh
              </button>
            )}
          </div>
        </div>

        {/* Results */}
        <div className="results-area">

          {loading && (
            <div className="loading-wrap">
              <div className="progress-track"><div className="progress-bar" /></div>
              <div className="step-list">
                {STEPS.map((s, i) => (
                  <div key={s} className={`step-item${i < stepIdx ? ' done' : i === stepIdx ? ' live' : ''}`}>
                    <div className={`step-pip${i < stepIdx ? ' done' : i === stepIdx ? ' live' : ''}`}>
                      {i < stepIdx ? '✓' : i + 1}
                    </div>
                    {s}
                  </div>
                ))}
              </div>
            </div>
          )}

          {error && (
            <div className="error-wrap">
              <div className="error-ico">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <circle cx="8" cy="8" r="6.5"/><path d="M8 5v3.5M8 11h.01"/>
                </svg>
              </div>
              <div>
                <div className="error-title">Pipeline error</div>
                <div className="error-msg">{error}</div>
              </div>
            </div>
          )}

          {result && meta && !loading && (
            <>
              <div className="meta-bar">
                <span className="tag tag-green">{result.entities.length} entities</span>
                <span className="tag tag-accent">{result.entity_type}</span>
                <span className="meta-sep">·</span>
                <span className="tag tag-neutral">{meta.pages_scraped} pages</span>
                <span className="tag tag-neutral">{meta.duration_seconds}s</span>
                <span className="meta-push" />
                <span className="meta-model">{meta.llm_provider} / {meta.llm_model}</span>
              </div>

              {result.entities.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">
                    <svg width="22" height="22" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3">
                      <circle cx="7" cy="7" r="4.5"/><path d="m10.5 10.5 2.5 2.5"/>
                    </svg>
                  </div>
                  <div className="empty-title">No entities found</div>
                  <div className="empty-desc">Try a more specific query or click Refresh.</div>
                </div>
              ) : (
                <ResultsTable result={result} />
              )}
            </>
          )}

          {!loading && !result && !error && (
            <div className="empty-state">
              <div className="empty-icon">
                <svg width="22" height="22" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3">
                  <circle cx="7" cy="7" r="4.5"/><path d="m10.5 10.5 2.5 2.5"/>
                </svg>
              </div>
              <div className="empty-title">Ready to search</div>
              <div className="empty-desc">
                Configure your API keys in the sidebar, then enter a topic above.
                Every result cell links to its source.
              </div>
            </div>
          )}

        </div>
      </main>
    </div>
  )
}