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
  const [showHelp, setShowHelp] = useState(false)

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
        {/* Help modal */}
        {showHelp && (
          <div className="help-overlay" onClick={() => setShowHelp(false)}>
            <div className="help-modal" onClick={e => e.stopPropagation()}>
              <div className="help-modal-header">
                <span className="help-modal-title">How to use Narada</span>
                <button className="help-close" onClick={() => setShowHelp(false)}>✕</button>
              </div>
              <div className="help-modal-body">
                <div className="help-step">
                  <div className="help-num">1</div>
                  <div>
                    <div className="help-step-title">Get free API keys</div>
                    <div className="help-step-desc">Narada needs an LLM and a search provider. Both have generous free tiers.</div>
                    <div className="help-key-links">
                      <a href="https://console.groq.com" target="_blank" rel="noreferrer">Groq <span>LLM · free</span></a>
                      <a href="https://tavily.com" target="_blank" rel="noreferrer">Tavily <span>Search · free</span></a>
                    </div>
                  </div>
                </div>
                <div className="help-step">
                  <div className="help-num">2</div>
                  <div>
                    <div className="help-step-title">Enter your keys in the sidebar</div>
                    <div className="help-step-desc">Paste your <strong>Groq key</strong> under LLM API Keys and your <strong>Tavily key</strong> under Search Provider. Keys live in sessionStorage only — cleared when you close the tab, never stored server-side.</div>
                  </div>
                </div>
                <div className="help-step">
                  <div className="help-num">3</div>
                  <div>
                    <div className="help-step-title">Type a query and press Enter</div>
                    <div className="help-step-desc">Describe what you want to research. Narada searches the web, scrapes relevant pages, and returns a structured table — every cell value linked to its source URL.</div>
                    <div className="help-examples">
                      <span>Try:</span>
                      <code>AI startups in healthcare</code>
                      <code>top pizza places in Brooklyn</code>
                      <code>electric vehicle companies in Europe</code>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Header */}
        <div className="search-header">
          <div className="search-header-top">
            <div className="breadcrumb">Narada / Search</div>
            <button className="help-btn" onClick={() => setShowHelp(true)} title="How to use">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8">
                <circle cx="8" cy="8" r="6.5"/>
                <path d="M6.2 6.2a2 2 0 1 1 2.4 2c-.4.2-.6.6-.6 1v.3M8 12.5h.01" strokeLinecap="round"/>
              </svg>
              Help
            </button>
          </div>
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
            <div className="getting-started">
              <div className="gs-title">Get started in 3 steps</div>
              <div className="gs-steps">
                <div className="gs-step">
                  <div className="gs-num">1</div>
                  <div className="gs-content">
                    <div className="gs-step-title">Get free API keys</div>
                    <div className="gs-step-desc">Narada needs an LLM and a search provider. Both have generous free tiers.</div>
                    <div className="gs-key-links">
                      <a href="https://console.groq.com" target="_blank" rel="noreferrer" className="gs-link">Groq <span>LLM · free</span></a>
                      <a href="https://tavily.com" target="_blank" rel="noreferrer" className="gs-link">Tavily <span>Search · free</span></a>
                    </div>
                  </div>
                </div>
                <div className="gs-step">
                  <div className="gs-num">2</div>
                  <div className="gs-content">
                    <div className="gs-step-title">Enter your keys in the sidebar</div>
                    <div className="gs-step-desc">Paste your <strong>Groq key</strong> under LLM API Keys and your <strong>Tavily key</strong> under Search Provider. Keys live in sessionStorage only — cleared when you close the tab, never stored server-side.</div>
                  </div>
                </div>
                <div className="gs-step">
                  <div className="gs-num">3</div>
                  <div className="gs-content">
                    <div className="gs-step-title">Type a query and press Enter</div>
                    <div className="gs-step-desc">Describe what you want to research. Narada searches the web, scrapes relevant pages, and returns a structured table — every cell value linked to its source URL.</div>
                    <div className="gs-examples">
                      <span className="gs-ex-label">Try:</span>
                      <button className="gs-ex" onClick={() => setQuery('AI startups in healthcare')}>AI startups in healthcare</button>
                      <button className="gs-ex" onClick={() => setQuery('top pizza places in Brooklyn')}>top pizza places in Brooklyn</button>
                      <button className="gs-ex" onClick={() => setQuery('electric vehicle companies in Europe')}>electric vehicle companies in Europe</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

        </div>
      </main>
    </div>
  )
}