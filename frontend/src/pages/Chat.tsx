import "../styles/Chat.css"
import ChatInterface from "../components/ChatInterface"

export default function Chat() {
  return (
    <div className="chat-container">
      <div className="terminal">
        <ChatInterface />
      </div>
    </div>
  )
}
