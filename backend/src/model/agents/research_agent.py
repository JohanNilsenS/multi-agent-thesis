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
import json

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
        
        # Lista över research-relaterade nyckelord och fraser
        research_keywords = [
            "research:",  # Standard prefix
            "sök",  # Sökningar
            "hitta",  # Hitta information
            "vad är",  # Frågor
            "förklara",  # Förklaringar
            "help",  # Hjälp på engelska
            "hjälp"  # Hjälp på svenska
        ]
        
        # Kontrollera om något av nyckelorden finns i uppgiften
        task_lower = task.lower()
        return any(keyword in task_lower for keyword in research_keywords)

    async def handle(self, task: str) -> dict:
        """Hantera en forskningsuppgift"""
        try:
            # Rensa prefix och extra mellanslag
            task = task.replace("research:", "").replace("sök:", "").replace("hitta:", "").strip()
            
            # Logga den rensade uppgiften
            self.log(f"Handling task: {task}")
            
            # Sök först i databasen
            self.log(f"Searching database for: {task}")
            db_result = await find_research(task)
            
            if db_result:
                self.log(f"Found results in database")
                return {
                    "source": "database",
                    "content": db_result
                }
            
            # Om inget hittades i databasen, sök på internet
            self.log("No results in database, searching internet...")
            search_results = await search_duckduckgo(task)
            
            if not search_results:
                return {
                    "source": "error",
                    "content": "Kunde inte hitta någon information om detta ämne."
                }
            
            # Filtrera och sammanfatta resultaten
            self.log("Filtrerar och sammanfattar sökresultat...")
            filtered_results = await self._filter_and_summarize_results(search_results, task)
            
            if not filtered_results:
                return {
                    "source": "error",
                    "content": "Kunde inte hitta relevant information om detta ämne."
                }
            
            # Spara resultaten i databasen
            self.log("Sparar resultat i databasen...")
            await save_research(task, filtered_results)
            
            return {
                "source": "internet",
                "content": filtered_results
            }
            
        except Exception as e:
            self.log(f"Error in handle: {str(e)}")
            return {
                "source": "error",
                "content": f"Ett fel uppstod: {str(e)}"
            }

    async def _filter_and_summarize_results(self, results: List[Dict], query: str) -> str:
        """Filtrerar och sammanfattar sökresultat."""
        self.log("Filtrerar och sammanfattar sökresultat...")
        
        # Konvertera resultaten till en strängrepresentation
        if isinstance(results, list):
            results_str = "\n".join(str(r) for r in results)
        else:
            results_str = str(results)
            
        self.log(f"Processed results: {results_str}")
        
        # Skapa en prompt för LLM att filtrera och sammanfatta
        prompt = f"""Filtrera och sammanfatta följande sökresultat för frågan: "{query}"

Sökresultat:
{results_str}

Skapa en sammanfattning som:
1. Besvarar frågan direkt och tydligt
2. Innehåller de viktigaste punkterna
3. Är välstrukturerad och lätt att läsa
4. Inkluderar källor där det är relevant
5. Filtrerar bort irrelevanta eller felaktiga uppgifter

Svara på svenska och var pedagogisk men teknisk."""

        self.log("Skickar filtrerings- och sammanfattningsprompt till LLM...")
        response = await self.llm.query(prompt)
        self.log("Fick svar från LLM")
        return response

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
        
        try:
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
            
        except Exception as e:
            self.log(f"Error saving to database: {str(e)}")
            # Vi fortsätter även om sparandet misslyckas - användaren får ändå sitt svar

