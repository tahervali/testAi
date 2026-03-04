import React from 'react'

const STEP_COLORS = {
  think: '#8888ff',
  decompose: '#aa88ff',
  pull: '#00aaff',
  hit: '#00ff88',
  miss: '#ff6644',
  compose: '#ffaa00',
  test: '#ff88ff',
  rate: '#88ddff',
  push: '#00ff88',
  done: '#00ff88',
  error: '#ff4444',
}

const STEP_ICONS = {
  think: '\u2261',
  decompose: '\u2193',
  pull: '\u2190',
  hit: '\u2713',
  miss: '\u2717',
  compose: '\u2692',
  test: '\u25B6',
  rate: '\u2605',
  push: '\u2191',
  done: '\u25CF',
  error: '\u26A0',
}

export default function StepCard({ step, data }) {
  const color = STEP_COLORS[step] || '#666'
  const icon = STEP_ICONS[step] || '\u2022'

  let detail = ''
  if (step === 'think') detail = data.task || ''
  else if (step === 'decompose' && data.subtasks) detail = data.subtasks.join(' | ')
  else if (step === 'decompose') detail = data.status || ''
  else if (step === 'hit') detail = `${data.subtask} \u2192 ${data.solution_id} (score: ${data.score})`
  else if (step === 'miss') detail = data.subtask || ''
  else if (step === 'compose') detail = data.status === 'done' ? `${data.code_length} chars` : data.status
  else if (step === 'test') detail = data.passed !== undefined ? (data.passed ? `PASS: ${data.reason}` : `FAIL: ${data.reason}`) : data.status
  else if (step === 'rate') detail = `${data.solution_id} \u2192 ${data.rating}`
  else if (step === 'push') detail = `${data.solution_id} [refs: ${(data.composed_from || []).length}]`
  else if (step === 'done') detail = data.passed ? 'completed successfully' : 'completed with failures'
  else if (step === 'error') detail = data.message || ''

  return (
    <div style={{
      display: 'flex', gap: 8, alignItems: 'flex-start',
      padding: '4px 0', fontSize: 12, lineHeight: '18px',
    }}>
      <span style={{
        color, fontWeight: 700, minWidth: 18, textAlign: 'center',
      }}>{icon}</span>
      <span style={{
        color, fontWeight: 600, minWidth: 80, textTransform: 'uppercase',
        fontSize: 11,
      }}>{step}</span>
      <span style={{ color: '#999', flex: 1, wordBreak: 'break-word' }}>
        {detail}
      </span>
    </div>
  )
}
