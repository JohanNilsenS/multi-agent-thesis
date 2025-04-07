// src/components/ChatInterface.tsx

import { useState } from "react"
import "../styles/ChatInterface.css" // we'll create this next

export default function ChatInterface() {
  const [task, setTask] = useState("")
  const [response, setResponse] = useState("")
  const [loading, setLoading] = useState(false)
  const API_BASE = "http://localhost:5000"
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!task.trim()) return

    setLoading(true)
    setResponse("")

    try {
      const res = await fetch(`${API_BASE}/api/ask-supervisor`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task }),
      })

      const data = await res.json()
      setResponse(data.content || data.error || "No response")
    } catch (err) {
      setResponse("Error contacting supervisor.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chat-interface">
      <form onSubmit={handleSubmit}>
        <label htmlFor="task-input">&gt; Enter your task:</label>
        <input
          id="task-input"
          type="text"
          value={task}
          onChange={(e) => setTask(e.target.value)}
          disabled={loading}
          placeholder="e.g., why do cats purr?"
        />
        <button type="submit" disabled={loading}>
          {loading ? "Thinking..." : "Ask"}
        </button>
      </form>

      {response && (
        <div className="terminal-response">
          <p>{response}</p>
        </div>
      )}
    </div>
  )
}
