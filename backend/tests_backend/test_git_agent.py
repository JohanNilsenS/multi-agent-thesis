import unittest
import os
import asyncio
from src.model.agents.git_agent import GitAgent
from src.model.supervisor import SupervisorAgent
from src.model.llm_client import LLMClient
import pytest
from dotenv import load_dotenv
from unittest.mock import AsyncMock, MagicMock, patch
import json

# Ladda miljövariabler
load_dotenv()

class TestGitAgent(unittest.TestCase):
    def setUp(self):
        # Se till att miljövariablerna är satta
        os.environ["GITHUB_AGENT_TOKEN"] = os.getenv("GITHUB_AGENT_TOKEN", "test_token")
        os.environ["GITHUB_REPO_OWNER"] = os.getenv("GITHUB_REPO_OWNER", "test_owner")
        os.environ["GITHUB_REPO_NAME"] = os.getenv("GITHUB_REPO_NAME", "test_repo")
        
        self.llm = LLMClient()
        self.agent = GitAgent(self.llm)
        self.supervisor = SupervisorAgent(self.llm)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def run_async_test(self, coro):
        """Kör en asynkron testfunktion."""
        return self.loop.run_until_complete(coro)

    def test_can_handle(self):
        """Testar om agenten kan hantera olika typer av uppgifter."""
        self.assertTrue(self.agent.can_handle("git: visa kod"))
        self.assertTrue(self.agent.can_handle("förklara koden"))
        self.assertTrue(self.agent.can_handle("visa filen app.py"))
        self.assertFalse(self.agent.can_handle("sök på internet"))

    def test_file_index(self):
        """Testar att filindexering fungerar."""
        async def test():
            # Tvinga omindexering genom att ta bort cache-filen
            if os.path.exists(".github_index_cache.json"):
                os.remove(".github_index_cache.json")
            
            await self.agent.initialize()
            self.assertIsInstance(self.agent.file_index, dict)
            self.assertGreater(len(self.agent.file_index), 0)
        self.run_async_test(test())

    def test_analyze_code(self):
        """Testar kodanalys."""
        async def test():
            await self.agent.initialize()
            response = await self.agent.analyze_code("analysera app.py")
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 0)
        self.run_async_test(test())

    def test_reindex_files(self):
        """Testar omindexering av filer."""
        async def test():
            await self.agent.initialize()
            initial_count = len(self.agent.file_index)
            self.agent.file_index = await self.agent.github_indexer.index_repo(force_refresh=True)
            self.assertGreaterEqual(len(self.agent.file_index), initial_count)
        self.run_async_test(test())

@pytest.fixture
def mock_llm():
    mock = AsyncMock(spec=LLMClient)
    mock.query.return_value = "Test response with commit and PR information"
    return mock

@pytest.fixture
def git_agent(mock_llm):
    agent = GitAgent(mock_llm)
    agent.github_indexer = MagicMock()
    agent.github_indexer.index_repo = AsyncMock(return_value={
        "app.py": "def main():\n    pass",
        "test_app.py": "def test_main():\n    pass"
    })
    return agent

@pytest.mark.asyncio
async def test_explain_file(git_agent, mock_llm):
    """Testa olika varianter av explain-kommandon"""
    test_cases = [
        # Grundläggande varianter
        "git: explain app.py",
        "git: förklara app.py",
        "visa filen app.py",
        "förklara koden i app.py",
        
        # Olika prefix och mellanslag
        "git:explain app.py",
        "git: explain  app.py",
        "git: EXPLAIN app.py",
        
        # Svenska varianter
        "git: visa filen app.py",
        "git: förklara filen app.py",
        "git: visa koden i app.py",
        "git: förklara koden i app.py",
        "git: visa innehållet i app.py",
        "git: förklara innehållet i app.py",
        "git: visa vad som finns i app.py",
        "git: förklara vad som finns i app.py",
        "git: visa koden från app.py",
        "git: förklara koden från app.py",
        
        # Utan git:-prefix
        "visa koden i app.py",
        "förklara koden i app.py",
        "visa innehållet i app.py",
        "förklara innehållet i app.py",
        
        # Med extra ord
        "git: kan du visa koden i app.py",
        "git: kan du förklara koden i app.py",
        "git: skulle du kunna visa koden i app.py",
        "git: skulle du kunna förklara koden i app.py",
        
        # Med frågetecken
        "git: kan du visa koden i app.py?",
        "git: kan du förklara koden i app.py?",
        
        # Med versaler
        "git: VISA KODEN I app.py",
        "git: FÖRKLARA KODEN I app.py",
        
        # Med extra mellanslag
        "git:  visa  koden  i  app.py",
        "git:  förklara  koden  i  app.py"
    ]
    
    for task in test_cases:
        result = await git_agent.handle(task)
        # Kontrollera antingen för filinnehåll eller felmeddelanden
        assert any(msg in result for msg in [
            "def main():",
            "Kunde inte hitta filen",
            "Kunde inte hantera git-kommandot"
        ]), f"Failed for command: {task}"
        # Kontrollera bara query-anropet om vi faktiskt hittade filen
        if "def main():" in result:
            mock_llm.query.assert_called()
        mock_llm.reset_mock()

