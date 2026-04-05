import { useSession } from '../hooks/useSession.js'

const IS_LOCAL = ['localhost', '127.0.0.1'].includes(window.location.hostname)

// LLM_PROVIDERS is derived inside the component based on effectiveLocal

export const DEFAULT_MODELS = {
  groq:      'llama-3.3-70b-versatile',
  openai:    'gpt-4o-mini',
  anthropic: 'claude-haiku-4-5-20251001',
  ollama:    'qwen3:4b',
}

const SEARCH_PROVIDERS = ['tavily', 'duckduckgo', 'brave']

const STEPS = [
  {
    key: 'query_analyzer',
    label: 'Query Analyzer',
    tip: 'Figures out what kind of things you are looking for and what details to extract. Also generates targeted search queries from your input.',
  },
  {
    key: 'extractor',
    label: 'Extractor',
    tip: 'Reads each web page and pulls out structured data - names, dates, locations, and whatever other attributes fit your query.',
  },
  {
    key: 'validator',
    label: 'Validator',
    tip: 'Reviews all extracted results and filters out anything that does not actually match your query - removing noise and off-topic entries.',
  },
]

export const DEFAULT_CONFIG = {
  groq_api_key: '',
  openai_api_key: '',
  anthropic_api_key: '',
  brave_api_key: '',
  tavily_api_key: '',
  ollama_base_url: 'http://localhost:11434',
  search_provider: 'tavily',
  llm_mode: 'unified',
  llm: { provider: 'groq', model: DEFAULT_MODELS.groq },
  query_analyzer: { provider: 'groq', model: DEFAULT_MODELS.groq },
  extractor:      { provider: 'groq', model: DEFAULT_MODELS.groq },
  validator:      { provider: 'groq', model: DEFAULT_MODELS.groq },
  use_cache: true,
  sim_prod: false,   // dev-only: simulate production behaviour locally
}

function LogoMark() {
  return (
    <svg viewBox="0 0 18 18" fill="none">
      <circle cx="9" cy="9" r="6" stroke="#fff" strokeWidth="1.5"/>
      <path d="M6 9h6M9 6v6" stroke="#fff" strokeWidth="1.5" strokeLinecap="round"/>
      <circle cx="9" cy="9" r="1.8" fill="#fff"/>
    </svg>
  )
}

