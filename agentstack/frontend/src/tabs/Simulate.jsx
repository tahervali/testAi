import React, { useState, useRef, useEffect } from 'react'
import AgentPanel from '../components/AgentPanel'
import SolutionCard from '../components/SolutionCard'

export default function Simulate({ api }) {
  const [completedWaves, setCompletedWaves] = useState(new Set())
  const [runningWave, setRunningWave] = useState(null)
  const [agentSteps, setAgentSteps] = useState({})
  const [feed, setFeed] = useState([])
  const [solutions, setSolutions] = useState([])
  const feedRef = useRef(null)

  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight
    }
  }, [feed])

  const loadSolutions = async () => {
    try {
      const res = await fetch(`${api}/solutions`)
      if (res.ok) setSolutions(await res.json())
    } catch {}
  }

  const runWave = async (wave) => {
    setRunningWave(wave)
    setAgentSteps({})
    setFeed([])

    try {
      const res = await fetch(`${api}/simulate/wave`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ wave }),
      })

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))
            setFeed(prev => [...prev, event])

            if (event.agent && event.agent !== 'system') {
              setAgentSteps(prev => ({
                ...prev,
                [event.agent]: [...(prev[event.agent] || []), event],
              }))
            }

            if (event.step === 'push') {
              loadSolutions()
            }

            if (event.step === 'wave_complete') {
              setCompletedWaves(prev => new Set([...prev, wave]))
              setRunningWave(null)
            }
          } catch {}
        }
      }
    } catch (err) {
      setFeed(prev => [...prev, { agent: 'system', step: 'error', message: err.message }])
      setRunningWave(null)
    }
  }

  const canRun = (wave) => {
    if (runningWave) return false
    if (wave === 1) return true
    return completedWaves.has(wave - 1)
  }

  return (
    <div>
      {/* Wave buttons */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {[1, 2, 3].map(w => (
          <button
            key={w}
            onClick={() => runWave(w)}
            disabled={!canRun(w)}
            style={{
              padding: '10px 24px',
              background: runningWave === w ? '#113311' : completedWaves.has(w) ? '#0d0d14' : '#1a1a2e',
              border: `1px solid ${completedWaves.has(w) ? '#00ff88' : canRun(w) ? '#00aaff' : '#333'}`,
              borderRadius: 4,
              color: completedWaves.has(w) ? '#00ff88' : canRun(w) ? '#00aaff' : '#444',
              cursor: canRun(w) ? 'pointer' : 'not-allowed',
              fontFamily: 'inherit',
              fontWeight: 600,
              fontSize: 13,
            }}
          >
            {runningWave === w ? `Wave ${w} running...` : completedWaves.has(w) ? `Wave ${w} \u2713` : `Wave ${w}`}
          </button>
        ))}
      </div>

      {/* Agent panels */}
      {Object.keys(agentSteps).length > 0 && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          {Object.entries(agentSteps).map(([name, steps]) => (
            <AgentPanel key={name} name={name} steps={steps} />
          ))}
        </div>
      )}

      {/* Live feed */}
      {feed.length > 0 && (
        <div>
          <div style={{ color: '#666', fontSize: 11, marginBottom: 6, fontWeight: 600 }}>
            LIVE FEED ({feed.length} events)
          </div>
          <div
            ref={feedRef}
            style={{
              maxHeight: 200, overflow: 'auto', background: '#080810',
              border: '1px solid #1a1a2e', borderRadius: 4, padding: 8,
            }}
          >
            {feed.map((e, i) => (
              <div key={i} style={{ fontSize: 11, color: '#666', lineHeight: '18px' }}>
                <span style={{ color: '#00aaff' }}>{e.agent}</span>
                {' '}
                <span style={{ color: '#888' }}>{e.step}</span>
                {e.message && <span style={{ color: '#ff4444' }}> {e.message}</span>}
                {e.solution_id && <span style={{ color: '#00ff88' }}> [{e.solution_id}]</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recently pushed solutions */}
      {solutions.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div style={{ color: '#666', fontSize: 11, marginBottom: 6, fontWeight: 600 }}>
            REGISTRY ({solutions.length} solutions)
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {solutions.slice(0, 10).map(s => (
              <SolutionCard key={s.id} solution={s} compact />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
