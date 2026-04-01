import { useState } from 'react'
import Sidebar, { DEFAULT_CONFIG } from './components/Sidebar.jsx'
import ResultsTable from './components/ResultsTable.jsx'
import { useSession } from './hooks/useSession.js'

const API_BASE = import.meta.env.VITE_API_URL || ''

/**
 * Build request headers from the user's session config.
 *
 * Keys go into custom HTTP headers (x-groq-api-key etc), NOT the request body.
 * Headers are excluded from most server access logs by default.
 * Nothing is stored on the server -- keys are used per-request and discarded.
 */
function buildHeaders(config) {
  const headers = { 'Content-Type': 'application/json' }

  if (config.groq_api_key)       headers['x-groq-api-key']        = config.groq_api_key
  if (config.openai_api_key)     headers['x-openai-api-key']       = config.openai_api_key
  if (config.anthropic_api_key)  headers['x-anthropic-api-key']    = config.anthropic_api_key
  if (config.tavily_api_key)     headers['x-tavily-api-key']       = config.tavily_api_key
  if (config.brave_api_key)      headers['x-brave-api-key']        = config.brave_api_key
  if (config.ollama_base_url)    headers['x-ollama-base-url']      = config.ollama_base_url
  if (config.search_provider)    headers['x-search-provider']      = config.search_provider

  if (config.query_analyzer?.provider) headers['x-query-analyzer-provider'] = config.query_analyzer.provider
  if (config.query_analyzer?.model)    headers['x-query-analyzer-model']    = config.query_analyzer.model
  if (config.extractor?.provider)      headers['x-extractor-provider']      = config.extractor.provider
  if (config.extractor?.model)         headers['x-extractor-model']         = config.extractor.model
  if (config.validator?.provider)      headers['x-validator-provider']      = config.validator.provider
  if (config.validator?.model)         headers['x-validator-model']         = config.validator.model

  return headers
}

export default function App() {
  const [config] = useSession('narada_config', DEFAULT_CONFIG)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [meta, setMeta] = useState(null)

  async function handleSearch(refresh = false) {
    const q = query.trim()
    if (!q || loading) return

    setLoading(true)
    setError(null)
    setResult(null)
    setMeta(null)

    try {
      const res = await fetch(`${API_BASE}/api/search`, {
        method: 'POST',
        headers: buildHeaders(config),
        body: JSON.stringify({ query: q, refresh }),
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || `HTTP ${res.status}`)
      }

      setResult(data.result)
      setMeta(data.result.metadata)

    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter') handleSearch(false)
  }

  return (
    <div className="layout">
      <Sidebar />

      <main className="main">
        <div className="search-area">
          <h1 className="search-title">What are you researching?</h1>
          <p className="search-subtitle">
            Enter a topic. Narada searches the web, extracts structured data,
            and returns a traceable table. Every cell links to its source.
          </p>

          <div className="search-row">
            <input
              className="search-input"
              type="text"
              placeholder='"AI startups in healthcare" or "top pizza places in Brooklyn"'
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
            />
            <button
              className="btn btn-primary"
              onClick={() => handleSearch(false)}
              disabled={loading || !query.trim()}
            >
              {loading ? 'Searching...' : 'Search'}
            </button>
            {result && (
              <button
                className="btn btn-ghost"
                onClick={() => handleSearch(true)}
                disabled={loading}
                title="Bypass cache and run fresh"
              >
                Refresh
              </button>
            )}
          </div>
        </div>

        <div className="results-area">
          {loading && (
            <div>
              <div className="loading-bar">
                <div className="loading-bar-inner" />
              </div>
              <div style={{ color: 'var(--text-3)', fontSize: 13, textAlign: 'center' }}>
                Searching the web, extracting entities, validating results...
              </div>
            </div>
          )}

          {error && (
            <div className="error-box">
              <strong>Pipeline error</strong>
              {error}
            </div>
          )}

          {result && meta && !loading && (
            <>
              <div className="status-bar">
                <span className="pill pill-green">
                  {result.entities.length} entities
                </span>
                <span className="pill pill-amber">
                  {result.entity_type}
                </span>
                <span>{meta.pages_scraped} pages scraped</span>
                <span>{meta.duration_seconds}s</span>
                <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                  {meta.llm_provider} / {meta.llm_model}
                </span>
              </div>

              {result.entities.length === 0 ? (
                <div className="empty-state">
                  <span className="icon">∅</span>
                  <h3>No entities found</h3>
                  <p>
                    Try a more specific query or click Refresh to run with different sources.
                  </p>
                </div>
              ) : (
                <ResultsTable result={result} />
              )}
            </>
          )}

          {!loading && !result && !error && (
            <div className="empty-state">
              <span className="icon" style={{ opacity: 0.4 }}>
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="1.2">
                  <circle cx="11" cy="11" r="8"/>
                  <path d="m21 21-4.35-4.35"/>
                </svg>
              </span>
              <h3>Enter a query to begin</h3>
              <p>
                Configure your API keys in the sidebar, then search any topic.
                Results are cached — repeated queries return instantly.
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}