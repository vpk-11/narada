import { useState } from 'react'

function SourceLink({ url }) {
  if (!url) return null
  let display = url
  try {
    display = new URL(url).hostname
  } catch {}

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="source-link"
      onClick={e => e.stopPropagation()}
      title={url}
    >
      ↗ {display}
    </a>
  )
}

function DetailRow({ entity, attributes, colSpan }) {
  return (
    <tr className="detail-row">
      <td colSpan={colSpan}>
        <div>
          <div className="detail-grid">
            {attributes.map(attr => {
              const cell = entity.attributes[attr]
              return (
                <div className="detail-card" key={attr}>
                  <div className="detail-card-key">{attr.replace(/_/g, ' ')}</div>
                  {cell ? (
                    <>
                      <div className="detail-card-value">{cell.value}</div>
                      <SourceLink url={cell.source_url} />
                    </>
                  ) : (
                    <div className="cell-empty">not found</div>
                  )}
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
  const [expanded, setExpanded] = useState(new Set())

  if (!result) return null

  const { entities, attributes } = result

  // Show up to 4 columns inline, rest in expanded detail
  const inlineCols = attributes.slice(0, 4)
  const totalCols = inlineCols.length + 2  // expand + name + inline cols

  function toggleRow(name) {
    setExpanded(prev => {
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
            <th></th>
            <th>Entity</th>
            {inlineCols.map(attr => (
              <th key={attr}>{attr.replace(/_/g, ' ')}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {entities.map(entity => {
            const isExpanded = expanded.has(entity.name)
            return (
              <>
                <tr
                  key={entity.name}
                  className={isExpanded ? 'expanded' : ''}
                  onClick={() => toggleRow(entity.name)}
                >
                  <td>
                    <span className="expand-icon">
                      {isExpanded ? '−' : '+'}
                    </span>
                  </td>
                  <td>
                    <span className="entity-name">{entity.name}</span>
                  </td>
                  {inlineCols.map(attr => {
                    const cell = entity.attributes[attr]
                    return (
                      <td key={attr}>
                        {cell ? (
                          <span className="cell-value" title={cell.value}>
                            {cell.value}
                          </span>
                        ) : (
                          <span className="cell-empty">—</span>
                        )}
                      </td>
                    )
                  })}
                </tr>

                {isExpanded && (
                  <DetailRow
                    key={`${entity.name}-detail`}
                    entity={entity}
                    attributes={attributes}
                    colSpan={totalCols}
                  />
                )}
              </>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
