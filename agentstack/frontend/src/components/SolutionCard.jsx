import React, { useState } from 'react'

export default function SolutionCard({ solution, compact }) {
  const [expanded, setExpanded] = useState(false)
  const s = solution
  const refs = s.composed_from?.length || 0
  const stars = s.success_rate >= 0.8 ? '\u2605\u2605\u2605' : s.success_rate >= 0.5 ? '\u2605\u2605' : s.success_rate > 0 ? '\u2605' : '\u2606'

  return (
    <div style={{
      border: '1px solid #1a1a2e',
      borderRadius: 6,
      padding: 10,
      background: '#0d0d14',
      fontSize: 12,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
        <div style={{ flex: 1 }}>
          <div style={{ color: '#e0e0e0', fontWeight: 600, marginBottom: 4 }}>
            {s.task_description}
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{ color: '#00aaff', fontSize: 10 }}>{s.language}</span>
            <span style={{ color: '#ffaa00', fontSize: 10 }}>{stars} {(s.success_rate * 100).toFixed(0)}%</span>
            <span style={{ color: '#666', fontSize: 10 }}>attempts: {s.attempt_count}</span>
            <span style={{ color: '#888', fontSize: 10 }}>by {s.agent_name}</span>
            {refs > 0 && <span style={{ color: '#aa88ff', fontSize: 10 }}>refs: {refs}</span>}
          </div>
          {s.tags?.length > 0 && (
            <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
              {s.tags.map((t, i) => (
                <span key={i} style={{
                  padding: '1px 6px', background: '#1a1a2e', borderRadius: 3,
                  color: '#888', fontSize: 10,
                }}>{t}</span>
              ))}
            </div>
          )}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-end' }}>
          <span style={{ color: '#444', fontSize: 10 }}>{s.id}</span>
          {!compact && (
            <button
              onClick={() => setExpanded(!expanded)}
              style={{
                background: '#1a1a2e', border: '1px solid #333', borderRadius: 3,
                color: '#888', padding: '2px 8px', cursor: 'pointer',
                fontFamily: 'inherit', fontSize: 10,
              }}
            >{expanded ? 'hide' : 'code'}</button>
          )}
        </div>
      </div>
      {expanded && (
        <pre style={{
          marginTop: 8, padding: 8, background: '#080810', borderRadius: 4,
          overflow: 'auto', maxHeight: 300, fontSize: 11, color: '#aaa',
          border: '1px solid #1a1a2e',
        }}>{s.solution}</pre>
      )}
    </div>
  )
}
