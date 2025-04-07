import { useState } from "react"

interface Props {
  entry: {
    query: string
    content: string
    updated_at: string
  }
  onDelete: () => void
}

export default function KnowledgeItem({ entry, onDelete }: Props) {
  const [editing, setEditing] = useState(false)
  const [newContent, setNewContent] = useState(entry.content)
  const API_BASE = "http://localhost:5000"

  const handleDelete = () => {
    fetch(`${API_BASE}/api/knowledge/${encodeURIComponent(entry.query)}`, {
      method: "DELETE"
    }).then(res => {
      if (res.ok) onDelete()
    })
  }

  const handleSave = () => {
    fetch(`${API_BASE}/api/knowledge/${encodeURIComponent(entry.query)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: newContent })
    }).then(res => {
      if (res.ok) setEditing(false)
    })
  }

  return (
    <div className="knowledge-item">
      <strong>{entry.query}</strong>
      <span>Last updated: {new Date(entry.updated_at).toLocaleString()}</span>

      {editing ? (
        <>
          <textarea
            value={newContent}
            onChange={e => setNewContent(e.target.value)}
            rows={6}
            style={{ width: "100%", marginBottom: "0.5rem" }}
          />
          <button className="edit-button" onClick={handleSave}>Save</button>
          <button className="delete-button" onClick={() => setEditing(false)}>Cancel</button>
        </>
      ) : (
        <>
          <p className="preview">{entry.content.slice(0, 200)}...</p>
          <button className="edit-button" onClick={() => setEditing(true)}>Edit</button>
          <button className="delete-button" onClick={handleDelete}>Delete</button>
        </>
      )}
    </div>
  )
}
