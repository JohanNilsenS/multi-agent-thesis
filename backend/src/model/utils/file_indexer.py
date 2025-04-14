# src/model/utils/file_indexer.py
import os
import json
from typing import Dict
import ast
from pathlib import Path

EXCLUDED_DIRS = {".git", ".venv", "__pycache__", "node_modules", "data"}
EXCLUDED_FILES = {".env"}
CACHE_FILE = "data/file_index.json"

def load_gitignore_patterns(repo_path: str) -> list:
    gitignore_path = os.path.join(repo_path, ".gitignore")
    patterns = []
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
    return patterns


def is_ignored(path: str, patterns: list) -> bool:
    parts = path.split(os.sep)
    
    if any(part in EXCLUDED_DIRS for part in parts):
        return True
    if os.path.basename(path) in EXCLUDED_FILES:
        return True
    for pattern in patterns:
        if pattern in path:
            return True
    return False

def index_repo_files(repo_path: str, force_refresh: bool = False) -> Dict[str, str]:
    """
    Indexerar alla filer i ett repository och returnerar en dictionary med filvägar som nycklar
    och filinnehåll som värden.
    
    Args:
        repo_path: Sökväg till repositoryt
        force_refresh: Om True, tvingar en ny indexering även om cache finns
        
    Returns:
        Dictionary med filvägar och innehåll
    """
    cache_file = Path(repo_path) / ".file_index_cache.json"
    
    # Om cache finns och vi inte tvingar refresh, ladda från cache
    if cache_file.exists() and not force_refresh:
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            # Om cache-filen är korrupt eller inte kan läsas, fortsätt med ny indexering
            pass
    
    file_index = {}
    ignore_dirs = {'.git', '__pycache__', 'node_modules', 'venv', '.env', '.pytest_cache', 'data'}
    ignore_extensions = {'.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe', '.json', '.cache'}
    
    # Ladda .gitignore-mönster
    gitignore_patterns = load_gitignore_patterns(repo_path)
    
    for root, dirs, files in os.walk(repo_path):
        # Filtrera bort ignorerade mappar
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, repo_path)
            
            # Kontrollera om filen ska ignoreras
            if is_ignored(rel_path, gitignore_patterns):
                continue
                
            # Kontrollera filändelse
            if any(rel_path.endswith(ext) for ext in ignore_extensions):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    file_index[rel_path] = content
            except (UnicodeDecodeError, PermissionError):
                # Hoppa över binära filer och filer vi inte har tillgång till
                continue
    
    # Spara till cache
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(file_index, f, ensure_ascii=False, indent=2)
    except (IOError, OSError) as e:
        print(f"Warning: Could not save file index cache: {e}")
    
    return file_index