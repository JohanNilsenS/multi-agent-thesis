# src/model/utils/file_indexer.py
import os
import json

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

def index_repo_files(repo_path: str, force_refresh=False) -> dict:
    os.makedirs("data", exist_ok=True)

    if os.path.exists(CACHE_FILE) and not force_refresh:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    file_index = {}
    gitignore = load_gitignore_patterns(repo_path)

    for root, _, files in os.walk(repo_path):
        for filename in files:
            rel_path = os.path.relpath(os.path.join(root, filename), repo_path)

            if is_ignored(rel_path, gitignore):
                continue

            try:
                with open(os.path.join(root, filename), "r", encoding="utf-8") as f:
                    content = f.read()
                    file_index[rel_path] = content
            except (UnicodeDecodeError, FileNotFoundError):
                continue

    # Save to cache
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(file_index, f, indent=2)

    return file_index