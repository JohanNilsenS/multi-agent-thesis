from flask import Blueprint, jsonify, request
from src.model.utils.mongo_client import collection, vector_store    
from src.model.utils.chunking import chunk_text
from src.model.utils.embedding import get_embedding_from_llm
from datetime import datetime
import uuid

bp = Blueprint("knowledge", __name__, url_prefix="/api")

@bp.route("/knowledge", methods=["GET"])
def get_knowledge():
    docs = collection.find(
        {"chunk": {"$exists": True}}, 
        {"_id": 0, "query": 1, "chunk": 1, "chunk_index": 1, "partition_id": 1, "updated_at": 1}
    )

    grouped = {}
    for doc in docs:
        pid = doc["partition_id"]
        if pid not in grouped:
            grouped[pid] = {
                "query": doc["query"],
                "chunks": [],
                "updated_at": doc["updated_at"]
            }
        grouped[pid]["chunks"].append((doc["chunk_index"], doc["chunk"]))
        # Uppdatera till senaste updated_at om nyare
        if doc["updated_at"] > grouped[pid]["updated_at"]:
            grouped[pid]["updated_at"] = doc["updated_at"]

    results = []
    for pid, data in grouped.items():
        # Sortera chunks baserat på chunk_index
        sorted_chunks = sorted(data["chunks"], key=lambda x: x[0])
        # Skapa en array med objekt med chunk_index och content
        chunk_list = [{"chunk_index": idx, "content": cnt} for idx, cnt in sorted_chunks]
        results.append({
            "partition_id": pid,
            "query": data["query"],
            "updated_at": data["updated_at"],
            "chunks": chunk_list
        })

    return jsonify(results)

@bp.route("/knowledge/<query>", methods=["PATCH"])
def update_knowledge(query):
    data = request.get_json()
    new_content = data.get("content")

    if not new_content:
        return jsonify({"error": "Missing content"}), 400

    # Hämta partition_id för denna query
    first_doc = collection.find_one({"query": query})
    if not first_doc:
        return jsonify({"error": "Entry not found"}), 404

    partition_id = first_doc["partition_id"]

    # Ta bort gamla chunkar
    collection.delete_many({"partition_id": partition_id})

    # Chunka nytt content
    chunks = chunk_text(new_content)
    for i, chunk in enumerate(chunks):
        embedding = get_embedding_from_llm(chunk)
        doc = {
            "query": query,
            "chunk": chunk,
            "chunk_index": i,
            "embedding": embedding,
            "partition_id": partition_id,
            "updated_at": datetime.utcnow()
        }
        collection.insert_one(doc)
        vector_store.add_entry(f"{query} (chunk {i})", embedding)
        vector_store.reindex()

    return jsonify({"message": "Entry updated"})

@bp.route("/knowledge/<query>", methods=["DELETE"])
def delete_knowledge(query):
    doc = collection.find_one({"query": query})
    if not doc:
        return jsonify({"error": "Entry not found"}), 404

    partition_id = doc["partition_id"]
    result = collection.delete_many({"partition_id": partition_id})
    vector_store.reindex()
    return jsonify({"message": f"Deleted {result.deleted_count} chunks."})

@bp.route("/knowledge", methods=["DELETE"])
def delete_all_knowledge():
    result = collection.delete_many({})
    vector_store.reindex()
    return jsonify({"message": f"Deleted {result.deleted_count} entries"})

@bp.route("/upload-document", methods=["POST"])
def upload_document():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
        
    if not file.filename.endswith('.txt'):
        return jsonify({"error": "Only .txt files are supported"}), 400

    try:
        # Läs innehållet från filen
        content = file.read().decode('utf-8')
        
        # Skapa ett unikt partition_id för dokumentet
        partition_id = str(uuid.uuid4())
        
        # Chunka innehållet
        chunks = chunk_text(content)
        
        # Spara dokumentinformation
        doc_info = {
            "query": file.filename,  # Använd filnamnet som query
            "type": "document",
            "original_filename": file.filename,
            "total_chunks": len(chunks),
            "upload_date": datetime.utcnow(),
            "partition_id": partition_id
        }
        
        # Spara varje chunk
        for i, chunk in enumerate(chunks):
            # Skapa embedding för chunken
            chunk_embedding = get_embedding_from_llm(chunk)
            
            # Spara i MongoDB
            doc = {
                "query": file.filename,
                "chunk": chunk,
                "chunk_index": i,
                "embedding": chunk_embedding,
                "partition_id": partition_id,
                "updated_at": datetime.utcnow(),
                "metadata": {
                    "partition_id": partition_id,
                    "is_chunk": True,
                    "chunk_index": i,
                    "document_type": "uploaded_file",
                    "filename": file.filename
                }
            }
            collection.insert_one(doc)
            
            # Lägg till i vector store
            vector_store.add_entry(
                query=file.filename,
                embedding=chunk_embedding,
                metadata={
                    "partition_id": partition_id,
                    "is_chunk": True,
                    "chunk_index": i,
                    "document_type": "uploaded_file",
                    "filename": file.filename
                }
            )
        
        # Reindexera efter att alla chunks har lagts till
        vector_store.reindex()
        
        return jsonify({
            "message": "Document processed successfully",
            "filename": file.filename,
            "chunks_processed": len(chunks),
            "partition_id": partition_id
        })
        
    except Exception as e:
        return jsonify({"error": f"Error processing document: {str(e)}"}), 500
