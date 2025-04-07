import { useEffect, useState } from "react"
import "../styles/KnowledgeCenter.css"
import KnowledgeItem from "../components/KnowledgeItem"

interface KnowledgeEntry {
  query: string
  content: string
  updated_at: string
}

export default function KnowledgeCenter() {
  const [entries, setEntries] = useState<KnowledgeEntry[]>([])
  const [search, setSearch] = useState("")

  useEffect(() => {
    fetch("http://localhost:5000/api/knowledge")
      .then(res => res.json())
      .then(data => setEntries(data))
  }, [])

  const filtered = entries.filter(e =>
    e.query.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="knowledge-container">
      <h2>Knowledge Center</h2>
      <p>This is a list of research entries currently stored in the database:</p>
      <input
        type="text"
        placeholder="Search entries..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        style={{
          padding: "0.5rem",
          marginBottom: "1rem",
          width: "100%",
          fontSize: "1rem",
          border: "1px solid #ccc",
          borderRadius: "4px"
        }}
      />
      <div className="knowledge-list">
        {filtered.map((entry, i) => (
          <KnowledgeItem key={i} entry={entry} onDelete={() =>
            setEntries(prev => prev.filter(e => e.query !== entry.query))
          } />
        ))}
      </div>
    </div>
  )
}
