# src/model/supervisor.py
from src.model.agents.research_agent import ResearchAgent
from src.model.agents.git_agent import GitAgent
from src.model.llm_client import LLMClient
from src.model.base_agent import BaseAgent
from typing import Dict, List, Optional
import os
import asyncio

class SupervisorAgent(BaseAgent):
    def __init__(self, llm: LLMClient):
        super().__init__("SupervisorAgent")
        self.llm = llm
        self.git_agent = GitAgent(llm)
        self.research_agent = ResearchAgent(llm)
        self.agents = {
            "GitAgent": self.git_agent,
            "ResearchAgent": self.research_agent
        }
        self.debug = True

    def log(self, message: str):
        if self.debug:
            print(f"[SupervisorAgent][DEBUG] {message}")

    async def initialize(self):
        """Initierar alla agenter."""
        self.log("Initializing SupervisorAgent...")
        await self.git_agent.initialize()
        self.log("SupervisorAgent initialized")

    def can_handle(self, task: str) -> bool:
        """Kontrollerar om någon agent kan hantera uppgiften."""
        self.log(f"Checking if can handle task: {task}")
        return self.git_agent.can_handle(task) or self.research_agent.can_handle(task)

    async def handle(self, task: str) -> str:
        """Hanterar en uppgift genom att delegera till rätt agent."""
        self.log(f"Handling task: {task}")
        
        # Initiera om nödvändigt
        if not hasattr(self, '_initialized'):
            await self.initialize()
            self._initialized = True
        
        # Bestäm vilken agent som ska hantera uppgiften
        if self.git_agent.can_handle(task):
            self.log("Delegating to GitAgent")
            return await self.git_agent.handle(task)
        elif self.research_agent.can_handle(task):
            self.log("Delegating to ResearchAgent")
            return await self.research_agent.handle(task)
        else:
            self.log("No suitable agent found")
            return "Ingen lämplig agent hittades för att hantera denna uppgift."

    def register_agent(self, agent: BaseAgent):
        self.agents[agent.name] = agent

    async def decide_agent(self, task: str) -> BaseAgent | None:
        # Först kontrollera om någon agent kan hantera uppgiften direkt
        for agent in self.agents.values():
            if agent.can_handle(task):
                return agent

        # Om ingen agent kan hantera det direkt, använd LLM för routing
        prompt = f"""
        Du är en routing-assistent i ett multi-agent system.
        Här är användarens uppgift:

        "{task}"

        Baserat på detta, vilken av följande agenter ska hantera det?

        - ResearchAgent: Svarar på frågor eller samlar in extern information från internet
        - GitAgent: Förklarar kod, analyserar commits, utforskar repositories, och gör code reviews

        Viktiga regler:
        1. Om uppgiften handlar om kod, filer, eller repository-struktur -> GitAgent
        2. Om uppgiften handlar om att hitta information på internet -> ResearchAgent
        3. Om uppgiften innehåller ord som "Förklara", "analyze", "code", "file", "git" -> GitAgent
        4. Om uppgiften handlar om att hitta fakta eller information som inte finns i koden -> ResearchAgent

        Svara endast med agentens namn: ResearchAgent eller GitAgent.
        """
        
        decision = await self.llm.query(prompt)
        self.log(f"LLM routing decision: {decision}")
        return self.agents.get(decision.strip())

    async def delegate(self, task: str, **kwargs):
        # Kontrollera om kommandot är tomt
        if not task or not task.strip():
            return {
                "source": self.name,
                "content": "Kunde inte hantera uppgiften. Ange ett giltigt kommando."
            }

        # Kontrollera om någon agent kan hantera uppgiften direkt
        for agent in self.agents.values():
            if agent.can_handle(task):
                self.log(f"Delegating to {agent.name} via keyword match")
                result = await agent.handle(task, **kwargs)
                return self._validate_semantic_match(task, result)
                
        # Om ingen agent kan hantera det direkt, använd LLM för routing
        selected = await self.decide_agent(task)
        if selected:
            self.log(f"Delegating to {selected.name} via LLM decision")
            result = await selected.handle(task, **kwargs)
            return self._validate_semantic_match(task, result)
            
        # Om ingen agent kunde hantera uppgiften
        return {
            "source": self.name,
            "content": "Kunde inte hantera uppgiften. Ange ett giltigt kommando."
        }

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
                research_agent = next((a for a in self.agents.values() if a.name == "ResearchAgent"), None)
                if research_agent:
                    return research_agent.handle(task, force_internet=True)
                return {"source": "supervisor", "content": "No relevant cached information and internet search is unavailable."}
        return result

    def get_selected_agent(self, task: str) -> str:
        """Returnerar namnet på den agent som skulle hantera en specifik uppgift."""
        # Kontrollera först om det finns ett prefix
        task_lower = task.lower()
        if task_lower.startswith("git:"):
            return "GitAgent"
        elif task_lower.startswith("research:"):
            return "ResearchAgent"
            
        # Om ingen agent kan hantera det direkt, använd LLM för routing
        prompt = f"""
        Du är en routing-assistent i ett multi-agent system.
        Här är användarens uppgift:

        "{task}"

        Baserat på detta, vilken av följande agenter ska hantera det?

        - ResearchAgent: Svarar på frågor eller samlar in extern information från internet
        - GitAgent: Förklarar kod, analyserar commits, utforskar repositories, och gör code reviews

        Viktiga regler:
        1. Om uppgiften handlar om kod, filer, eller repository-struktur -> GitAgent
        2. Om uppgiften handlar om att hitta information på internet -> ResearchAgent
        3. Om uppgiften innehåller ord som "Förklara", "analyze", "code", "file", "git" -> GitAgent
        4. Om uppgiften handlar om att hitta fakta eller information som inte finns i koden -> ResearchAgent
        5. Om uppgiften handlar om att förstå eller analysera kod, OAVSETT om det är en agent eller annan kod -> GitAgent

        Exempel på GitAgent-uppgifter:
        - "Förklara hur ResearchAgent fungerar"
        - "Visa mig koden i filen app.py"
        - "Analysera denna funktion"
        - "Hur fungerar denna klass"

        Exempel på ResearchAgent-uppgifter:
        - "Vad är väderleken i Stockholm?"
        - "Hitta information om Python"
        - "Vad är den senaste nyheten om AI?"
        - "Sök efter information om maskininlärning"

        Svara endast med agentens namn: ResearchAgent eller GitAgent.
        """
        
        decision = self.llm.query(prompt).strip()
        self.log(f"LLM routing decision: {decision}")
        return decision

