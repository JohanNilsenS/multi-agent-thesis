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
    
    const sourceLower = source.toLowerCase();
    switch (sourceLower) {
      case 'gitagent':
        return 'git-color';
      case 'researchagent':
        return 'research-color';
      case 'supervisor':
        return 'supervisor-color';
      case 'user':
        return 'user-color';
      case 'error':
        return 'error-color';
      default:
        return 'system-color';
    }
  }

  const getSourceEmoji = (source?: string) => {
    if (!source) return '⚙️';
    
    const sourceLower = source.toLowerCase();
    switch (sourceLower) {
      case 'gitagent':
        return '💻';
      case 'researchagent':
        return '🔍';
      case 'supervisor':
        return '👨‍💼';
      case 'user':
        return '👤';
      case 'error':
        return '⚠️';
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
    e.preventDefault();
    if (!task.trim()) return;

    const userMessage: Message = {
      content: task,
      isUser: true,
      source: "user"
    };
    setMessages(prev => [...prev, userMessage]);
    setTask("");
    setLoading(true);

    try {
      console.log("Sending request with task:", task);
      const response = await fetch(`${API_BASE}/api/ask-supervisor`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ task }),
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const data = await response.json();
      console.log("Received response:", data);
      
      // Hantera trädstruktur och gör filnamn klickbara
      if (data.content) {
        // Lista över vanliga filändelser
        const fileExtensions = ['.tsx', '.ts', '.js', '.jsx', '.html', '.css', '.py', '.md', '.json', '.yml', '.yaml'];
        
        // Funktion för att göra filnamn klickbara
        const makeFilesClickable = (text: string) => {
          // Dela upp texten i rader
          const lines = text.split('\n');
          
          // Processa varje rad
          return lines.map(line => {
            // Hitta filnamn med filändelser i raden
            const fileMatch = line.match(/([^\/\s]+(\.tsx|\.ts|\.js|\.jsx|\.html|\.css|\.py|\.md|\.json|\.yml|\.yaml))/);
            
            if (fileMatch) {
              const fileName = fileMatch[0];
              // Hitta hela sökvägen till filen
              const pathMatch = line.match(/([^│├└\s]+)\s*$/);
              if (pathMatch) {
                const fullPath = pathMatch[1].trim();
                // Ersätt bara filnamnet med en länk
                return line.replace(fileName, `<span class="file-link" data-command="git: explain ${fullPath}">${fileName}</span>`);
              }
            }
            return line;
          }).join('\n');
        };

        // Gör filnamn klickbara i svaret
        const processedContent = makeFilesClickable(data.content);
        
        // Uppdatera medan vi behåller HTML-formateringen
        setMessages(prev => [...prev, {
          content: processedContent,
          isUser: false,
          source: data.source || "unknown"
        }]);
      } else {
        setMessages(prev => [...prev, {
          content: "Inget svar mottaget",
          isUser: false,
          source: data.source || "unknown"
        }]);
      }
    } catch (error) {
      console.error('Error in handleSubmit:', error);
      setMessages(prev => [...prev, {
        content: error instanceof Error ? 
          `Ett fel uppstod: ${error.message}` : 
          'Ett okänt fel uppstod vid kommunikation med servern',
        isUser: false,
        source: "error"
      }]);
    } finally {
      setLoading(false);
    }
  };

  // Lägg till useEffect för att hantera fil-länkar
  useEffect(() => {
    const handleFileClick = async (event: Event) => {
      const target = event.currentTarget as HTMLElement;
      const command = target.getAttribute('data-command');
      if (command) {
        // Lägg till system-meddelande
        setMessages(prev => [...prev, {
          content: `Kör kommandot: ${command}`,
          source: 'system'
        }]);

        // Visa laddningsindikator
        setLoading(true);

        // Skicka kommandot direkt
        try {
          const response = await fetch(`${API_BASE}/api/ask-supervisor`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ task: command }),
          });

          if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
          }

          const data = await response.json();
          
          if (data.content) {
            setMessages(prev => [...prev, {
              content: data.content,
              isUser: false,
              source: data.source || "unknown"
            }]);
          }
        } catch (error) {
          console.error('Error in handleFileClick:', error);
          setMessages(prev => [...prev, {
            content: error instanceof Error ? 
              `Ett fel uppstod: ${error.message}` : 
              'Ett okänt fel uppstod vid kommunikation med servern',
            isUser: false,
            source: "error"
          }]);
        } finally {
          setLoading(false);
        }
      }
    };

    // Lägg till event listeners för alla fil-länkar
    const fileLinks = document.getElementsByClassName('file-link');
    for (let i = 0; i < fileLinks.length; i++) {
      fileLinks[i].addEventListener('click', handleFileClick);
    }

    // Städa upp event listeners när komponenten unmountas
    return () => {
      for (let i = 0; i < fileLinks.length; i++) {
        fileLinks[i].removeEventListener('click', handleFileClick);
      }
    };
  }, [messages]); // Kör useEffect när messages uppdateras

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
            <div 
              className="message-content"
              dangerouslySetInnerHTML={{ __html: msg.content }}
            />
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
