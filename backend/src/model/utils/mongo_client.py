from datetime import datetime, timedelta
from pymongo import MongoClient
import os
import asyncio
from src.model.vector_store.vector_store import VectorStore
from src.model.utils.embedding import get_embedding_from_llm
from src.model.utils.chunking import chunk_text
import uuid

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:supersecret@localhost:27017/")
client = MongoClient(MONGO_URI)

db = client["multiagent"]
collection = db["research_cache"]

# ✅ Initialize vector store from Mongo data
vector_store = VectorStore(collection)

async def save_research(query: str, content: str, embedding=None):
    """Asynkron funktion för att spara research i databasen"""
    try:
        # Beräkna embedding om den inte finns
        if embedding is None:
            embedding = await get_embedding_from_llm(query)

        # Skapa en partition_id för att gruppera relaterade chunks
        partition_id = str(uuid.uuid4())
        
        # Chunka innehållet
        chunks = chunk_text(content)
        
        # Spara varje chunk i databasen och vector store
        for i, chunk in enumerate(chunks):
            chunk_embedding = await get_embedding_from_llm(chunk)
            
            # Spara i MongoDB
            doc = {
                "query": query,
                "chunk": chunk,
                "chunk_index": i,
                "embedding": chunk_embedding,
                "partition_id": partition_id,
                "updated_at": datetime.utcnow()
            }
            collection.insert_one(doc)
            
            # Spara i vector store
            vector_store.add_entry(
                query=query,
                embedding=chunk_embedding,
                metadata={
                    "partition_id": partition_id,
                    "is_chunk": True,
                    "chunk_index": i
                }
            )

        # Uppdatera indexet
        vector_store.reindex()

        print(f"[MongoClient] Successfully saved research for query: {query} with {len(chunks)} chunks")
    except Exception as e:
        print(f"[MongoClient] Error saving research: {str(e)}")

async def find_research(query: str, max_age_days: int = 7) -> str:
    """Asynkron funktion för att söka efter research i databasen"""
    try:
        # Beräkna embedding för frågan
        embedding = await get_embedding_from_llm(query)
        # Sök efter matchande poster via FAISS
        results = vector_store.search(embedding, top_k=1, threshold=0.85)
        if results:
            best = results[0]
            metadata = best.get("metadata", {})
            partition_id = metadata.get("partition_id")
            if partition_id:
                # Hämta alla dokument med samma partition_id och sortera på chunk_index
                docs = list(collection.find({"partition_id": partition_id}).sort("chunk_index", 1))
                aggregated_content = "\n\n".join(d.get("chunk", "") for d in docs)
                # Eventuellt: även kolla om posten inte är för gammal
                if docs:
                    updated_at = docs[-1].get("updated_at")
                    if updated_at and datetime.utcnow() - updated_at > timedelta(days=max_age_days):
                        return ""
                return aggregated_content
            else:
                # Om inget partition_id finns, returnera det enskilda dokumentets innehåll
                return best.get("content", best.get("chunk", ""))
    except Exception as e:
        print(f"[MongoClient] Error during research search: {str(e)}")
    return ""
