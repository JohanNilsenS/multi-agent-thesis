import "../styles/About.css"

export default function About() {
  return (
    <div className="about-container">
      <h1>Multi-Agent Supervisor System</h1>
      <p>
        This project is a research-driven thesis exploring how intelligent agent systems can
        enhance software development workflows using Large Language Models (LLMs).
      </p>

      <p>
        At its core, the application is powered by a <strong>Supervisor Agent</strong> who manages and delegates tasks
        to a set of specialized agents, including:
      </p>

      <ul>
        <li>
          <strong>GitAgent</strong>: understands your codebase, explains functions, analyzes commits, and suggests improvements.
        </li>
        <li>
          <strong>ResearchAgent</strong>: searches a local database and the internet to find relevant information, summarize it, and save it for future reuse.
        </li>
      </ul>

      <p>
        Users can interact with the system via a clean web interface or (in the future) directly from Visual Studio Code.
        The goal is to make it feel like you're working with an AI-powered teammate — not just a tool.
      </p>

      <p>
        The Supervisor intelligently interprets your input and delegates tasks accordingly, with support for real-time
        web search and LLM summarization. The system is fully modular, extensible, and built without heavy dependencies like LangChain.
      </p>

      <p>
        You can view the full source code on GitHub:<br />
        👉 <a href="https://github.com/JohanNilsenS/multi-agent-thesis" target="_blank" rel="noreferrer">
          github.com/JohanNilsenS/multi-agent-thesis
        </a>
      </p>
    </div>
  )
}
