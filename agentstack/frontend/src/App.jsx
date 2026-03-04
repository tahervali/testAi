import React, { useState } from 'react'
import Simulate from './tabs/Simulate'
import Graph from './tabs/Graph'
import Registry from './tabs/Registry'
import Terminal from './tabs/Terminal'

const API = 'http://localhost:8000'

const TABS = [
  { id: 'simulate', label: 'SIMULATE' },
  { id: 'graph', label: 'GRAPH' },
  { id: 'registry', label: 'REGISTRY' },
  { id: 'terminal', label: 'TERMINAL' },
]

export default function App() {
  const [tab, setTab] = useState('simulate')

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <header style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 24px', borderBottom: '1px solid #1a1a2e',
        background: '#0d0d14',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 20, fontWeight: 700, color: '#00ff88' }}>AgentStack</span>
          <span style={{ fontSize: 12, color: '#555' }}>v0.1.0</span>
        </div>
        <nav style={{ display: 'flex', gap: 4 }}>
          {TABS.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              style={{
                padding: '8px 16px',
                background: tab === t.id ? '#1a1a2e' : 'transparent',
                color: tab === t.id ? '#00ff88' : '#666',
                border: tab === t.id ? '1px solid #00ff88' : '1px solid transparent',
                borderRadius: 4,
                cursor: 'pointer',
                fontFamily: 'inherit',
                fontSize: 13,
                fontWeight: 600,
                letterSpacing: 1,
              }}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      {/* Tab content */}
      <main style={{ flex: 1, padding: 24, overflow: 'auto' }}>
        {tab === 'simulate' && <Simulate api={API} />}
        {tab === 'graph' && <Graph api={API} />}
        {tab === 'registry' && <Registry api={API} />}
        {tab === 'terminal' && <Terminal api={API} />}
      </main>
    </div>
  )
}
