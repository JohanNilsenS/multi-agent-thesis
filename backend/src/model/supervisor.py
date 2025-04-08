# src/model/supervisor.py
from src.model.base_agent import BaseAgent
from src.model.agents.research_agent import ResearchAgent
from src.model.agents.git_agent import GitAgent
from src.model.llm_client import LLMClient
import os

class SupervisorAgent:
    def __init__(self):
        self.agents: list[BaseAgent] = []
        self.database = {}
        self.llm = LLMClient()
        self.debug = True  # Sätt till False för att stänga av debug-loggning

        # Registrera underagenter
        self.register_agent(ResearchAgent(self.database, self.llm))
        repo_path = os.path.abspath(".")
        self.register_agent(GitAgent(repo_path, self.llm))

    def log(self, message: str):
        if self.debug:
            print(f"[Supervisor][DEBUG] {message}")

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
        self.log(f"LLM routing decision: {decision}")
        return next((a for a in self.agents if a.name == decision), None)

    def delegate(self, task: str, **kwargs):
        for agent in self.agents:
            if agent.can_handle(task):
                self.log(f"Delegating to {agent.name} via keyword match")
                result = agent.handle(task, **kwargs)
                return self._validate_semantic_match(task, result)
        selected = self.decide_agent(task)
        if selected:
            self.log(f"Delegating to {selected.name} via LLM decision")
            result = selected.handle(task, **kwargs)
            return self._validate_semantic_match(task, result)
        raise ValueError(f"No agent found to handle task: {task}")

    def _validate_semantic_match(self, task: str, result):
        # Om resultatet inte är en dictionary, returnera det direkt.
        if not isinstance(result, dict):
            return result

        source = result.get("source", "")
        # Validera både för legacy result (source=="database") och semantiska matchningar.
        if source.startswith("semantic match:") or source == "database":
            # Använd ett prompt som beskriver att vi har hittat ett cachat svar och be LLM om en bekräftelse
            content = result.get("content", "")[:500]  # Förhandsvisning av innehållet
            prompt = (
                f"A cached research entry was found for the query '{task}':\n\n"
                f"Content Preview:\n{content}\n\n"
                "Is this cached content relevant to the current question? Respond only YES or NO."
            )
            self.log("Validating cached research entry via LLM...")
            verdict = self.llm.query(prompt).strip().lower()
            self.log(f"Semantic match validation verdict: {verdict}")
            if "yes" in verdict:
                return result
            else:
                self.log("Cached result rejected by LLM, forcing internet search.")
                research_agent = next((a for a in self.agents if a.name == "ResearchAgent"), None)
                if research_agent:
                    return research_agent.handle(task, force_internet=True)
                return {"source": "supervisor", "content": "No relevant cached information and internet search is unavailable."}
        return result

