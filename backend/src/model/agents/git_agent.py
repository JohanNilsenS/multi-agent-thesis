# src/model/agents/git_agent.py

import subprocess
import os
import re
import ast
from src.model.base_agent import BaseAgent
from src.model.llm_client import LLMClient
from src.model.utils.file_indexer import index_repo_files

class GitAgent(BaseAgent):
    def __init__(self, repo_path: str, llm_client: LLMClient):
        super().__init__("GitAgent")
        self.repo_path = repo_path
        self.llm = llm_client
        self.file_index = index_repo_files(self.repo_path)

    def can_handle(self, task: str) -> bool:
        task = task.lower()
        return any(keyword in task for keyword in [
            "git", "code review", "commit", "project overview", "suggest improvement"
        ])

    def handle(self, task: str, **kwargs):
        if "summary" in task:
            return self.summarize_latest_commit()
        elif "project overview" in task:
            return self.project_overview()
        elif "suggest improvement" in task:
            return self.suggest_improvements()
        else:
            return "GitAgent: Task not recognized."

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
        from src.model.utils.file_indexer import index_repo_files
        self.file_index = index_repo_files(self.repo_path, force_refresh=True)
        print("[GitAgent] File index refreshed and cached.")

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