export default function Sidebar() {
  const [config, setConfig] = useSession('narada_config', DEFAULT_CONFIG)

  function set(field, value) {
    setConfig(c => ({ ...c, [field]: value }))
  }

  function setStep(step, field, value) {
    setConfig(c => ({ ...c, [step]: { ...c[step], [field]: value } }))
  }

  function onProviderChange(step, provider) {
    setConfig(c => ({ ...c, [step]: { provider, model: DEFAULT_MODELS[provider] || '' } }))
  }

  function onUnifiedProviderChange(provider) {
    setConfig(c => ({ ...c, llm: { provider, model: DEFAULT_MODELS[provider] || '' } }))
  }

  const llmMode = config.llm_mode || 'unified'
  // When sim_prod is on, behave as if we are in production
  const effectiveLocal = IS_LOCAL && !config.sim_prod
  const LLM_PROVIDERS = effectiveLocal
    ? ['groq', 'openai', 'anthropic', 'ollama']
    : ['groq', 'openai', 'anthropic']

  return (
    <aside className="sidebar">

      {/* Logo */}
      <div className="sidebar-top">
        <div className="sidebar-logo-row">
          <div className="logo-mark"><LogoMark /></div>
          <span className="logo-name">
            Narada
            {IS_LOCAL && (
              <sup className={`dev-badge ${config.sim_prod ? 'dev-badge-sim' : ''}`}>
                {config.sim_prod ? 'SIM PROD' : 'DEV'}
              </sup>
            )}
          </span>
        </div>
        <div className="logo-sub">Research Intelligence</div>
      </div>

      {/* Body */}
      <div className="sidebar-body">

        {/* Security */}
        <div className="s-section">
          <div className="s-label">Security</div>
          <div className="s-section-note">Your keys never leave your browser tab. They are held in sessionStorage and sent directly as request headers - cleared the moment you close the tab.</div>
          <div className="sec-note">
            <div className="sec-note-title">
              <span className="sec-dot" />
              Key Handling
            </div>
            <ul>
              <li>sessionStorage only</li>
              <li>Cleared on tab close</li>
              <li>Sent as request headers</li>
              <li>Never stored server-side</li>
              <li>Never appear in logs</li>
            </ul>
          </div>
        </div>

        {/* Search provider */}
        <div className="s-section">
          <div className="s-label">Search Provider</div>
          <div className="s-section-note">
            The service Narada uses to find relevant URLs for your query. Tavily is built for AI agents and gives the best results. DuckDuckGo requires no key.
          </div>
          <div className="s-fallback-note">Leave the key field empty to use the server's configured key.</div>
          <div className="field">
            <label>Provider</label>
            <select value={config.search_provider} onChange={e => set('search_provider', e.target.value)}>
              {SEARCH_PROVIDERS.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          {config.search_provider === 'tavily' && (
            <div className="field">
              <label>Tavily API Key</label>
              <input type="password" placeholder="tvly-..."
                value={config.tavily_api_key}
                onChange={e => set('tavily_api_key', e.target.value)} />
            </div>
          )}
          {config.search_provider === 'brave' && (
            <div className="field">
              <label>Brave API Key</label>
              <input type="password" placeholder="BSA_..."
                value={config.brave_api_key}
                onChange={e => set('brave_api_key', e.target.value)} />
            </div>
          )}
        </div>

        {/* LLM API Keys */}
        <div className="s-section">
          <div className="s-label">LLM API Keys</div>
          <div className="s-section-note">
            The AI model that reads pages and extracts structured data. Groq is recommended - it is fast, free, and handles all three pipeline steps well.
          </div>
          <div className="s-fallback-note">Leave any field empty to fall back to the server's configured key for that provider.</div>
          <div className="field">
            <label>Groq</label>
            <input type="password" placeholder="gsk_..." value={config.groq_api_key}
              onChange={e => set('groq_api_key', e.target.value)} />
          </div>
          <div className="field">
            <label>OpenAI</label>
            <input type="password" placeholder="sk-..." value={config.openai_api_key}
              onChange={e => set('openai_api_key', e.target.value)} />
          </div>
          <div className="field">
            <label>Anthropic</label>
            <input type="password" placeholder="sk-ant-..." value={config.anthropic_api_key}
              onChange={e => set('anthropic_api_key', e.target.value)} />
          </div>
          {effectiveLocal && (
            <div className="field">
              <label>Ollama URL</label>
              <input type="text" value={config.ollama_base_url}
                onChange={e => set('ollama_base_url', e.target.value)} />
            </div>
          )}
        </div>

        {/* Cache - local only */}
        {effectiveLocal && (
          <div className="s-section">
            <div className="s-label">Cache</div>
            <div className="s-section-note">When enabled, identical queries return instantly from disk instead of re-running the full pipeline. Disabled automatically in production.</div>
            <div className="toggle-row">
              <span className="toggle-label">Use cached results</span>
              <button
                className={`toggle-btn ${config.use_cache ? 'on' : 'off'}`}
                onClick={() => set('use_cache', !config.use_cache)}
              >
                <span className="toggle-thumb" />
              </button>
            </div>
            <div className="cache-hint">
              {config.use_cache
                ? 'Same query returns instantly if cached'
                : 'Every search runs fresh - no cache'}
            </div>
          </div>
        )}

        {/* Pipeline LLM */}
        <div className="s-section">
          <div className="s-label-row">
            <div className="s-label" style={{ marginBottom: 0 }}>Pipeline LLM</div>
            <div className="mode-toggle">
              <button
                className={`mode-btn ${llmMode === 'unified' ? 'active' : ''}`}
                onClick={() => set('llm_mode', 'unified')}
              >Unified</button>
              <button
                className={`mode-btn ${llmMode === 'per-step' ? 'active' : ''}`}
                onClick={() => set('llm_mode', 'per-step')}
              >Per Step</button>
            </div>
          </div>
          <div className="s-section-note" style={{ marginTop: 10 }}>
            {llmMode === 'unified'
              ? 'One provider and model handles all three pipeline steps. The simplest setup - good for most queries.'
              : 'Assign a different provider and model to each pipeline step. Useful if you want a lightweight model for analysis and a larger one for extraction.'}
          </div>

          {llmMode === 'unified' ? (
            <div className="step-block" style={{ marginTop: 14 }}>
              <div className="step-header">
                <span className="step-name" style={{ fontSize: 15, color: 'var(--text-3)', fontWeight: 400 }}>All stages</span>
                <div className="step-help">
                  <div className="step-help-icon">?</div>
                  <div className="step-tooltip">
                    The same provider and model is used for Query Analysis, Extraction, and Validation.
                    Switch to Per Step if you want to use a different model for each stage.
                  </div>
                </div>
              </div>
              <div className="field">
                <label>Provider</label>
                <select value={config.llm?.provider || 'groq'}
                  onChange={e => onUnifiedProviderChange(e.target.value)}>
                  {LLM_PROVIDERS.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div className="field">
                <label>Model</label>
                <input type="text"
                  placeholder={DEFAULT_MODELS[config.llm?.provider] || 'model name'}
                  value={config.llm?.model || ''}
                  onChange={e => set('llm', { ...config.llm, model: e.target.value })} />
              </div>
            </div>
          ) : (
            <div style={{ marginTop: 14 }}>
              {STEPS.map(({ key, label, tip }) => (
                <div className="step-block" key={key}>
                  <div className="step-header">
                    <div className="step-dot" />
                    <span className="step-name">{label}</span>
                    <div className="step-help">
                      <div className="step-help-icon">?</div>
                      <div className="step-tooltip">{tip}</div>
                    </div>
                  </div>
                  <div className="field">
                    <label>Provider</label>
                    <select value={config[key]?.provider || 'groq'}
                      onChange={e => onProviderChange(key, e.target.value)}>
                      {LLM_PROVIDERS.map(p => <option key={p} value={p}>{p}</option>)}
                    </select>
                  </div>
                  <div className="field">
                    <label>Model</label>
                    <input type="text" placeholder={DEFAULT_MODELS[config[key]?.provider] || 'model name'}
                      value={config[key]?.model || ''}
                      onChange={e => setStep(key, 'model', e.target.value)} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Dev Tools — local only */}
        {IS_LOCAL && (
          <div className="s-section s-section-dev">
            <div className="s-label">Dev Tools</div>
            <div className="s-section-note">Simulate how the app behaves in production so you can test prod-only flows (key errors, fallback popup) without deploying.</div>
            <div className="toggle-row">
              <span className="toggle-label">Simulate production</span>
              <button
                className={`toggle-btn ${config.sim_prod ? 'on' : 'off'}`}
                onClick={() => set('sim_prod', !config.sim_prod)}
              >
                <span className="toggle-thumb" />
              </button>
            </div>
            {config.sim_prod && (
              <div className="cache-hint" style={{ color: 'var(--accent)' }}>
                Acting as prod: no Ollama, no cache, key errors show fallback popup
              </div>
            )}
          </div>
        )}

      </div>

    </aside>
  )
}
