# src/model/agents/research_agent.py
import os
from typing import Dict, List
from ..base_agent import BaseAgent
from ..llm_client import LLMClient
from src.model.tools.internet_search import search_duckduckgo
from src.model.utils.mongo_client import find_research, save_research, collection, vector_store
from src.model.utils.embedding import get_embedding_from_llm
from src.model.utils.chunking import chunk_text
import uuid
from datetime import datetime

class ResearchAgent(BaseAgent):
    def __init__(self, llm: LLMClient):
        super().__init__("ResearchAgent")
        self.llm = llm
        self.debug = True

    def log(self, message: str):
        if self.debug:
            print(f"[ResearchAgent][DEBUG] {message}")

    def can_handle(self, task: str) -> bool:
        """Kontrollerar om agenten kan hantera uppgiften."""
        self.log(f"Checking if can handle task: {task}")
        # Kontrollera om kommandot börjar med "research:" eller innehåller sök-relaterade ord
        return task.startswith("research:") or any(word in task.lower() for word in ["sök", "hitta", "vad är", "förklara"])

    async def handle(self, task: str) -> dict:
        """Hanterar en uppgift asynkront."""
        self.log(f"Handling task: {task}")
        
        # Kontrollera om kommandot är tomt eller ogiltigt
        if not task or not task.strip():
            return {
                "source": self.name,
                "content": "Kunde inte hantera uppgiften. Ange ett giltigt kommando."
            }
            
        # Ta bort research: prefix om det finns
        if task.startswith("research:"):
            task = task[8:].strip()
            self.log(f"Removed research: prefix, new task: {task}")
            
            # Kontrollera om kommandot är tomt efter att prefixet tagits bort
            if not task:
                return {
                    "source": self.name,
                    "content": "Kunde inte hantera uppgiften. Ange ett giltigt kommando."
                }
        
        # Kontrollera om kommandot är ogiltigt
        if not self.can_handle(task):
            return {
                "source": self.name,
                "content": "Kunde inte hantera uppgiften. Ange ett giltigt kommando."
            }
        
        prompt = f"""
        Användaren vill veta: {task}
        
        Sök efter relevant information och ge ett tydligt svar som:
        1. Besvarar användarens fråga direkt
        2. Innehåller relevanta fakta och information
        3. Är välstrukturerat och lätt att förstå
        4. Inkluderar källor om möjligt
        
        Svara på svenska och var tydlig och pedagogisk.
        """
        
        self.log("Sending prompt to LLM...")
        response = await self.llm.query(prompt)
        self.log("Got response from LLM")
        return {
            "source": self.name,
            "content": response
        }

    async def search_database(self, query: str) -> str:
        """Söker i databasen efter tidigare research."""
        self.log(f"Searching database for: {query}")
        result = find_research(query, max_age_days=7)
        self.log(f"Found {len(result) if result else 0} results in database")
        return result

    def is_enough_info(self, result: str) -> bool:
        """Kontrollerar om resultatet innehåller tillräckligt med information."""
        return bool(result and len(result.strip()) > 50)

    async def save_to_database(self, query: str, result: str):
        """Sparar research-resultat i databasen."""
        self.log(f"Saving research for query: {query}")
        partition_id = str(uuid.uuid4())
        chunks = chunk_text(result)
        
        # Skapa en embedding för hela query först
        query_embedding = await get_embedding_from_llm(query)
        
        # Spara huvudquery i vector store
        vector_store.add_entry(
            query=query,
            embedding=query_embedding,
            metadata={"partition_id": partition_id, "is_query": True}
        )
        
        # Spara chunks
        for i, chunk in enumerate(chunks):
            chunk_embedding = await get_embedding_from_llm(chunk)
            doc = {
                "query": query,  # Spara original-queryn
                "chunk": chunk,
                "chunk_index": i,
                "embedding": chunk_embedding,
                "partition_id": partition_id,
                "updated_at": datetime.utcnow(),
                "metadata": {
                    "partition_id": partition_id,
                    "is_chunk": True,
                    "chunk_index": i
                }
            }
            collection.insert_one(doc)
            
            # Spara chunk i vector store med original-query
            vector_store.add_entry(
                query=query,
                embedding=chunk_embedding,
                metadata={
                    "partition_id": partition_id,
                    "is_chunk": True,
                    "chunk_index": i
                }
            )
        
        self.log("Reindexing vector store after adding new entries...")
        vector_store.reindex()

