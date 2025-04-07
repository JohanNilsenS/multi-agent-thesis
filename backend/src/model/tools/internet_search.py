# src/model/tools/internet_search.py

import requests
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import urllib.parse
import time
print("init")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )
}

def search_duckduckgo(query: str, max_results: int = 5) -> list[str]:
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max_results)
            return [
                f"{r['title']} - {r['body']}\n{r['href']}"
                for r in results
            ]
    except Exception as e:
        print(f"[DuckDuckGoSearch] Error: {e}")
        return [f"[Search Error] {e}"]