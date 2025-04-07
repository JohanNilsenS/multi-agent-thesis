# src/model/supervisor.py

from src.model.base_agent import BaseAgent
from src.model.agents.research_agent import ResearchAgent
from src.model.agents.git_agent import GitAgent
from src.model.llm_client import LLMClient
import os

class SupervisorAgent:
    def __init__(self):
        self.agents: list[BaseAgent] = []

        # Setup: shared in-memory DB and LLM client
        self.database = {}
        self.llm = LLMClient()

        # Register sub-agents
        self.register_agent(ResearchAgent(self.database, self.llm))

        # Set repo path (use current project root as default)
        repo_path = os.path.abspath(".")
        self.register_agent(GitAgent(repo_path, self.llm))

    def register_agent(self, agent: BaseAgent):
        self.agents.append(agent)

    def decide_agent(self, task: str) -> BaseAgent | None:
        prompt = (
            f"You are a routing assistant in a multi-agent system.\n"
            f"Here is the user task:\n\n\"{task}\"\n\n"
            "Based on this, which of the following agents should handle it?\n"
            "- ResearchAgent: answers questions or gathers external information\n"
            "- GitAgent: explains code, analyzes commits, explores repositories\n\n"
            "Respond with only the agent name: ResearchAgent or GitAgent."
        )
        decision = self.llm.query(prompt).strip()
        return next((a for a in self.agents if a.name == decision), None)

    def delegate(self, task: str, **kwargs):
        for agent in self.agents:
            if agent.can_handle(task):
                print(f"[Supervisor] Delegating to {agent.name} via keyword match")
                return agent.handle(task, **kwargs)

        # Fallback: use LLM to decide
        selected = self.decide_agent(task)
        if selected:
            print(f"[Supervisor] Delegating to {selected.name} via LLM decision")
            return selected.handle(task, **kwargs)

        raise ValueError(f"No agent found to handle task: {task}")
