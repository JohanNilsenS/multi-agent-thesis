from flask import Blueprint, jsonify, request
from src.model.utils.mongo_client import collection
from datetime import datetime, timedelta

bp = Blueprint("knowledge", __name__, url_prefix="/api")

@bp.route("/knowledge", methods=["GET"])
def get_knowledge():
    docs = collection.find({}, {"_id": 0, "query": 1, "content": 1, "updated_at": 1})
    return jsonify(list(docs))

@bp.route("/knowledge/<query>", methods=["PATCH"])
def update_knowledge(query):
    data = request.get_json()
    new_content = data.get("content")

    if not new_content:
        return jsonify({"error": "Missing content"}), 400

    result = collection.update_one(
        {"query": query},
        {
            "$set": {
                "content": new_content,
                "updated_at": datetime.utcnow()
            }
        }
    )

    if result.matched_count == 0:
        return jsonify({"error": "Entry not found"}), 404

    return jsonify({"message": "Entry updated"})

@bp.route("/knowledge/<query>", methods=["DELETE"])
def delete_knowledge(query):
    result = collection.delete_one({"query": query})

    if result.deleted_count == 0:
        return jsonify({"error": "Entry not found"}), 404

    return jsonify({"message": "Entry deleted"})