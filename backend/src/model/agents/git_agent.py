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
import requests
import logging

class GitAgent(BaseAgent):
    def __init__(self, llm: LLMClient):
        super().__init__("GitAgent")
        self.llm = llm
        self.debug = True
        self.name = "GitAgent"
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.info("GitAgent initialiserad")
        self.github_token = os.getenv("GITHUB_AGENT_TOKEN")
        self.repo_name = os.getenv("GITHUB_REPO_NAME")
        self.repo_owner = os.getenv("GITHUB_REPO_OWNER")
        self.github_indexer = create_github_indexer()
        self.file_index = {}

    def log(self, message: str):
        if self.debug:
            print(f"[GitAgent][DEBUG] {message}")

    async def initialize(self):
        """Initierar agenten genom att hämta repository-data."""
        self.logger.info("Initializing GitAgent...")
        self.file_index = await self.github_indexer.index_repo()
        self.logger.info(f"Initialized with {len(self.file_index)} files")

    def can_handle(self, task: str) -> bool:
        """Kontrollera om agenten kan hantera uppgiften."""
        self.logger.debug(f"Kontrollerar om GitAgent kan hantera uppgift: {task}")
        
        # Lista över git-relaterade nyckelord och fraser
        git_keywords = [
            "git:",  # Standard prefix
            "visa fil",  # Visa filer
            "visa koden",  # Visa kod
            "förklara fil",  # Förklara filer
            "förklara koden",  # Förklara kod
            "pull request",  # PR-relaterat
            "pr",  # PR-förkortning
            "commit",  # Commit-relaterat
            "ändring",  # Ändringar
            "kod",  # Kod-relaterat
            "repository",  # Repository-relaterat
            "repo"  # Repo-förkortning
        ]
        
        # Kontrollera om något av nyckelorden finns i uppgiften
        task_lower = task.lower()
        return any(keyword in task_lower for keyword in git_keywords)

    async def handle(self, task: str) -> dict:
        """Hanterar en uppgift asynkront."""
        self.log(f"Handling task: {task}")
        
        # Initiera om nödvändigt
        if not hasattr(self, '_initialized'):
            await self.initialize()
            self._initialized = True
            
        # Ta bort git: prefix om det finns
        if task.startswith("git:"):
            task = task[4:].strip()
            self.log(f"Removed git: prefix, new task: {task}")
            
        # Kontrollera om kommandot är tomt efter att prefixet tagits bort
        if not task:
            return {
                "source": self.name,
                "content": "Kunde inte hantera git-kommandot. Ange ett kommando som 'git: explain app.py'"
            }
            
        # Hantera olika typer av kommandon
        task_lower = task.lower().strip()

        # Kontrollera först om det är help-kommando
        if task_lower == "help":
            return {
                "source": self.name,
                "content": """Här är vad jag kan hjälpa dig med:

1. Förklara kod:
   - git: explain [filnamn]
   - git: förklara [filnamn]
   - visa filen [filnamn]

2. Granska Pull Requests:
   - git: review PR #[nummer]
   - git: granska PR #[nummer]

3. Analysera Commits:
   - git: analyze commit [hash]
   - git: analysera commit [hash]

4. Visa projektöversikt:
   - git: project overview
   - git: visa översikt
   - git: projektöversikt
   - git: struktur

5. Kombinerade kommandon:
   - git: explain [filnamn] and review PR #[nummer]

Tips: Du kan skriva kommandona på både svenska och engelska!"""
            }

        # Kontrollera först om det är en projektöversikt som efterfrågas
        if any(keyword in task_lower for keyword in ["project overview", "visa översikt", "projektöversikt", "struktur"]):
            return await self.project_overview()
            
        if "explain" in task_lower or "förklara" in task_lower or "visa" in task_lower:
            return await self.handle_explain(task)
        elif "review" in task_lower or "granska" in task_lower:
            result = await self.review_pull_request(task)
            return {
                "source": self.name,
                "content": result
            }
        elif "analyze" in task_lower or "analysera" in task_lower:
            result = await self.analyze_commit(task)
            return {
                "source": self.name,
                "content": result
            }
        else:
            return {
                "source": self.name,
                "content": "Kunde inte hantera git-kommandot. Prova 'git: help' för att se tillgängliga kommandon."
            }

    async def review_pull_request(self, task: str) -> dict:
        """Granskar en pull request."""
        self.logger.info("Starting pull request review...")
        
        # Extrahera PR-nummer från uppgiften
        pr_number = None
        if "#" in task:
            pr_number = task.split("#")[-1].strip()
        elif "pr" in task.lower():
            parts = task.lower().split("pr")
            if len(parts) > 1:
                pr_number = parts[1].strip()
        
        if not pr_number:
            return {
                "source": self.name,
                "content": "Kunde inte hitta pull request-nummer. Ange PR-nummer som 'git: review PR #3'"
            }
        
        self.logger.info(f"Reviewing PR #{pr_number}")
        
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
                    self.logger.error(f"Kunde inte hämta pull request #{pr_number}. Status: {response.status}")
                    return {
                        "source": self.name,
                        "content": f"Kunde inte hämta pull request #{pr_number}"
                    }
                
                pr_data = await response.json()
                
            # Hämta ändringar
            files_url = f"{pr_url}/files"
            async with session.get(files_url, headers=headers) as response:
                if response.status != 200:
                    self.logger.error(f"Kunde inte hämta ändringar för PR #{pr_number}. Status: {response.status}")
                    return {
                        "source": self.name,
                        "content": f"Kunde inte hämta ändringar för PR #{pr_number}"
                    }
                
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

        self.logger.info("Sending review prompt to LLM...")
        review_text = await self.llm.query(prompt)
        self.logger.info("Received review response from LLM")

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
                        self.logger.info("Successfully posted review to GitHub")
                        return {
                            "source": self.name,
                            "content": f"Granskning postad till PR #{pr_number}:\n\n{review_text}"
                        }
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Failed to post review to GitHub. Status: {response.status}, Error: {error_text}")
                        return {
                            "source": self.name,
                            "content": f"Kunde inte posta granskningen till GitHub. Status: {response.status}\n\nGranskningstext:\n{review_text}"
                        }
        except Exception as e:
            self.logger.error(f"Error posting review to GitHub: {str(e)}")
            return {
                "source": self.name,
                "content": f"Ett fel uppstod vid postning av granskningen till GitHub: {str(e)}\n\nGranskningstext:\n{review_text}"
            }

    async def handle_explain(self, task: str) -> dict:
        """Hanterar förklaringskommandon."""
        self.log(f"Handling explain command: {task}")
        
        # Extrahera filnamnet från uppgiften
        filename = None
        if "explain" in task.lower():
            filename = task.split("explain")[-1].strip()
        elif "förklara" in task.lower():
            filename = task.split("förklara")[-1].strip()
        elif "visa" in task.lower():
            filename = task.split("visa")[-1].strip()
            
        if not filename:
            return {
                "source": self.name,
                "content": "Kunde inte hitta filnamn i kommandot. Ange ett filnamn att förklara."
            }
            
        # Hitta filen i indexet
        file_content = None
        for path, content in self.file_index.items():
            if filename in path:
                file_content = content
                break
                
        if not file_content:
            return {
                "source": self.name,
                "content": f"Kunde inte hitta filen {filename}"
            }
            
        # Skapa en prompt för LLM
        prompt = f"""
        Förklara följande kodfil:
        
        Fil: {filename}
        Innehåll:
        {file_content}
        
        Förklaringen ska innehålla:
        1. Filens huvudsyfte och funktion
        2. Viktiga klasser och funktioner
        3. Hur den interagerar med andra delar av systemet
        4. Eventuella beroenden eller kopplingar
        5. Viktiga säkerhetsaspekter eller prestandaöverväganden
        
        Var pedagogisk men teknisk i förklaringen.
        """
        
        self.log("Sending explain prompt to LLM...")
        response = await self.llm.query(prompt)
        self.log("Got response from LLM")
        
        return {
            "source": self.name,
            "content": response
        }

    async def explain_file(self, filename: str) -> str:
        """Förklarar innehållet i en fil och dess kopplingar till andra filer."""
        self.logger.info(f"Förklarar fil: {filename}")
        
        # Hitta filen i indexet
        file_content = None
        file_path = None
        for path, content in self.file_index.items():
            if filename in path:
                file_content = content
                file_path = path
                break
        
        if not file_content:
            self.logger.error(f"Kunde inte hitta filen {filename}")
            return f"Kunde inte hitta filen {filename}"

        # Hitta relaterade filer baserat på imports och referenser
        related_files = self._find_related_files(file_content)
        
        # Skapa en sammanfattning av relaterade filer
        related_files_summary = "\n".join([
            f"- {path}: {self._get_file_summary(content)}"
            for path, content in related_files.items()
        ])

        # Skapa prompt för LLM
        prompt = f"""Förklara följande kodfil och dess kopplingar till andra filer:

Fil: {file_path}
Innehåll:
{file_content}

Relaterade filer:
{related_files_summary}

Förklaringen ska innehålla:
1. Filens huvudsyfte och funktion
2. Viktiga klasser och funktioner
3. Hur den interagerar med andra filer
4. Eventuella beroenden och kopplingar
5. Viktiga säkerhetsaspekter eller prestandaöverväganden

Var pedagogisk men teknisk i förklaringen."""

        self.logger.info("Skickar förklaringsprompt till LLM")
        response = await self.llm.query(prompt)
        self.logger.info("Fick förklaringssvar från LLM")
        return response

    def _find_related_files(self, content: str) -> dict:
        """Hittar filer som är relaterade till den givna filen baserat på imports och referenser."""
        self.logger.debug("Hittar relaterade filer")
        related_files = {}
        
        # Hitta imports och referenser
        import_patterns = [
            r'from\s+([\w\.]+)\s+import',
            r'import\s+([\w\.]+)',
            r'from\s+\.([\w\.]+)\s+import',
            r'import\s+\.([\w\.]+)'
        ]
        
        for pattern in import_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                # Konvertera import-sökväg till filnamn
                potential_file = match.replace('.', '/') + '.py'
                # Hitta filen i indexet
                for path, file_content in self.file_index.items():
                    if potential_file in path:
                        related_files[path] = file_content
                        break
        
        return related_files

    def _get_file_summary(self, content: str) -> str:
        """Skapar en kort sammanfattning av en fil."""
        # Hitta klasser och funktioner
        classes = re.findall(r'class\s+(\w+)', content)
        functions = re.findall(r'def\s+(\w+)', content)
        
        summary = []
        if classes:
            summary.append(f"Klasser: {', '.join(classes)}")
        if functions:
            summary.append(f"Funktioner: {', '.join(functions)}")
        
        return " | ".join(summary) if summary else "Inga klasser eller funktioner hittades"

    def summarize_latest_commit(self):
        diff = self._get_latest_commit_diff()
        prompt = f"Review and summarize this Git commit:\n\n{diff}"
        return self.llm.query(prompt)

    async def project_overview(self) -> Dict[str, str]:
        """Returnerar en översikt över projektstrukturen."""
        try:
            # Initiera om nödvändigt
            if not hasattr(self, '_initialized'):
                await self.initialize()
                self._initialized = True

            # Uppdatera GitHub-indexet med force_refresh
            self.file_index = await self.github_indexer.index_repo(force_refresh=True)
            
            if not self.file_index:
                return {
                    "source": self.name,
                    "content": "Kunde inte hämta projektstrukturen. Försök igen senare."
                }
            
            # Skapa en trädvy av projektstrukturen
            tree = self._get_directory_structure(self.file_index)
            if not tree:
                return {
                    "source": self.name,
                    "content": "Kunde inte generera projektstrukturen. Försök igen senare."
                }
            
            return {
                "source": self.name,
                "content": tree
            }
        except Exception as e:
            logger.error(f"Fel vid hämtning av projektöversikt: {str(e)}")
            return {
                "source": self.name,
                "content": f"Ett fel uppstod vid hämtning av projektöversikt: {str(e)}"
            }

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


    def _get_directory_structure(self, file_index: dict) -> str:
        """Skapar en trädvy av projektstrukturen från file_index."""
        try:
            # Skapa en trädstruktur från file_index
            structure = {}
            for path in file_index.keys():
                # Hoppa över oönskade filer/kataloger
                if any(skip in path for skip in ['.git', 'node_modules', '__pycache__', '.env']):
                    continue
                    
                parts = path.split('/')
                current = structure
                for i, part in enumerate(parts):
                    if i == len(parts) - 1:  # Det är en fil
                        current[part] = None
                    else:  # Det är en katalog
                        if part not in current:
                            current[part] = {}
                        current = current[part]
            
            # Konvertera strukturen till en sträng med fin formatering
            output = []
            
            def add_to_output(node, prefix="", is_last=True):
                items = sorted(node.items()) if isinstance(node, dict) else []
                for i, (name, subtree) in enumerate(items):
                    is_last_item = i == len(items) - 1
                    if subtree is None:  # Det är en fil
                        output.append(f"{prefix}{'└── ' if is_last_item else '├── '}📄 {name}")
                    else:  # Det är en katalog
                        output.append(f"{prefix}{'└── ' if is_last_item else '├── '}📁 {name}/")
                        new_prefix = prefix + ('    ' if is_last_item else '│   ')
                        add_to_output(subtree, new_prefix, is_last_item)
            
            add_to_output(structure)
            return "\n".join(output) if output else "Ingen filstruktur hittades"

        except Exception as e:
            self.logger.error(f"Fel vid generering av katalogstruktur: {str(e)}")
            return "Kunde inte generera projektstruktur"

    async def analyze_commit(self, commit_hash: str) -> str:
        """Analyserar en specifik commit."""
        self.logger.info(f"Analyserar commit: {commit_hash}")
        
        headers = {
            "Authorization": f"token {os.getenv('GITHUB_AGENT_TOKEN')}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Hämta commit-information från GitHub
        commit_url = f"https://api.github.com/repos/{os.getenv('GITHUB_REPO_OWNER')}/{os.getenv('GITHUB_REPO_NAME')}/commits/{commit_hash}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(commit_url, headers=headers) as response:
                    if response.status != 200:
                        self.logger.error(f"Kunde inte hämta commit {commit_hash}. Status: {response.status}")
                        return f"Kunde inte hämta commit {commit_hash}"
                    
                    commit_data = await response.json()
                
                # Hämta ändringar för denna commit
                async with session.get(f"{commit_url}", headers=headers) as response:
                    if response.status != 200:
                        self.logger.error(f"Kunde inte hämta ändringar för commit {commit_hash}")
                        return f"Kunde inte hämta ändringar för commit {commit_hash}"
                    
                    changes_data = await response.json()
        
            # Skapa en sammanfattning av ändringarna
            files_changed = changes_data.get('files', [])
            changes_summary = []
            for file in files_changed:
                changes_summary.append(f"Fil: {file['filename']}")
                changes_summary.append(f"Ändringar: +{file.get('additions', 0)} -{file.get('deletions', 0)}")
                if file.get('patch'):
                    changes_summary.append("Ändringar:")
                    changes_summary.append(file['patch'])
                changes_summary.append("---")
            
            # Skapa prompt för LLM
            prompt = f"""Analysera följande commit:

Commit: {commit_hash}
Författare: {commit_data['commit']['author']['name']}
Datum: {commit_data['commit']['author']['date']}
Meddelande: {commit_data['commit']['message']}

Ändringar:
{chr(10).join(changes_summary)}

Ge en detaljerad analys som inkluderar:
1. Sammanfattning av ändringarna
2. Potentiell påverkan på kodbasen
3. Eventuella risker eller problem
4. Kodkvalitet och följsamhet mot best practices
5. Förslag på förbättringar

Var specifik och teknisk i analysen."""

            self.logger.info("Skickar analysprompt till LLM")
            response = await self.llm.query(prompt)
            self.logger.info("Fick analyssvar från LLM")
            return response

        except Exception as e:
            error_msg = f"Ett fel uppstod vid analys av commit {commit_hash}: {str(e)}"
            self.logger.error(error_msg)
            return error_msg

    async def analyze_code(self, task: str) -> str:
        """Analyserar kod i repositoryt."""
        self.logger.info(f"Analyserar kod för uppgift: {task}")
        
        # Hitta relevanta filer baserat på uppgiften
        relevant_files = self._find_relevant_files(task)
        if not relevant_files:
            self.logger.warning("Inga relevanta filer hittades för analys")
            return "Kunde inte hitta relevanta filer att analysera."

        self.logger.info(f"Hittade {len(relevant_files)} relevanta filer för analys")

        # Skapa en sammanfattning av filerna
        files_summary = "\n\n".join([
            f"=== {path} ===\n{self._get_file_summary(content)}"
            for path, content in relevant_files.items()
        ])

        # Skapa prompt för LLM
        prompt = f"""Analysera följande kod:

{files_summary}

Analysen ska innehålla:
1. Översikt av koden och dess struktur
2. Identifierade mönster och arkitektur
3. Potentiella förbättringar och optimeringar
4. Eventuella buggar eller säkerhetsproblem
5. Rekommendationer för vidareutveckling

Var teknisk och specifik i analysen."""

        self.logger.info("Skickar analysprompt till LLM")
        response = await self.llm.query(prompt)
        self.logger.info("Fick analyssvar från LLM")
        return response

    def _find_relevant_files(self, query: str) -> dict:
        """Hittar relevanta filer baserat på en fråga."""
        self.logger.debug(f"Hittar relevanta filer för fråga: {query}")
        relevant_files = {}
        
        # Om det är en specifik fil, hitta den exakt
        if "visa filen" in query.lower():
            filename = query.replace("visa filen", "").strip()
            for path, content in self.file_index.items():
                if filename in path:
                    relevant_files[path] = content
                    break
        else:
            # Annars, hitta alla relevanta filer baserat på söktermen
            query_lower = query.lower()
            for path, content in self.file_index.items():
                if query_lower in path.lower() or query_lower in content.lower():
                    relevant_files[path] = content
        
        self.logger.debug(f"Hittade {len(relevant_files)} relevanta filer")
        return relevant_files

    async def handle_analyze(self, task: str) -> str:
        """Analyserar kod i repositoryt."""
        self.logger.info(f"Analyserar kod för uppgift: {task}")
        
        # Hitta relevanta filer baserat på uppgiften
        relevant_files = self._find_relevant_files(task)
        if not relevant_files:
            self.logger.warning("Inga relevanta filer hittades för analys")
            return "Kunde inte hitta relevanta filer att analysera."

        self.logger.info(f"Hittade {len(relevant_files)} relevanta filer för analys")

        # Skapa en sammanfattning av filerna
        files_summary = "\n\n".join([
            f"=== {path} ===\n{self._get_file_summary(content)}"
            for path, content in relevant_files.items()
        ])

        # Skapa prompt för LLM
        prompt = f"""Analysera följande kod:

{files_summary}

Analysen ska innehålla:
1. Översikt av koden och dess struktur
2. Identifierade mönster och arkitektur
3. Potentiella förbättringar och optimeringar
4. Eventuella buggar eller säkerhetsproblem
5. Rekommendationer för vidareutveckling

Var teknisk och specifik i analysen."""

        self.logger.info("Skickar analysprompt till LLM")
        response = await self.llm.query(prompt)
        self.logger.info("Fick analyssvar från LLM")
        return response
