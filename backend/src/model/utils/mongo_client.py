# src/model/utils/mongo_client.py
from datetime import datetime, timedelta
from pymongo import MongoClient
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:supersecret@localhost:27017/")
client = MongoClient(MONGO_URI)

db = client["multiagent"]
collection = db["research_cache"]


def save_research(query: str, content: str):
    collection.update_one(
        {"query": query},
        {
            "$set": {
                "content": content,
                "updated_at": datetime.utcnow()
            }
        },
        upsert=True
    )



def find_research(query: str, max_age_days: int = 7):
    doc = collection.find_one({"query": query})
    if not doc:
        return None

    updated_at = doc.get("updated_at")
    if updated_at and datetime.utcnow() - updated_at > timedelta(days=max_age_days):
        return None  # Too old

    return doc["content"]
