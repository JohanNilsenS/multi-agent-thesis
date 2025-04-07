import os
import requests

def get_embedding_from_llm(text: str) -> list[float]:
    EMBEDDING_API = os.getenv("EMBEDDING_API_URL")
    API_KEY = os.getenv("EMBEDDING_API_KEY")  # if needed

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    payload = {
        "input": text,
        "model": "embedding"  # Replace with your model name if needed
    }

    try:
        response = requests.post(EMBEDDING_API, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        # This might change depending on the API format
        return data["data"][0]["embedding"]

    except Exception as e:
        print(f"[Embedding Error] {e}")
        return []