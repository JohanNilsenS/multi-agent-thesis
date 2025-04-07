# src/model/agents/research_agent.py

from src.model.base_agent import BaseAgent
from src.model.llm_client import LLMClient
from src.model.tools.internet_search import search_duckduckgo
from src.model.utils.mongo_client import find_research, save_research


class ResearchAgent(BaseAgent):
    def __init__(self, database: dict, llm_client: LLMClient):
        super().__init__("ResearchAgent")
        self.database = database
        self.llm = llm_client

    def can_handle(self, task: str) -> bool:
        return "research" in task.lower()

    def handle(self, task: str, **kwargs):
        query = kwargs.get("query", task)

        # Step 1: Check local database
        result = self.search_database(query)
        if self.is_enough_info(result):
            return {"source": "database", "content": result}

        # Step 2: Perform internet search
        search_results = search_duckduckgo(query, max_results=5)
        combined_snippets = "\n\n".join(search_results)

        prompt = (
            f"You are a research assistant. Based on the following web search results, "
            f"write a detailed summary about: '{query}'\n\n{combined_snippets}"
        )
        summary = self.llm.query(prompt)

        # Step 3: Save the summary to local DB (and eventually to vector store)
        self.save_to_database(query, summary)

        return {"source": "internet", "content": summary}

    def search_database(self, query: str) -> str:
        return find_research(query, max_age_days=7)

    def is_enough_info(self, result: str) -> bool:
        return bool(result and len(result.strip()) > 50)

    def save_to_database(self, query: str, result: str):
        save_research(query, result)
