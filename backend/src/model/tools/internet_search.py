# src/model/tools/internet_search.py

import requests
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import urllib.parse
import time
import asyncio
from typing import List

print("init")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )
}

async def search_duckduckgo(query: str, max_results: int = 5) -> List[str]:
    """
    Asynkron funktion för att söka med DuckDuckGo.
    """
    try:
        # Kör den synkrona DuckDuckGo-sökningen i en separat tråd för att inte blockera
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, lambda: _sync_search_duckduckgo(query, max_results))
        return results
    except Exception as e:
        print(f"[DuckDuckGoSearch] Error: {e}")
        return [f"[Search Error] {e}"]

def _sync_search_duckduckgo(query: str, max_results: int = 5) -> List[str]:
    """
    Synkron hjälpfunktion för DuckDuckGo-sökning.
    """
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=max_results)
        return [
            f"{r['title']} - {r['body']}\n{r['href']}"
            for r in results
        ]