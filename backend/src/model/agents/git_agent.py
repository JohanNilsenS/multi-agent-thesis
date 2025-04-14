# src/model/agents/git_agent.py

import subprocess
import os
import re
import ast
from src.model.base_agent import BaseAgent
from src.model.llm_client import LLMClient
from src.model.utils.github_indexer import create_github_indexer
from typing import Dict, List, Optional
import json
from pathlib import Path
from ..utils.github_indexer import create_github_indexer
from ..llm_client import LLMClient
import asyncio

class GitAgent(BaseAgent):
    def __init__(self, llm: LLMClient):
        super().__init__("GitAgent")
        self.llm = llm
        self.github_token = os.getenv("GITHUB_AGENT_TOKEN")
        self.repo_name = os.getenv("GITHUB_REPO_NAME")
        self.repo_owner = os.getenv("GITHUB_REPO_OWNER")
        self.github_indexer = create_github_indexer()
        self.file_index = {}
        self.debug = True

    def log(self, message: str):
        if self.debug:
            print(f"[GitAgent][DEBUG] {message}")

    async def initialize(self):
        """Initierar agenten genom att hämta repository-data."""
        self.log("Initializing GitAgent...")
        self.file_index = await self.github_indexer.index_repo()
        self.log(f"Initialized with {len(self.file_index)} files")

    def can_handle(self, task: str) -> bool:
        """Kontrollerar om agenten kan hantera uppgiften."""
        self.log(f"Checking if can handle task: {task}")
        return task.startswith("git:") or "kod" in task.lower() or "fil" in task.lower()

    async def handle(self, task: str) -> str:
        """Hanterar en uppgift asynkront."""
        self.log(f"Handling task: {task}")
        
        # Om vi inte har någon data än, initiera
        if not self.file_index:
            await self.initialize()
        
        # Ta bort git: prefix om det finns
        if task.startswith("git:"):
            task = task[4:].strip()
            self.log(f"Removed git: prefix, new task: {task}")
        
        # Kolla om det är en direkt fråga om att visa kod
        if "visa" in task.lower() and "kod" in task.lower() and "fil" in task.lower():
            self.log("Detected direct code viewing request")
            # Extrahera filnamn
            filename = None
            if "filen" in task.lower():
                parts = task.lower().split("filen")
                if len(parts) > 1:
                    filename = parts[1].strip()
            elif "i" in task.lower():
                parts = task.lower().split("i")
                if len(parts) > 1:
                    filename = parts[1].strip()
            
            if filename:
                self.log(f"Looking for specific file: {filename}")
                # Tvinga refresh från GitHub för att få senaste versionen
                self.file_index = await self.github_indexer.index_repo(force_refresh=True)
                
                for path, content in self.file_index.items():
                    if filename in path:
                        self.log(f"Found file: {path}")
                        return {
                            "source": "git_agent",
                            "content": f"```python\n{content}\n```",
                            "type": "code"
                        }
                return {
                    "source": "git_agent",
                    "content": f"Kunde inte hitta filen {filename}",
                    "type": "error"
                }
        
        # Analysera uppgiften och bestäm vilken metod som ska användas
        if "förklara" in task.lower() or "vad gör" in task.lower():
            self.log("Detected explanation request")
            return await self.find_and_explain_file(task)
        else:
            self.log("Detected code analysis request")
            return await self.analyze_code(task)

    async def analyze_code(self, task: str) -> str:
        """Analyserar kod baserat på användarens fråga asynkront."""
        self.log(f"Starting code analysis for task: {task}")
        relevant_files = self._get_relevant_files(task)
        
        if not relevant_files:
            self.log("No relevant files found")
            return "Kunde inte hitta någon relevant kod för din fråga."
        
        self.log(f"Found relevant files, preparing prompt...")
        prompt = f"""
        Användaren vill veta: {task}
        
        Här är den relevanta koden:
        {relevant_files}
        
        Analysera och förklara:
        1. Vad koden gör
        2. Hur den fungerar
        3. Viktiga delar och funktioner
        4. Eventuella samband med andra delar av systemet
        
        Svara på svenska och var tydlig och pedagogisk.
        """
        
        self.log("Sending prompt to LLM...")
        response = self.llm.query(prompt)
        self.log("Got response from LLM")
        return response

    async def find_and_explain_file(self, task: str) -> str:
        """Hittar och förklarar specifika filer baserat på användarens fråga asynkront."""
        try:
            self.log(f"Starting find_and_explain_file for task: {task}")
            
            # Extrahera filnamn från frågan
            filename = None
            if "filen" in task.lower():
                parts = task.lower().split("filen")
                if len(parts) > 1:
                    filename = parts[1].strip()
                    self.log(f"Extracted filename: {filename}")
            
            if filename:
                # Om vi har ett specifikt filnamn, tvinga refresh från GitHub
                self.log(f"Looking for specific file: {filename}")
                self.log("Forcing refresh from GitHub for specific file...")
                self.file_index = await self.github_indexer.index_repo(force_refresh=True)
                
                for path, content in self.file_index.items():
                    if filename in path:
                        self.log(f"Found file: {path}")
                        return await self._explain_single_file(path, content)
            
            # Om ingen specifik fil hittades, använd den generella sökningen
            self.log("No specific file found, using general search")
            relevant_files = self._get_relevant_files(task)
            if not relevant_files:
                self.log("No relevant files found")
                return "Kunde inte hitta några relevanta filer för din fråga."
            
            self.log(f"Found relevant files, preparing prompt...")
            prompt = f"""
            Användaren vill förstå: {task}
            
            Här är de relevanta filerna:
            {relevant_files}
            
            Förklara:
            1. Vad varje fil gör
            2. Hur filerna hänger ihop
            3. Viktiga funktioner eller klasser
            4. Hur de används i systemet
            
            Svara på svenska och var tydlig och pedagogisk.
            """
            
            self.log("Sending prompt to LLM...")
            response = self.llm.query(prompt)
            self.log("Got response from LLM")
            return response
        except Exception as e:
            self.log(f"Error in find_and_explain_file: {str(e)}")
            return f"Ett fel uppstod vid sökning av filer: {str(e)}"

    async def _explain_single_file(self, path: str, content: str) -> str:
        """Förklarar en enskild fil asynkront."""
        self.log(f"Explaining single file: {path}")
        prompt = f"""
        Förklara följande fil: {path}
        
        Innehåll:
        {content}
        
        Förklara:
        1. Vad filen gör
        2. Viktiga funktioner eller klasser
        3. Hur den används i systemet
        4. Eventuella samband med andra delar
        
        Svara på svenska och var tydlig och pedagogisk.
        """
        
        self.log("Sending prompt to LLM...")
        response = self.llm.query(prompt)
        self.log("Got response from LLM")
        return response

    def _get_relevant_files(self, task: str) -> str:
        """Hittar relevanta filer baserat på uppgiften."""
        self.log(f"Getting relevant files for task: {task}")
        relevant_files = []
        
        # Sök efter filer som matchar uppgiften
        for path, content in self.file_index.items():
            if any(keyword in path.lower() for keyword in task.lower().split()):
                relevant_files.append(f"=== {path} ===\n{content}\n")
        
        return "\n".join(relevant_files) if relevant_files else ""

    def summarize_latest_commit(self):
        diff = self._get_latest_commit_diff()
        prompt = f"Review and summarize this Git commit:\n\n{diff}"
        return self.llm.query(prompt)

    def project_overview(self):
        structure = self._get_directory_structure()
        prompt = f"This is the file structure of a codebase:\n\n{structure}\n\nWhat is this project likely doing?"
        return self.llm.query(prompt)

    def suggest_improvements(self):
        structure = self._get_directory_structure()
        prompt = f"Here is the project structure:\n\n{structure}\n\nSuggest possible improvements to structure or code quality."
        return self.llm.query(prompt)
    
    def print_file_index_preview(self, limit: int = 3, chars: int = 300):
        print(f"\n[GitAgent] Previewing first {limit} indexed files:\n")
        count = 0
        for path, content in self.file_index.items():
            print(f"--- {path} ---")
            print(content[:chars] + ("..." if len(content) > chars else ""))
            print()
            count += 1
            if count >= limit:
                break

        if count == 0:
            print("No files were indexed.")


    def reindex_files(self):
        """Uppdaterar filindexeringen från GitHub."""
        self.file_index = self.github_indexer.index_repo(force_refresh=True)
        print("[GitAgent] File index refreshed from GitHub and cached.")

    def explain_function(self, function_name: str) -> str:
            for path, content in self.file_index.items():
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef) and node.name == function_name:
                            # Get full source code lines
                            lines = content.splitlines()
                            start_line = node.lineno - 1
                            end_line = getattr(node, 'end_lineno', start_line + 1)

                            # Extract function code block
                            function_code = "\n".join(lines[start_line:end_line])

                            prompt = (
                                f"Here's a Python function called `{function_name}` from the file `{path}`:\n\n"
                                f"```python\n{function_code.strip()}\n```\n\n"
                                "Please explain in detail what this function does."
                            )
                            return self.llm.query(prompt)
                except SyntaxError:
                    continue

            return f"Function `{function_name}` not found in indexed files."
    
    def list_all_functions(self) -> list[dict]:
        functions = []

        for path, content in self.file_index.items():
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        functions.append({
                            "name": node.name,
                            "path": path
                        })
            except SyntaxError:
                continue

        return functions

    def _get_latest_commit_diff(self) -> str:
        try:
            result = subprocess.run(
                ["git", "show", "--stat", "--unified=1"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"[GitAgent Error] Could not retrieve commit diff:\n{e.stderr or str(e)}"


    def _get_directory_structure(self) -> str:
        output = []
        for root, dirs, files in os.walk(self.repo_path):
            depth = root.replace(self.repo_path, "").count(os.sep)
            indent = "  " * depth
            output.append(f"{indent}{os.path.basename(root)}/")
            for f in files:
                output.append(f"{indent}  {f}")
        return "\n".join(output)
