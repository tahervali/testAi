import React, { useState, useEffect } from 'react'
import SolutionCard from '../components/SolutionCard'

export default function Registry({ api }) {
  const [solutions, setSolutions] = useState([])
  const [search, setSearch] = useState('')
  const [searchResults, setSearchResults] = useState(null)
  const [showPush, setShowPush] = useState(false)
  const [pushForm, setPushForm] = useState({
    task_description: '',
    solution: '',
    solution_type: 'artifact',
    language: 'python',
    tags: '',
    input_schema: '',
    output_schema: '',
    api_key: '',
  })
  const [pushMsg, setPushMsg] = useState('')

  const loadSolutions = async () => {
    try {
      const res = await fetch(`${api}/solutions`)
      if (res.ok) setSolutions(await res.json())
    } catch {}
  }

  useEffect(() => { loadSolutions() }, [])

  const doSearch = async () => {
    if (!search.trim()) { setSearchResults(null); return }
    try {
      const res = await fetch(`${api}/solutions/search?q=${encodeURIComponent(search)}`)
      if (res.ok) {
        const data = await res.json()
        setSearchResults(data.map(r => r.solution))
      }
    } catch {}
  }

  useEffect(() => {
    const t = setTimeout(doSearch, 300)
    return () => clearTimeout(t)
  }, [search])

  const doPush = async () => {
    setPushMsg('')
    if (!pushForm.api_key) { setPushMsg('API key required'); return }
    if (!pushForm.task_description || !pushForm.solution) { setPushMsg('Task description and solution code required'); return }

    try {
      const res = await fetch(`${api}/solutions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': pushForm.api_key,
        },
        body: JSON.stringify({
          ...pushForm,
          tags: pushForm.tags.split(',').map(t => t.trim()).filter(Boolean),
          api_key: undefined,
        }),
      })
      if (res.ok) {
        setPushMsg('Pushed successfully!')
        setPushForm(f => ({ ...f, task_description: '', solution: '', tags: '' }))
        loadSolutions()
      } else {
        const err = await res.json()
        setPushMsg(`Error: ${err.detail || 'Push failed'}`)
      }
    } catch (e) {
      setPushMsg(`Error: ${e.message}`)
    }
  }

  const displayed = searchResults !== null ? searchResults : solutions

  return (
    <div>
      {/* Search bar */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search solutions..."
          style={{
            flex: 1, padding: '8px 12px', background: '#0d0d14',
            border: '1px solid #1a1a2e', borderRadius: 4, color: '#e0e0e0',
            fontFamily: 'inherit', fontSize: 13, outline: 'none',
          }}
        />
        <button
          onClick={() => setShowPush(!showPush)}
          style={{
            padding: '8px 16px', background: showPush ? '#113311' : '#1a1a2e',
            border: `1px solid ${showPush ? '#00ff88' : '#333'}`,
            borderRadius: 4, color: showPush ? '#00ff88' : '#888',
            cursor: 'pointer', fontFamily: 'inherit', fontSize: 12,
          }}
        >PUSH</button>
      </div>

      {/* Push form */}
      {showPush && (
        <div style={{
          marginBottom: 16, padding: 16, background: '#0d0d14',
          border: '1px solid #1a1a2e', borderRadius: 6,
        }}>
          <div style={{ color: '#666', fontSize: 11, fontWeight: 600, marginBottom: 8 }}>PUSH NEW SOLUTION</div>
          <div style={{ display: 'grid', gap: 8 }}>
            {[
              ['api_key', 'API Key', 'text'],
              ['task_description', 'Task Description', 'text'],
              ['language', 'Language', 'text'],
              ['tags', 'Tags (comma-separated)', 'text'],
              ['input_schema', 'Input Schema (optional)', 'text'],
              ['output_schema', 'Output Schema (optional)', 'text'],
            ].map(([key, label, type]) => (
              <div key={key}>
                <label style={{ color: '#555', fontSize: 10 }}>{label}</label>
                <input
                  type={type}
                  value={pushForm[key]}
                  onChange={e => setPushForm(f => ({ ...f, [key]: e.target.value }))}
                  style={{
                    width: '100%', padding: '6px 10px', background: '#080810',
                    border: '1px solid #1a1a2e', borderRadius: 3, color: '#e0e0e0',
                    fontFamily: 'inherit', fontSize: 12, outline: 'none',
                  }}
                />
              </div>
            ))}
            <div>
              <label style={{ color: '#555', fontSize: 10 }}>Solution Type</label>
              <select
                value={pushForm.solution_type}
                onChange={e => setPushForm(f => ({ ...f, solution_type: e.target.value }))}
                style={{
                  width: '100%', padding: '6px 10px', background: '#080810',
                  border: '1px solid #1a1a2e', borderRadius: 3, color: '#e0e0e0',
                  fontFamily: 'inherit', fontSize: 12,
                }}
              >
                <option value="artifact">artifact</option>
                <option value="tool_call">tool_call</option>
                <option value="subagent">subagent</option>
                <option value="skill">skill</option>
              </select>
            </div>
            <div>
              <label style={{ color: '#555', fontSize: 10 }}>Solution Code</label>
              <textarea
                value={pushForm.solution}
                onChange={e => setPushForm(f => ({ ...f, solution: e.target.value }))}
                rows={8}
                style={{
                  width: '100%', padding: '6px 10px', background: '#080810',
                  border: '1px solid #1a1a2e', borderRadius: 3, color: '#e0e0e0',
                  fontFamily: 'inherit', fontSize: 12, outline: 'none', resize: 'vertical',
                }}
              />
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <button onClick={doPush} style={{
                padding: '8px 20px', background: '#113311', border: '1px solid #00ff88',
                borderRadius: 4, color: '#00ff88', cursor: 'pointer',
                fontFamily: 'inherit', fontSize: 12, fontWeight: 600,
              }}>Push Solution</button>
              {pushMsg && <span style={{ color: pushMsg.startsWith('Error') ? '#ff4444' : '#00ff88', fontSize: 11 }}>{pushMsg}</span>}
            </div>
          </div>
        </div>
      )}

      {/* Results */}
      <div style={{ color: '#666', fontSize: 11, marginBottom: 8, fontWeight: 600 }}>
        {searchResults !== null ? `SEARCH RESULTS (${displayed.length})` : `ALL SOLUTIONS (${displayed.length})`}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {displayed.length === 0 && (
          <div style={{ color: '#333', fontSize: 12 }}>No solutions found</div>
        )}
        {displayed.map(s => (
          <SolutionCard key={s.id} solution={s} />
        ))}
      </div>
    </div>
  )
}
