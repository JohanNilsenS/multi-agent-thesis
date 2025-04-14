# src/model/llm_client.py

import os
import requests
from dotenv import load_dotenv

load_dotenv()

class LLMClient:
    def __init__(self):
        self.base_url = os.getenv("LLM_ENDPOINT")
        self.api_key = os.getenv("LLM_API_KEY")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"  # Try "Api-Key" if this fails
        }

    def query(self, user_prompt: str, system_prompt: str = "You are a helpful assistant.", **kwargs) -> str:
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 2048,
            **kwargs
        }
        try:
            response = requests.post(self.base_url, json=payload, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except requests.RequestException as e:
            print(f"[LLMClient] Error: {e}")
            return f"Error querying LLM: {e}"
