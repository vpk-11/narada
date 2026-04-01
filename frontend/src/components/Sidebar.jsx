import { useSession } from '../hooks/useSession.js'

const LLM_PROVIDERS = ['groq', 'openai', 'anthropic', 'ollama']

const LLM_MODELS = {
  groq: ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant', 'qwen-qwq-32b', 'gemma2-9b-it'],
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'],
  anthropic: ['claude-opus-4-5', 'claude-sonnet-4-5', 'claude-haiku-4-5'],
  ollama: [],
}

const SEARCH_PROVIDERS = ['tavily', 'duckduckgo']

const STEPS = [
  { key: 'query_analyzer', label: 'Query Analyzer' },
  { key: 'extractor', label: 'Extractor' },
  { key: 'validator', label: 'Validator' },
]

const DEFAULT_CONFIG = {
  groq_api_key: '',
  openai_api_key: '',
  anthropic_api_key: '',
  tavily_api_key: '',
  ollama_base_url: 'http://localhost:11434',
  search_provider: 'tavily',
  query_analyzer: { provider: 'groq', model: 'llama-3.3-70b-versatile' },
  extractor: { provider: 'groq', model: 'llama-3.3-70b-versatile' },
  validator: { provider: 'groq', model: 'llama-3.3-70b-versatile' },
}

export default function Sidebar() {
  const [config, setConfig] = useSession('narada_config', DEFAULT_CONFIG)

  function setKey(field, value) {
    setConfig(c => ({ ...c, [field]: value }))
  }

  function setStep(step, field, value) {
    setConfig(c => ({
      ...c,
      [step]: { ...c[step], [field]: value }
    }))
  }

  function handleProviderChange(step, provider) {
    const models = LLM_MODELS[provider]
    const model = models.length > 0 ? models[0] : ''
    setConfig(c => ({ ...c, [step]: { provider, model } }))
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">Narada</div>
        <div className="sidebar-tagline">Agentic Research Intelligence</div>
      </div>

      <div className="sidebar-body">

        {/* Security disclosure */}
        <div className="session-note" style={{ marginBottom: 20 }}>
          <strong>How your keys are handled:</strong>
          <ul style={{ marginTop: 6, paddingLeft: 14, lineHeight: 1.8 }}>
            <li>Stored in <strong>sessionStorage</strong> only</li>
            <li>Cleared when this tab closes</li>
            <li>Sent as <strong>request headers</strong>, not body</li>
            <li>Used per-request and <strong>never stored</strong> server-side</li>
            <li>Never appear in server logs</li>
          </ul>
        </div>

        {/* Search provider */}
        <div className="sidebar-section">
          <div className="sidebar-section-title">Search Provider</div>
          <div className="field">
            <label>Provider</label>
            <select
              value={config.search_provider}
              onChange={e => setKey('search_provider', e.target.value)}
            >
              {SEARCH_PROVIDERS.map(p => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>

          {config.search_provider === 'tavily' && (
            <div className="field">
              <label>Tavily API Key</label>
              <input
                type="password"
                placeholder="tvly-..."
                value={config.tavily_api_key}
                onChange={e => setKey('tavily_api_key', e.target.value)}
              />
            </div>
          )}
        </div>

        {/* API Keys */}
        <div className="sidebar-section">
          <div className="sidebar-section-title">LLM API Keys</div>

          <div className="field">
            <label>Groq API Key</label>
            <input
              type="password"
              placeholder="gsk_..."
              value={config.groq_api_key}
              onChange={e => setKey('groq_api_key', e.target.value)}
            />
          </div>

          <div className="field">
            <label>OpenAI API Key</label>
            <input
              type="password"
              placeholder="sk-..."
              value={config.openai_api_key}
              onChange={e => setKey('openai_api_key', e.target.value)}
            />
          </div>

          <div className="field">
            <label>Anthropic API Key</label>
            <input
              type="password"
              placeholder="sk-ant-..."
              value={config.anthropic_api_key}
              onChange={e => setKey('anthropic_api_key', e.target.value)}
            />
          </div>

          <div className="field">
            <label>Ollama Base URL</label>
            <input
              type="text"
              value={config.ollama_base_url}
              onChange={e => setKey('ollama_base_url', e.target.value)}
            />
          </div>
        </div>

        {/* Per-step config */}
        <div className="sidebar-section">
          <div className="sidebar-section-title">Pipeline Step Config</div>

          {STEPS.map(({ key, label }) => (
            <div className="step-config" key={key}>
              <div className="step-config-label">{label}</div>

              <div className="field">
                <label>Provider</label>
                <select
                  value={config[key]?.provider || 'groq'}
                  onChange={e => handleProviderChange(key, e.target.value)}
                >
                  {LLM_PROVIDERS.map(p => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>

              <div className="field">
                <label>Model</label>
                {LLM_MODELS[config[key]?.provider]?.length > 0 ? (
                  <select
                    value={config[key]?.model || ''}
                    onChange={e => setStep(key, 'model', e.target.value)}
                  >
                    {LLM_MODELS[config[key]?.provider].map(m => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    placeholder="e.g. qwen3:4b"
                    value={config[key]?.model || ''}
                    onChange={e => setStep(key, 'model', e.target.value)}
                  />
                )}
              </div>
            </div>
          ))}
        </div>

      </div>
    </aside>
  )
}

export { DEFAULT_CONFIG }