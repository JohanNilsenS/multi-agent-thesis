import faiss
import numpy as np
from pymongo.collection import Collection

def normalize_embedding(embedding: list[float]) -> np.ndarray:
    """Converts list to float32 numpy array and normalizes it."""
    arr = np.array(embedding).astype("float32")
    norm = np.linalg.norm(arr)
    if norm > 0:
        return arr / norm
    return arr

class VectorStore:
    def __init__(self, mongo_collection: Collection):
        self.mongo_collection = mongo_collection
        self.index = None
        self.mapping = {}  # maps FAISS index positions to a dict containing query and metadata
        self._initialize_index()

    def _initialize_index(self):
        print("[VectorStore] Loading embeddings from MongoDB...")
        embeddings = []
        self.mapping = {}  # Reset mapping
        processed_count = 0
        error_count = 0

        try:
            cursor = self.mongo_collection.find({"embedding": {"$exists": True}})
            total_docs = self.mongo_collection.count_documents({"embedding": {"$exists": True}})

            for i, doc in enumerate(cursor):
                try:
                    vec = doc.get("embedding")
                    if not vec or not isinstance(vec, list):
                        error_count += 1
                        continue

                    norm_vec = normalize_embedding(vec)
                    
                    if i > 0 and len(norm_vec) != len(embeddings[0]):
                        error_count += 1
                        continue

                    embeddings.append(norm_vec)
                    self.mapping[i] = {
                        "query": doc["query"],
                        "metadata": doc.get("metadata", {}),
                        "doc_id": str(doc["_id"])
                    }
                    processed_count += 1

                except Exception:
                    error_count += 1
                    continue

            if embeddings:
                dim = len(embeddings[0])
                self.index = faiss.IndexFlatIP(dim)
                self.index.add(np.array(embeddings))
                print(f"[VectorStore] Loaded {len(embeddings)} vectors into FAISS")
                if error_count > 0:
                    print(f"[VectorStore] Warning: {error_count} documents were skipped due to errors")
            else:
                print("[VectorStore] No valid embeddings found in DB")
                self.index = None

        except Exception as e:
            print(f"[VectorStore] Critical error during index initialization: {str(e)}")
            self.index = None
            raise

    def search(self, query_vector: list[float], top_k=5, threshold=0.7) -> list[dict]:
        if not self.index:
            return []

        try:
            norm_query = normalize_embedding(query_vector)
            query_np = np.array([norm_query])
            distances, indices = self.index.search(query_np, top_k)

            results = []
            for idx, sim in zip(indices[0], distances[0]):
                if idx == -1:  # FAISS returns -1 for not enough results
                    continue
                    
                if idx in self.mapping and sim >= threshold:
                    mapping_entry = self.mapping[idx]
                    doc = self.mongo_collection.find_one({"query": mapping_entry["query"]})
                    
                    if doc:
                        result = {
                            "query": doc["query"],
                            "content": doc.get("content", doc.get("chunk", "")),
                            "metadata": mapping_entry["metadata"],
                            "distance": float(sim)
                        }
                        results.append(result)

            return results

        except Exception as e:
            print(f"[VectorStore] Error during search: {str(e)}")
            return []

    def add_entry(self, query: str, embedding: list[float], metadata: dict = None):
        try:
            norm_embedding = normalize_embedding(embedding)
            
            if not self.index:
                dim = len(norm_embedding)
                self.index = faiss.IndexFlatIP(dim)
            
            idx = self.index.ntotal
            self.index.add(np.array([norm_embedding]))
            self.mapping[idx] = {"query": query, "metadata": metadata or {}}
            
        except Exception as e:
            print(f"[VectorStore] Error adding entry: {str(e)}")
            raise

    def reindex(self):
        try:
            self._initialize_index()
            print("[VectorStore] FAISS index reinitialized")
        except Exception as e:
            print(f"[VectorStore] Error during reindexing: {str(e)}")
            raise
