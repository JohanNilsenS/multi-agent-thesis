// src/components/ChatInterface.tsx

import { useState, useRef, useEffect } from "react"
import "../styles/ChatInterface.css"

interface Message {
  content: string;
  source?: string;  // Gör source optional
  isUser?: boolean;
}

const HELP_MESSAGES = {
  git: {
    source: "GitAgent",
    content: `Här är vad jag kan hjälpa dig med:

1. Förklara kod:
   - git: explain [filnamn]
   - git: förklara [filnamn]
   - visa filen [filnamn]

2. Granska Pull Requests:
   - git: review PR #[nummer]
   - git: granska PR #[nummer]

3. Analysera Commits:
   - git: analyze commit [hash]
   - git: analysera commit [hash]

4. Visa projektöversikt:
   - git: project overview
   - git: visa översikt
   - visa projektöversikt

5. Kombinerade kommandon:
   - git: explain [filnamn] and review PR #[nummer]

Tips: Du kan skriva kommandona på både svenska och engelska!`
  },
  research: {
    source: "ResearchAgent",
    content: `Här är vad jag kan hjälpa dig med:

1. Sök information:
   - research: [sökfråga]
   - sök: [sökfråga]
   - hitta information om [ämne]

2. Specifika frågor:
   - research: vad är [ämne]?
   - förklara [ämne]
   - berätta om [ämne]

3. Kontext-baserad sökning:
   - research: hitta information om [ämne] i nuvarande filer
   - research: sök efter [ämne] i kodbasen

Tips: Du kan ställa frågor på både svenska och engelska!`
  }
};

export default function ChatInterface() {
  const [task, setTask] = useState("")
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const API_BASE = "http://localhost:5000"

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const getSourceColor = (source?: string) => {
    if (!source) return 'system-color';
    
    switch (source.toLowerCase()) {
      case 'gitagent':
        return 'git-color';
      case 'researchagent':
        return 'research-color';
      case 'supervisor':
        return 'supervisor-color';
      default:
        return 'system-color';
    }
  }

  const getSourceEmoji = (source?: string) => {
    if (!source) return '⚙️';
    
    switch (source.toLowerCase()) {
      case 'gitagent':
        return '💻';
      case 'researchagent':
        return '🔍';
      case 'supervisor':
        return '👨‍💼';
      default:
        return '⚙️';
    }
  }

  const handleHelp = (command: string) => {
    if (command.toLowerCase().includes('git: help')) {
      return HELP_MESSAGES.git;
    } else if (command.toLowerCase().includes('research: help')) {
      return HELP_MESSAGES.research;
    }
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!task.trim()) return

    // Lägg till användarens meddelande
    setMessages(prev => [...prev, { content: task, source: "User", isUser: true }])
    
    // Kolla om det är ett hjälpkommando
    const helpMessage = handleHelp(task);
    if (helpMessage) {
      setMessages(prev => [...prev, helpMessage]);
      setTask("");
      return;
    }

    setLoading(true)
    setTask("") // Rensa input efter att meddelandet skickats

    try {
      const res = await fetch(`${API_BASE}/api/ask-supervisor`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task }),
      })

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`);
      }

      const data = await res.json()
      setMessages(prev => [...prev, {
        content: data.content || 'Inget svar mottaget',
        source: data.source || 'System'
      }]);
    } catch (err) {
      console.error('Error in handleSubmit:', err);
      setMessages(prev => [...prev, { 
        content: err instanceof Error ? 
          `Ett fel uppstod: ${err.message}` : 
          'Ett okänt fel uppstod vid kommunikation med servern', 
        source: "System" 
      }]);
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chat-interface">
      <div className="messages-container">
        {messages.length === 0 && (
          <div className="welcome-message message agent-message">
            <p className="response-source supervisor-color">
              {getSourceEmoji("supervisor")} Supervisor
            </p>
            <p className="message-content">
              Välkommen! Jag kan hjälpa dig med olika uppgifter. Prova att skriva:
              - git: help
              - research: help
            </p>
          </div>
        )}
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.isUser ? 'user-message' : 'agent-message'}`}>
            {!msg.isUser && (
              <p className={`response-source ${getSourceColor(msg.source)}`}>
                {getSourceEmoji(msg.source)} {msg.source}
              </p>
            )}
            <p className="message-content">{msg.content}</p>
          </div>
        ))}
        <div ref={messagesEndRef} />
        {loading && (
          <div className="message agent-message">
            <p className="response-source supervisor-color">
              {getSourceEmoji("supervisor")} Supervisor
            </p>
            <p className="message-content typing-indicator">...</p>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="chat-input-form">
        <input
          id="task-input"
          type="text"
          value={task}
          onChange={(e) => setTask(e.target.value)}
          disabled={loading}
          placeholder="Skriv ditt meddelande här..."
        />
        <button type="submit" disabled={loading}>
          {loading ? "Tänker..." : "Skicka"}
        </button>
      </form>
    </div>
  )
}