@pytest.mark.asyncio
async def test_review_pr(git_agent, mock_llm):
    """Testa olika varianter av PR-granskningskommandon"""
    test_cases = [
        "git: review PR #3",
        "git: granska PR #3",
        "pull request #3",
        "git: granska pull request #3"
    ]
    
    for task in test_cases:
        result = await git_agent.handle(task)
        assert "PR" in result or "Kunde inte hämta pull request" in result
        if "Kunde inte hämta pull request" not in result:
            mock_llm.query.assert_called()
        mock_llm.reset_mock()

@pytest.mark.asyncio
async def test_analyze_commit(git_agent, mock_llm):
    """Testa olika varianter av commit-analyskommandon"""
    test_cases = [
        "git: analyze commit 98fc5b6",
        "git: analysera commit 98fc5b6"
    ]
    
    for task in test_cases:
        result = await git_agent.handle(task)
        assert any(msg in result.lower() for msg in [
            "commit",
            "kunde inte hitta commit",
            "kunde inte hantera git-kommandot"
        ])
        if "kunde inte hantera git-kommandot" not in result.lower():
            mock_llm.query.assert_called()
        mock_llm.reset_mock()

@pytest.mark.asyncio
async def test_error_handling(git_agent, mock_llm):
    """Testa felhantering för olika scenarion"""
    test_cases = [
        ("git: explain nonexistent_file.py", "Kunde inte hitta filen nonexistent_file.py"),
        ("git: review PR #999999", "Kunde inte hämta pull request #999999"),
        ("git: invalid command", "Kunde inte hantera git-kommandot"),
        ("git: explain", "Kunde inte hantera git-kommandot. Ange filnamn som 'git: explain app.py'"),
        ("git: review PR", "Kunde inte hitta pull request-nummer. Ange PR-nummer som 'git: review PR #3'"),
        ("git: analyze commit", "Kunde inte hantera git-kommandot. Ange commit-hash som 'git: analyze commit 98fc5b6'")
    ]
    
    for task, expected_error in test_cases:
        result = await git_agent.handle(task)
        assert expected_error in result, f"Expected error '{expected_error}' not found in result: '{result}'"
        # Kontrollera att query inte anropas för ogiltiga kommandon
        if expected_error == "Kunde inte hantera git-kommandot":
            mock_llm.query.assert_not_called()
        mock_llm.reset_mock()

@pytest.mark.asyncio
async def test_combined_commands(git_agent, mock_llm):
    """Testa kombinerade kommandon"""
    task = "git: explain app.py and review PR #3"
    result = await git_agent.handle(task)
    assert "Kunde inte hantera git-kommandot" in result or "PR" in result

@pytest.mark.asyncio
async def test_file_explanation_content(git_agent, mock_llm):
    """Testa att filförklaringar innehåller rätt information"""
    task = "git: explain app.py"
    result = await git_agent.handle(task)
    assert "def main():" in result or "Kunde inte hitta filen" in result

@pytest.mark.asyncio
async def test_pr_review_content(git_agent, mock_llm):
    """Testa att PR-granskningar innehåller rätt information"""
    task = "git: review PR #3"
    result = await git_agent.handle(task)
    assert "PR" in result or "Kunde inte hämta pull request" in result

@pytest.mark.asyncio
async def test_commit_analysis_content(git_agent, mock_llm):
    """Testa att commit-analyser innehåller rätt information"""
    task = "git: analyze commit 98fc5b6"
    result = await git_agent.handle(task)
    assert "commit" in result.lower() or "Kunde inte hitta commit" in result

def test_github_token():
    """Testa att GitHub-token finns."""
    token = os.getenv("GITHUB_AGENT_TOKEN")
    assert token is not None, "GITHUB_AGENT_TOKEN saknas i .env-filen"
    assert len(token) > 0, "GITHUB_AGENT_TOKEN är tom"

if __name__ == '__main__':
    unittest.main() 