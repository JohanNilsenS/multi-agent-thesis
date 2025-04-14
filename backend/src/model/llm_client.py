# src/model/llm_client.py

"""LLMClient hanterar kommunikationen med språkmodellen.

Denna modul tillhandahåller funktionalitet för att skicka frågor till och
ta emot svar från en språkmodell via API.
"""

import os
import aiohttp
import json
from typing import Optional, Dict, Any

class LLMClient:
    """En klient för att kommunicera med en språkmodell.
    
    Denna klass hanterar all kommunikation med språkmodellen via API,
    inklusive autentisering, frågeformatering och felhantering.
    
    Attribut:
        api_key (str): API-nyckeln för autentisering
        model_name (str): Namnet på språkmodellen att använda
        base_url (str): Bas-URL:en för API:et
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gpt-3.5-turbo",
        base_url: Optional[str] = None
    ):
        """Initierar en ny LLM-klient.
        
        Args:
            api_key (str, optional): API-nyckeln. Om None, hämtas från miljövariabeln.
            model_name (str, optional): Namnet på språkmodellen. Default är "gpt-3.5-turbo".
            base_url (str, optional): Bas-URL:en för API:et. Om None, hämtas från miljövariabeln.
        """
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.model_name = model_name
        self.base_url = base_url or os.getenv("LLM_ENDPOINT")
        
        if not self.api_key:
            raise ValueError("API-nyckel krävs. Ange den direkt eller via LLM_API_KEY.")
        if not self.base_url:
            raise ValueError("LLM endpoint krävs. Ange den direkt eller via LLM_ENDPOINT.")

    async def query(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """Skickar en fråga till språkmodellen och returnerar svaret.
        
        Args:
            prompt (str): Frågan att skicka till modellen
            max_tokens (int, optional): Maximalt antal tokens i svaret. Default är 1000.
            temperature (float, optional): Kreativitetsnivå (0-1). Default är 0.7.
            
        Returns:
            str: Modellens svar på frågan
            
        Raises:
            Exception: Om något går fel vid API-anropet
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(
                            f"API-anrop misslyckades med status {response.status}: {error_text}"
                        )
                    
                    response_data = await response.json()
                    return response_data["choices"][0]["message"]["content"]
                    
        except Exception as e:
            raise Exception(f"Fel vid kommunikation med språkmodellen: {str(e)}")
