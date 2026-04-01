import { useState } from 'react'

function SourceChip({ url }) {
  if (!url) return null
  let host = url
  try { host = new URL(url).hostname } catch {}
  return (
    <a href={url} target="_blank" rel="noopener noreferrer"
      className="source-chip" onClick={e => e.stopPropagation()} title={url}>
      ↗ {host}
    </a>
  )
}

function Detail({ entity, attributes, cols }) {
  return (
    <tr className="detail-row">
      <td colSpan={cols}>
        <div className="detail-inner">
          <div className="detail-grid">
            {attributes.map(attr => {
              const cell = entity.attributes[attr]
              return (
                <div className="detail-card" key={attr}>
                  <div className="dc-key">{attr.replace(/_/g, ' ')}</div>
                  {cell
                    ? <><div className="dc-val">{cell.value}</div><SourceChip url={cell.source_url} /></>
                    : <div className="dc-nil">not found</div>
                  }
                </div>
              )
            })}
          </div>
        </div>
      </td>
    </tr>
  )
}

export default function ResultsTable({ result }) {
  const [open, setOpen] = useState(new Set())
  if (!result) return null

  const { entities, attributes } = result
  const inline = attributes.slice(0, 4)
  const cols   = inline.length + 2

  function toggle(name) {
    setOpen(prev => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th />
            <th>Entity</th>
            {inline.map(a => <th key={a}>{a.replace(/_/g, ' ')}</th>)}
          </tr>
        </thead>
        <tbody>
          {entities.map(entity => {
            const isOpen = open.has(entity.name)
            return (
              <>
                <tr key={entity.name}
                  className={isOpen ? 'is-open' : ''}
                  onClick={() => toggle(entity.name)}>
                  <td>
                    <button className="expand-btn"
                      onClick={e => { e.stopPropagation(); toggle(entity.name) }}>
                      {isOpen ? '−' : '+'}
                    </button>
                  </td>
                  <td><span className="cell-name">{entity.name}</span></td>
                  {inline.map(attr => {
                    const cell = entity.attributes[attr]
                    return (
                      <td key={attr}>
                        {cell
                          ? <span className="cell-val" title={cell.value}>{cell.value}</span>
                          : <span className="cell-nil">—</span>
                        }
                      </td>
                    )
                  })}
                </tr>
                {isOpen && <Detail key={`${entity.name}-d`} entity={entity} attributes={attributes} cols={cols} />}
              </>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}