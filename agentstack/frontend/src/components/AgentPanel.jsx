import React from 'react'
import StepCard from './StepCard'

export default function AgentPanel({ name, steps }) {
  const isDone = steps.some(s => s.step === 'done')
  const hasError = steps.some(s => s.step === 'error')
  const borderColor = hasError ? '#ff4444' : isDone ? '#00ff88' : '#333'

  return (
    <div style={{
      border: `1px solid ${borderColor}`,
      borderRadius: 6,
      padding: 12,
      background: '#0d0d14',
      minWidth: 320,
      flex: 1,
    }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 8, paddingBottom: 8, borderBottom: '1px solid #1a1a2e',
      }}>
        <span style={{ color: '#00aaff', fontWeight: 700, fontSize: 13 }}>{name}</span>
        <span style={{
          fontSize: 10, padding: '2px 8px', borderRadius: 3,
          background: hasError ? '#331111' : isDone ? '#113311' : '#111133',
          color: hasError ? '#ff4444' : isDone ? '#00ff88' : '#8888ff',
        }}>
          {hasError ? 'ERROR' : isDone ? 'DONE' : 'RUNNING'}
        </span>
      </div>
      <div style={{ maxHeight: 400, overflow: 'auto' }}>
        {steps.map((s, i) => (
          <StepCard key={i} step={s.step} data={s} />
        ))}
        {steps.length === 0 && (
          <span style={{ color: '#444', fontSize: 12 }}>Waiting...</span>
        )}
      </div>
    </div>
  )
}
