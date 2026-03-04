import React, { useState, useEffect } from 'react'

export default function Graph({ api }) {
  const [solutions, setSolutions] = useState([])
  const [stats, setStats] = useState(null)

  const load = async () => {
    try {
      const [solRes, statsRes] = await Promise.all([
        fetch(`${api}/solutions`),
        fetch(`${api}/stats`),
      ])
      if (solRes.ok) setSolutions(await solRes.json())
      if (statsRes.ok) setStats(await statsRes.json())
    } catch {}
  }

  useEffect(() => { load() }, [])

  // Build layers
  const byId = {}
  solutions.forEach(s => { byId[s.id] = s })

  const layer1 = solutions.filter(s => !s.composed_from || s.composed_from.length === 0)
  const layer2 = solutions.filter(s => s.composed_from && s.composed_from.length === 1)
  const layer3 = solutions.filter(s => s.composed_from && s.composed_from.length >= 2)

  const totalRefs = solutions.reduce((sum, s) => sum + (s.composed_from?.length || 0), 0)
  const reuseEvents = solutions.filter(s => s.composed_from?.length > 0).length

  const renderCard = (s) => {
    const refs = s.composed_from || []
    return (
      <div key={s.id} style={{
        border: '1px solid #1a1a2e', borderRadius: 6, padding: 10,
        background: '#0d0d14', minWidth: 260, maxWidth: 340, fontSize: 11,
      }}>
        <div style={{ color: '#e0e0e0', fontWeight: 600, marginBottom: 4, fontSize: 12 }}>
          {s.task_description.length > 60 ? s.task_description.slice(0, 60) + '...' : s.task_description}
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
          <span style={{ color: '#00aaff' }}>{s.language}</span>
          <span style={{ color: '#ffaa00' }}>{(s.success_rate * 100).toFixed(0)}%</span>
          <span style={{ color: '#666' }}>by {s.agent_name}</span>
          <span style={{ color: '#444' }}>{s.id}</span>
        </div>
        {refs.length > 0 && (
          <div style={{ marginTop: 4, paddingTop: 4, borderTop: '1px solid #1a1a2e' }}>
            <span style={{ color: '#aa88ff', fontSize: 10 }}>built from: </span>
            {refs.map((rid, i) => {
              const ref = byId[rid]
              return (
                <span key={i} style={{ color: '#888', fontSize: 10 }}>
                  {i > 0 && ' + '}
                  {ref ? ref.task_description.slice(0, 30) + '...' : rid}
                  <span style={{ color: '#444' }}> [{rid}]</span>
                </span>
              )
            })}
          </div>
        )}
      </div>
    )
  }

  const renderLayer = (label, items, color) => (
    <div style={{ marginBottom: 24 }}>
      <div style={{
        color, fontWeight: 700, fontSize: 13, marginBottom: 8,
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <span style={{
          width: 8, height: 8, borderRadius: '50%', background: color,
          display: 'inline-block',
        }} />
        {label}
        <span style={{ color: '#444', fontWeight: 400, fontSize: 11 }}>({items.length})</span>
      </div>
      {items.length === 0 ? (
        <div style={{ color: '#333', fontSize: 12, paddingLeft: 16 }}>No solutions in this layer</div>
      ) : (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {items.map(renderCard)}
        </div>
      )}
    </div>
  )

  return (
    <div>
      {/* Stats bar */}
      {stats && (
        <div style={{
          display: 'flex', gap: 20, marginBottom: 24, padding: 12,
          background: '#0d0d14', borderRadius: 6, border: '1px solid #1a1a2e',
          flexWrap: 'wrap',
        }}>
          {[
            ['Total Solutions', stats.total_solutions, '#e0e0e0'],
            ['Atomic', stats.atomic_solutions, '#00aaff'],
            ['Composed', stats.composed_solutions, '#aa88ff'],
            ['Total References', totalRefs, '#ffaa00'],
            ['Reuse Events', reuseEvents, '#00ff88'],
            ['Avg Success', `${(stats.avg_success_rate * 100).toFixed(1)}%`, '#ff88ff'],
          ].map(([label, val, color]) => (
            <div key={label} style={{ textAlign: 'center' }}>
              <div style={{ color, fontSize: 20, fontWeight: 700 }}>{val}</div>
              <div style={{ color: '#555', fontSize: 10 }}>{label}</div>
            </div>
          ))}
        </div>
      )}

      <button onClick={load} style={{
        padding: '6px 14px', background: '#1a1a2e', border: '1px solid #333',
        borderRadius: 4, color: '#888', cursor: 'pointer', fontFamily: 'inherit',
        fontSize: 11, marginBottom: 16,
      }}>Refresh</button>

      {/* Layers */}
      {renderLayer('Layer 1 \u2014 Atomic Primitives', layer1, '#00aaff')}
      {renderLayer('Layer 2 \u2014 Single Composition', layer2, '#aa88ff')}
      {renderLayer('Layer 3 \u2014 Deep Compositions (2+ refs)', layer3, '#ff88ff')}
    </div>
  )
}
