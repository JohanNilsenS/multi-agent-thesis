# src/model/llm_client.py

import os
import aiohttp
from typing import Optional

class LLMClient:
    def __init__(self):
        self.base_url = os.getenv("LLM_ENDPOINT")
        self.api_key = os.getenv("LLM_API_KEY")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        self.debug = True

    def log(self, message: str):
        if self.debug:
            print(f"[LLMClient][DEBUG] {message}")

    async def query(self, prompt: str) -> str:
        """Skickar en fråga till LLM och returnerar svaret."""
        self.log("Sending query to LLM...")
        payload = {
            "messages": [
                {"role": "system", "content": "Du är en hjälpsam AI-assistent som svarar på svenska."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, json=payload, headers=self.headers) as response:
                    response.raise_for_status()
                    data = await response.json()
                    self.log("Received response from LLM")
                    return data["choices"][0]["message"]["content"]
        except Exception as e:
            self.log(f"Error in LLM query: {str(e)}")
            return f"Ett fel uppstod vid kommunikation med LLM: {str(e)}"
