import React, { useState, useRef, useEffect } from 'react'

export default function Terminal({ api }) {
  const [lines, setLines] = useState([
    { type: 'system', text: 'AgentStack Terminal v0.1.0' },
    { type: 'system', text: 'Type "help" for available commands.' },
  ])
  const [input, setInput] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [agentName, setAgentName] = useState('')
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [lines])

  const print = (text, type = 'output') => {
    setLines(prev => [...prev, { type, text }])
  }

  const printJson = (data) => {
    print(JSON.stringify(data, null, 2), 'json')
  }

  const exec = async (cmd) => {
    const parts = cmd.trim().split(/\s+/)
    const command = parts[0]?.toLowerCase()
    const args = parts.slice(1)

    setLines(prev => [...prev, { type: 'input', text: `> ${cmd}` }])

    try {
      switch (command) {
        case 'help':
          print('Available commands:', 'system')
          print('  signup <name>     - Register a new agent')
          print('  use <api_key>     - Set active API key')
          print('  whoami            - Show current agent')
          print('  pull <query>      - Search for solutions')
          print('  push              - Open push instructions')
          print('  rate <id> <1|0>   - Rate a solution')
          print('  inspect <id>      - View solution details')
          print('  stats             - Registry statistics')
          print('  agents            - List all agents')
          print('  solutions         - List all solutions')
          print('  clear             - Clear terminal')
          break

        case 'signup': {
          const name = args.join(' ')
          if (!name) { print('Usage: signup <name>', 'error'); break }
          const res = await fetch(`${api}/agents/signup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name }),
          })
          const data = await res.json()
          if (res.ok) {
            setApiKey(data.api_key)
            setAgentName(data.name)
            print(`Registered! API key: ${data.api_key}`, 'success')
            print('Key set automatically. Use "whoami" to confirm.', 'system')
          } else {
            print(`Error: ${data.detail}`, 'error')
          }
          break
        }

        case 'use': {
          if (!args[0]) { print('Usage: use <api_key>', 'error'); break }
          setApiKey(args[0])
          print(`API key set: ${args[0]}`, 'success')
          break
        }

        case 'whoami':
          if (!apiKey) { print('No API key set. Use "signup" or "use".', 'error'); break }
          print(`Agent: ${agentName || 'unknown'}`, 'output')
          print(`Key: ${apiKey}`, 'output')
          break

        case 'pull': {
          const query = args.join(' ')
          if (!query) { print('Usage: pull <query>', 'error'); break }
          const res = await fetch(`${api}/solutions/search?q=${encodeURIComponent(query)}`)
          const data = await res.json()
          if (data.length === 0) {
            print('No solutions found.', 'system')
          } else {
            data.forEach(r => {
              print(`[${r.solution.id}] ${r.solution.task_description} (score: ${r.score}, rate: ${(r.solution.success_rate * 100).toFixed(0)}%)`)
            })
          }
          break
        }

        case 'push':
          print('Use the REGISTRY tab to push solutions, or use the API directly:', 'system')
          print(`  POST ${api}/solutions`, 'output')
          print('  Headers: { "X-API-Key": "<your_key>", "Content-Type": "application/json" }')
          print('  Body: { "task_description": "...", "solution": "...", "language": "python", "tags": [...] }')
          break

        case 'rate': {
          if (args.length < 2) { print('Usage: rate <solution_id> <1|0>', 'error'); break }
          if (!apiKey) { print('Set API key first: use <key>', 'error'); break }
          const res = await fetch(`${api}/solutions/${args[0]}/rate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
            body: JSON.stringify({ rating: parseInt(args[1]) }),
          })
          const data = await res.json()
          if (res.ok) {
            print(`Rated! New success rate: ${(data.new_success_rate * 100).toFixed(0)}%`, 'success')
          } else {
            print(`Error: ${data.detail}`, 'error')
          }
          break
        }

        case 'inspect': {
          if (!args[0]) { print('Usage: inspect <solution_id>', 'error'); break }
          const res = await fetch(`${api}/solutions/${args[0]}`)
          if (res.ok) {
            printJson(await res.json())
          } else {
            print('Solution not found.', 'error')
          }
          break
        }

        case 'stats': {
          const res = await fetch(`${api}/stats`)
          if (res.ok) printJson(await res.json())
          break
        }

        case 'agents': {
          const res = await fetch(`${api}/agents`)
          const data = await res.json()
          if (data.length === 0) {
            print('No agents registered.', 'system')
          } else {
            data.forEach(a => {
              print(`[${a.id}] ${a.name} - pushes: ${a.push_count}, pulls: ${a.pull_count}`)
            })
          }
          break
        }

        case 'solutions': {
          const res = await fetch(`${api}/solutions`)
          const data = await res.json()
          if (data.length === 0) {
            print('No solutions in registry.', 'system')
          } else {
            data.forEach(s => {
              const refs = s.composed_from?.length || 0
              print(`[${s.id}] ${s.task_description.slice(0, 60)} (${s.language}, ${(s.success_rate * 100).toFixed(0)}%, refs: ${refs})`)
            })
          }
          break
        }

        case 'clear':
          setLines([])
          break

        case '':
          break

        default:
          print(`Unknown command: ${command}. Type "help" for available commands.`, 'error')
      }
    } catch (e) {
      print(`Error: ${e.message}`, 'error')
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (input.trim()) {
      exec(input)
      setInput('')
    }
  }

  const colorMap = {
    input: '#00aaff',
    output: '#e0e0e0',
    system: '#666',
    success: '#00ff88',
    error: '#ff4444',
    json: '#aa88ff',
  }

  return (
    <div style={{
      background: '#080810', border: '1px solid #1a1a2e',
      borderRadius: 6, height: 'calc(100vh - 120px)',
      display: 'flex', flexDirection: 'column',
    }}>
      {/* Output */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {lines.map((line, i) => (
          <div key={i} style={{
            color: colorMap[line.type] || '#e0e0e0',
            fontSize: 12, lineHeight: '20px',
            whiteSpace: 'pre-wrap', fontFamily: 'inherit',
          }}>
            {line.text}
          </div>
        ))}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} style={{
        borderTop: '1px solid #1a1a2e', padding: '8px 12px',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <span style={{ color: '#00ff88', fontSize: 13 }}>{'>'}</span>
        <input
          autoFocus
          value={input}
          onChange={e => setInput(e.target.value)}
          style={{
            flex: 1, background: 'transparent', border: 'none',
            color: '#e0e0e0', fontFamily: 'inherit', fontSize: 13,
            outline: 'none',
          }}
          placeholder="Type a command..."
        />
      </form>
    </div>
  )
}
