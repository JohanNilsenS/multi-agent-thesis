from datetime import datetime, timedelta
from pymongo import MongoClient
import os
from src.model.vector_store.vector_store import VectorStore
from src.model.utils.embedding import get_embedding_from_llm  # se till att denna är korrekt importerad

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:supersecret@localhost:27017/")
client = MongoClient(MONGO_URI)

db = client["multiagent"]
collection = db["research_cache"]

# ✅ Initialize vector store from Mongo data
vector_store = VectorStore(collection)

def save_research(query: str, content: str, embedding=None):
    update_data = {
        "content": content,
        "updated_at": datetime.utcnow()
    }
    if embedding:
        update_data["embedding"] = embedding

    collection.update_one(
        {"query": query},
        {"$set": update_data},
        upsert=True
    )

    if embedding:
        # Vid sparande av nya chunkade poster bör du se till att vector_store.add_entry anropas med metadata
        vector_store.add_entry(query, embedding, metadata={})
        
def find_research(query: str, max_age_days: int = 7) -> str:
    """
    Uppdaterad implementation som använder semantisk sökning via FAISS-indexet.
    Beräknar embedding för query, söker i vector_store, och om en match hittas
    så hämtas hela posten (alla chunkar) via partition_id och aggregeras.
    """
    # Beräkna embedding för frågan
    embedding = get_embedding_from_llm(query)
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
    return ""
