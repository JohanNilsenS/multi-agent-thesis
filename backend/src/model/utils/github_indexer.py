import os
import json
import aiohttp
import asyncio
from typing import Dict, List
from pathlib import Path

class GitHubIndexer:
    def __init__(self, token: str, owner: str, repo: str):
        self.token = token
        self.owner = owner
        self.repo = repo
        self.base_url = f"https://api.github.com/repos/{owner}/{repo}"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.cache_file = Path(".github_index_cache.json")
        self.debug = True
        self.session = None
        self.semaphore = None

    def log(self, message: str):
        if self.debug:
            print(f"[GitHubIndexer][DEBUG] {message}")

    async def _get_file_content(self, path: str) -> str:
        """Hämtar innehållet i en fil från GitHub asynkront."""
        if self.semaphore is None:
            self.semaphore = asyncio.Semaphore(10)
            
        async with self.semaphore:
            self.log(f"Fetching content for file: {path}")
            url = f"{self.base_url}/contents/{path}"
            try:
                async with self.session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        self.log(f"Successfully fetched content for {path}")
                        data = await response.json()
                        content = data["content"]
                        import base64
                        return base64.b64decode(content).decode('utf-8')
                    self.log(f"Failed to fetch content for {path}. Status code: {response.status}")
                    return ""
            except Exception as e:
                self.log(f"Error fetching {path}: {str(e)}")
                return ""

    async def _get_repo_structure(self) -> Dict[str, str]:
        """Hämtar hela repository-strukturen från GitHub asynkront."""
        self.log("Fetching repository structure from GitHub...")
        url = f"{self.base_url}/git/trees/main?recursive=1"
        
        try:
            async with self.session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    self.log(f"Failed to fetch repository structure. Status code: {response.status}")
                    return {}
                
                self.log("Successfully fetched repository structure")
                data = await response.json()
                tree = data["tree"]
                
                files_to_fetch = []
                for item in tree:
                    if item["type"] == "blob" and self._should_index(item["path"]):
                        files_to_fetch.append(item["path"])
                
                self.log(f"Found {len(files_to_fetch)} files to fetch")
                
                # Skapa en ny semaphore för varje anrop
                self.semaphore = asyncio.Semaphore(10)
                tasks = [self._get_file_content(path) for path in files_to_fetch]
                contents = await asyncio.gather(*tasks)
                
                file_index = {}
                for path, content in zip(files_to_fetch, contents):
                    if content:
                        file_index[path] = content
                        self.log(f"Added file to index: {path}")
                
                self.log(f"Indexed {len(file_index)} files from GitHub")
                return file_index
                
        except Exception as e:
            self.log(f"Error in _get_repo_structure: {str(e)}")
            return {}

    def _should_index(self, path: str) -> bool:
        """Bestämmer om en fil ska indexeras."""
        ignore_dirs = {'.git', '__pycache__', 'node_modules', 'venv', '.env', '.pytest_cache', 'data'}
        ignore_extensions = {'.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe', '.json', '.cache'}
        
        if any(part in ignore_dirs for part in path.split('/')):
            return False
            
        if any(path.endswith(ext) for ext in ignore_extensions):
            return False
            
        return True

    async def index_repo(self, force_refresh: bool = False) -> Dict[str, str]:
        """Indexerar hela repot från GitHub asynkront."""
        self.log(f"Starting repository indexing. Force refresh: {force_refresh}")
        
        if self.cache_file.exists() and not force_refresh:
            try:
                self.log("Loading from cache...")
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                    self.log(f"Loaded {len(cache)} files from cache")
                    return cache
            except (json.JSONDecodeError, FileNotFoundError) as e:
                self.log(f"Cache load failed: {str(e)}")
        
        # Skapa en ny session för varje indexering
        async with aiohttp.ClientSession() as self.session:
            self.log("Fetching files from GitHub...")
            file_index = await self._get_repo_structure()
            
            try:
                self.log("Saving to cache...")
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(file_index, f, ensure_ascii=False, indent=2)
                self.log("Cache saved successfully")
            except (IOError, OSError) as e:
                self.log(f"Cache save failed: {str(e)}")
            
            return file_index

def create_github_indexer() -> GitHubIndexer:
    """Skapar en GitHubIndexer med konfiguration från miljövariabler."""
    token = os.getenv("GITHUB_AGENT_TOKEN")
    owner = os.getenv("GITHUB_REPO_OWNER")
    repo = os.getenv("GITHUB_REPO_NAME")
    
    if not all([token, owner, repo]):
        raise ValueError("Missing required GitHub configuration. Please set GITHUB_AGENT_TOKEN, GITHUB_REPO_OWNER, and GITHUB_REPO_NAME environment variables.")
    
    return GitHubIndexer(token, owner, repo) 