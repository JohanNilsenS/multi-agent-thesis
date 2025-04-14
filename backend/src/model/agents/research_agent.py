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
        return task.startswith("research:") or "sök" in task.lower() or "hitta" in task.lower()

    async def handle(self, task: str) -> str:
        """Hanterar en uppgift asynkront."""
        self.log(f"Handling task: {task}")
        
        # Ta bort research: prefix om det finns
        if task.startswith("research:"):
            task = task[8:].strip()
            self.log(f"Removed research: prefix, new task: {task}")
        
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
        response = self.llm.query(prompt)
        self.log("Got response from LLM")
        return response

    def search_database(self, query: str) -> str:
        return find_research(query, max_age_days=7)

    def is_enough_info(self, result: str) -> bool:
        return bool(result and len(result.strip()) > 50)

    def save_to_database(self, query: str, result: str):
        partition_id = str(uuid.uuid4())
        chunks = chunk_text(result)
        
        # Skapa en embedding för hela query först
        query_embedding = get_embedding_from_llm(query)
        
        # Spara huvudquery i vector store
        vector_store.add_entry(
            query=query,
            embedding=query_embedding,
            metadata={"partition_id": partition_id, "is_query": True}
        )
        
        # Spara chunks
        for i, chunk in enumerate(chunks):
            chunk_embedding = get_embedding_from_llm(chunk)
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

