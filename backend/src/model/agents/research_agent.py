# src/model/agents/research_agent.py
import uuid
from datetime import datetime
from src.model.base_agent import BaseAgent
from src.model.llm_client import LLMClient
from src.model.tools.internet_search import search_duckduckgo
from src.model.utils.mongo_client import find_research, save_research, collection, vector_store
from src.model.utils.embedding import get_embedding_from_llm
from src.model.utils.chunking import chunk_text

class ResearchAgent(BaseAgent):
    def __init__(self, database: dict, llm_client: LLMClient):
        super().__init__("ResearchAgent")
        self.database = database
        self.llm = llm_client
        self.debug = True  # Sätt till False för att stänga av debug-loggning

    def log(self, message: str):
        if self.debug:
            print(f"[ResearchAgent][DEBUG] {message}")

    def can_handle(self, task: str) -> bool:
        return "research" in task.lower()

    def handle(self, task: str, force_internet: bool = False, **kwargs):
        query = kwargs.get("query", task)
        self.log(f"Handling query: {query} | force_internet={force_internet}")

        if force_internet:
            self.log("Force internet search flag true. Bypassing cached search.")
        else:
            embedding = get_embedding_from_llm(query)
            self.log(f"Calculating embedding for query: {query}")
            
            # Sök efter liknande queries och chunks
            similar = vector_store.search(embedding, top_k=5, threshold=0.70)
            self.log(f"Found {len(similar)} potential matches")
            
            if similar:
                # Gruppera resultat efter partition_id
                grouped_results = {}
                for result in similar:
                    if not result.get("content"):
                        continue
                        
                    pid = result.get("metadata", {}).get("partition_id")
                    if not pid:
                        continue
                        
                    if pid not in grouped_results:
                        grouped_results[pid] = {
                            "query": result["query"],
                            "chunks": [],
                            "max_similarity": result["distance"]
                        }
                    
                    # Om detta är en chunk, lägg till den
                    if result.get("metadata", {}).get("is_chunk"):
                        grouped_results[pid]["chunks"].append({
                            "content": result["content"],
                            "similarity": result["distance"],
                            "chunk_index": result.get("metadata", {}).get("chunk_index", 0)
                        })
                        # Uppdatera max similarity om denna chunk har högre
                        grouped_results[pid]["max_similarity"] = max(
                            grouped_results[pid]["max_similarity"],
                            result["distance"]
                        )
                
                if grouped_results:
                    # Sortera grupperna efter högsta similarity
                    sorted_groups = sorted(
                        grouped_results.items(),
                        key=lambda x: x[1]["max_similarity"],
                        reverse=True
                    )
                    
                    # Sammanställ innehåll för LLM
                    contents = []
                    for pid, group in sorted_groups:
                        # Sortera chunks efter index
                        sorted_chunks = sorted(group["chunks"], key=lambda x: x["chunk_index"])
                        full_content = " ".join(chunk["content"] for chunk in sorted_chunks)
                        contents.append({
                            "content": full_content,
                            "query": group["query"],
                            "distance": group["max_similarity"]
                        })
                    
                    if contents:
                        # Första steget: Identifiera relevant information
                        identification_prompt = (
                            f"Du har fått följande innehåll från olika källor. "
                            f"Baserat på frågan '{query}', välj ut och markera det mest relevanta innehållet.\n\n"
                            f"Källor:\n"
                        )
                        for i, content in enumerate(contents, 1):
                            identification_prompt += (
                                f"{i}. Query: {content['query']}\n"
                                f"Content: {content['content']}\n"
                                f"Similarity: {content['distance']}\n\n"
                            )
                        
                        identification_prompt += (
                            f"\nVälj den mest relevanta informationen för frågan '{query}'. "
                            f"Om ingen av källorna innehåller relevant information, svara 'NO_RELEVANT_INFO'."
                        )
                        
                        relevant_info = self.llm.query(identification_prompt)
                        
                        if "NO_RELEVANT_INFO" not in relevant_info:
                            # Andra steget: Förfina och anpassa svaret
                            refinement_prompt = (
                                f"Besvara frågan '{query}' baserat på följande information:\n{relevant_info}\n\n"
                                f"Ge ett kort och koncist svar. Undvik onödig artighet eller utfyllnad. "
                                f"Om informationen är osäker, nämn det kortfattat."
                            )
                            
                            refined_answer = self.llm.query(refinement_prompt)
                            return {
                                "source": "semantic search",
                                "content": refined_answer,
                                "confidence": sorted_groups[0][1]["max_similarity"]
                            }

            self.log("No relevant cached results found, performing internet search.")

        # Om force_internet är True, eller om ingen relevant träff hittats ovan:
        self.log("Performing internet search.")
        search_results = search_duckduckgo(query, max_results=5)
        self.log(f"Internet search results: {search_results}")
        combined_snippets = "\n\n".join(search_results)
        
        # Använd samma typ av förfining för internetsökningar
        initial_prompt = (
            f"Sammanfatta följande sökresultat för att besvara frågan: '{query}'\n\n{combined_snippets}\n\n"
            f"Ge en kort och koncis sammanfattning."
        )
        initial_summary = self.llm.query(initial_prompt)
        
        refinement_prompt = (
            f"Besvara frågan '{query}' baserat på följande information:\n{initial_summary}\n\n"
            f"Ge ett kort och koncist svar. Undvik onödig artighet eller utfyllnad. "
            f"Om informationen är osäker, nämn det kortfattat."
        )
        
        refined_answer = self.llm.query(refinement_prompt)
        self.save_to_database(query, refined_answer)
        return {"source": "internet", "content": refined_answer}

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

