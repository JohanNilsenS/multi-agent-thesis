# src/model/agents/git_agent.py

import subprocess
import os
import re
import ast
from .base_agent import BaseAgent
from ..llm_client import LLMClient
from ..utils.github_indexer import GitHubIndexer, create_github_indexer
from typing import Dict, List, Optional
import json
from pathlib import Path
from ..utils.github_indexer import create_github_indexer
from ..llm_client import LLMClient
import asyncio
import aiohttp

class GitAgent(BaseAgent):
    def __init__(self, llm: LLMClient):
        super().__init__(llm)
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
        return any(prefix in task.lower() for prefix in ["git:", "visa kod", "förklara kod", "pull request", "pr"])

    async def handle(self, task: str) -> str:
        """Hanterar en uppgift."""
        self.log(f"Handling task: {task}")
        
        # Ta bort git: prefix om det finns
        if task.lower().startswith("git:"):
            task = task[4:].strip()
            self.log(f"Removed git: prefix. New task: {task}")

        if "pull request" in task.lower() or "pr" in task.lower():
            return await self.review_pull_request(task)
        elif "visa filen" in task.lower():
            return await self.find_and_explain_file(task)
        else:
            return await self.analyze_code(task)

    async def review_pull_request(self, task: str) -> str:
        """Granskar en pull request."""
        self.log("Starting pull request review...")
        
        # Extrahera PR-nummer från uppgiften
        pr_number = None
        if "#" in task:
            pr_number = task.split("#")[-1].strip()
        elif "pr" in task.lower():
            parts = task.lower().split("pr")
            if len(parts) > 1:
                pr_number = parts[1].strip()
        
        if not pr_number:
            return "Kunde inte hitta pull request-nummer. Ange PR-nummer som 'git: review PR #3'"
        
        self.log(f"Reviewing PR #{pr_number}")
        
        # Hämta PR-information från GitHub
        headers = {
            "Authorization": f"token {os.getenv('GITHUB_AGENT_TOKEN')}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Hämta PR-detaljer
        pr_url = f"https://api.github.com/repos/{os.getenv('GITHUB_REPO_OWNER')}/{os.getenv('GITHUB_REPO_NAME')}/pulls/{pr_number}"
        async with aiohttp.ClientSession() as session:
            async with session.get(pr_url, headers=headers) as response:
                if response.status != 200:
                    return f"Kunde inte hämta pull request #{pr_number}. Status: {response.status}"
                
                pr_data = await response.json()
                
            # Hämta ändringar
            files_url = f"{pr_url}/files"
            async with session.get(files_url, headers=headers) as response:
                if response.status != 200:
                    return f"Kunde inte hämta ändringar för PR #{pr_number}. Status: {response.status}"
                
                files_data = await response.json()
        
        # Skapa en sammanfattning av ändringarna
        changes_summary = []
        for file in files_data:
            changes_summary.append(f"Fil: {file['filename']}")
            changes_summary.append(f"Status: {file['status']}")
            changes_summary.append(f"Ändringar: +{file['additions']} -{file['deletions']}")
            changes_summary.append("---")
        
        # Skapa prompt för LLM
        prompt = f"""Granska följande pull request:

Titel: {pr_data['title']}
Beskrivning: {pr_data['body']}

Ändringar:
{chr(10).join(changes_summary)}

Ge konstruktiv feedback på:
1. Kodkvalitet
2. Potentiella buggar
3. Förbättringsförslag
4. Överensstämmelse med kodningsstandarder

Var specifik och hänvisa till specifika rader eller filer där det är relevant."""

        self.log("Sending review prompt to LLM...")
        review_text = await self.llm.query(prompt)
        self.log("Received review response from LLM")

        # Posta kommentaren till GitHub med en ny session
        comments_url = f"{pr_url}/reviews"
        review_payload = {
            "body": review_text,
            "event": "COMMENT",
            "comments": []  # Vi kan lägga till specifika kommentarer på rader här om vi vill
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(comments_url, headers=headers, json=review_payload) as response:
                    if response.status == 200:
                        self.log("Successfully posted review to GitHub")
                        return f"Granskning postad till PR #{pr_number}:\n\n{review_text}"
                    else:
                        error_text = await response.text()
                        self.log(f"Failed to post review to GitHub. Status: {response.status}, Error: {error_text}")
                        return f"Kunde inte posta granskningen till GitHub. Status: {response.status}\n\nGranskningstext:\n{review_text}"
        except Exception as e:
            self.log(f"Error posting review to GitHub: {str(e)}")
            return f"Ett fel uppstod vid postning av granskningen till GitHub: {str(e)}\n\nGranskningstext:\n{review_text}"

    async def find_and_explain_file(self, task: str) -> str:
        """Hittar och förklarar en specifik fil."""
        self.log(f"Finding and explaining file for task: {task}")
        
        # Extrahera filnamnet från uppgiften
        filename = task.replace("visa filen", "").strip()
        if not filename:
            return "Vänligen ange ett filnamn att visa."
        
        self.log(f"Looking for file: {filename}")
        
        # Hitta relevanta filer
        relevant_files = self._get_relevant_files(filename)
        if not relevant_files:
            return f"Kunde inte hitta filen {filename}"
        
        self.log(f"Found relevant files: {relevant_files}")
        
        # Skapa prompt för LLM
        prompt = f"""Förklara följande fil:

{relevant_files}

Förklaringen ska innehålla:
1. Filens syfte och funktion
2. Viktiga klasser och funktioner
3. Viktiga beroenden
4. Eventuella säkerhetsaspekter

Var pedagogisk men teknisk i förklaringen."""
        
        self.log("Sending explanation prompt to LLM...")
        response = await self.llm.query(prompt)
        self.log("Received explanation response from LLM")
        
        return response

    async def analyze_code(self, task: str) -> str:
        """Analyserar kod i repositoryt."""
        self.log(f"Analyzing code for task: {task}")
        
        # Hitta relevanta filer
        relevant_files = self._get_relevant_files(task)
        if not relevant_files:
            return "Kunde inte hitta relevanta filer att analysera."
        
        self.log(f"Found relevant files for analysis: {relevant_files}")
        
        # Skapa prompt för LLM
        prompt = f"""Analysera följande kod:

{relevant_files}

Analysen ska innehålla:
1. Översikt av koden
2. Identifierade mönster och arkitektur
3. Potentiella förbättringar
4. Eventuella buggar eller säkerhetsproblem

Var teknisk och specifik i analysen."""
        
        self.log("Sending analysis prompt to LLM...")
        response = await self.llm.query(prompt)
        self.log("Received analysis response from LLM")
        
        return response

    def _get_relevant_files(self, query: str) -> str:
        """Hittar relevanta filer baserat på en fråga."""
        self.log(f"Getting relevant files for query: {query}")
        
        # Om det är en specifik fil, hitta den exakt
        if "visa filen" in query.lower():
            filename = query.replace("visa filen", "").strip()
            for path, content in self.file_index.items():
                if filename in path:
                    return f"=== {path} ===\n{content}"
        
        # Annars, hitta alla relevanta filer
        relevant_files = []
        for path, content in self.file_index.items():
            if query.lower() in path.lower() or query.lower() in content.lower():
                relevant_files.append(f"=== {path} ===\n{content}")
        
        self.log(f"Found {len(relevant_files)} relevant files")
        return "\n\n".join(relevant_files)

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
