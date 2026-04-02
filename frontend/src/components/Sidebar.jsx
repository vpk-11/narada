import { useSession } from '../hooks/useSession.js'

const LLM_PROVIDERS = ['groq', 'openai', 'anthropic', 'ollama']

const DEFAULT_MODELS = {
  groq:      'llama-3.3-70b-versatile',
  openai:    'gpt-4o-mini',
  anthropic: 'claude-haiku-4-5-20251001',
  ollama:    'qwen3:4b',
}

const SEARCH_PROVIDERS = ['tavily', 'duckduckgo', 'brave']

const STEPS = [
  { key: 'query_analyzer', label: 'Query Analyzer' },
  { key: 'extractor',      label: 'Extractor' },
  { key: 'validator',      label: 'Validator' },
]

export const DEFAULT_CONFIG = {
  groq_api_key: '',
  openai_api_key: '',
  anthropic_api_key: '',
  tavily_api_key: '',
  ollama_base_url: 'http://localhost:11434',
  search_provider: 'tavily',
  query_analyzer: { provider: 'groq', model: 'llama-3.3-70b-versatile' },
  extractor:      { provider: 'groq', model: 'llama-3.3-70b-versatile' },
  validator:      { provider: 'groq', model: 'llama-3.3-70b-versatile' },
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

function UserIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="8" cy="5.5" r="2.5"/>
      <path d="M2.5 13.5c0-3.038 2.462-5.5 5.5-5.5s5.5 2.462 5.5 5.5"/>
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

  return (
    <aside className="sidebar">

      {/* Logo */}
      <div className="sidebar-top">
        <div className="sidebar-logo-row">
          <div className="logo-mark"><LogoMark /></div>
          <span className="logo-name">Narada</span>
        </div>
        <div className="logo-sub">Research Intelligence</div>
      </div>

      {/* Body */}
      <div className="sidebar-body">

        {/* Security */}
        <div className="s-section">
          <div className="s-label">Security</div>
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
          <div className="field">
            <label>Provider</label>
            <select value={config.search_provider} onChange={e => set('search_provider', e.target.value)}>
              {SEARCH_PROVIDERS.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          {config.search_provider === 'tavily' && (
            <div className="field">
              <label>Tavily API Key</label>
              <input type="password" placeholder="tvly-..." value={config.tavily_api_key}
                onChange={e => set('tavily_api_key', e.target.value)} />
            </div>
          )}
        </div>

        {/* LLM keys */}
        <div className="s-section">
          <div className="s-label">LLM API Keys</div>
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
          <div className="field">
            <label>Ollama URL</label>
            <input type="text" value={config.ollama_base_url}
              onChange={e => set('ollama_base_url', e.target.value)} />
          </div>
        </div>

        {/* Pipeline steps */}
        <div className="s-section">
          <div className="s-label">Pipeline Steps</div>
          {STEPS.map(({ key, label }) => (
            <div className="step-block" key={key}>
              <div className="step-header">
                <div className="step-dot" />
                <span className="step-name">{label}</span>
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

      </div>

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="avatar"><UserIcon /></div>
        <div>
          <div className="profile-name">Kaushik</div>
          <div className="profile-ver">narada v0.1</div>
        </div>
      </div>

    </aside>
  )
}