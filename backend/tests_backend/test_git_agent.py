import unittest
import os
import asyncio
from src.model.agents.git_agent import GitAgent
from src.model.supervisor import SupervisorAgent
from src.model.llm_client import LLMClient
import pytest
from dotenv import load_dotenv

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
def git_agent():
    """Skapa en GitAgent-instans för tester."""
    llm_client = LLMClient()
    agent = GitAgent(llm_client)
    return agent

def test_can_handle(git_agent):
    """Testa om agenten kan hantera git-relaterade uppgifter."""
    # Testa olika git-relaterade uppgifter
    assert git_agent.can_handle("git: explain app.py")
    assert git_agent.can_handle("git: review PR #3")
    assert git_agent.can_handle("git: analyze commit abc123")
    assert git_agent.can_handle("visa filen app.py")
    assert git_agent.can_handle("förklara koden i app.py")
    assert git_agent.can_handle("pull request #3")
    
    # Testa icke-git-relaterade uppgifter
    assert not git_agent.can_handle("hej världen")
    assert not git_agent.can_handle("vad är klockan?")

@pytest.mark.asyncio
async def test_explain_file(git_agent):
    """Testa filförklaring."""
    # Testa med en giltig fil
    result = await git_agent.explain_file("app.py")
    assert isinstance(result, str)
    assert len(result) > 0
    
    # Testa med en ogiltig fil
    result = await git_agent.explain_file("nonexistent_file.py")
    assert "kunde inte hitta" in result.lower()

@pytest.mark.asyncio
async def test_review_pull_request(git_agent):
    """Testa PR-granskning."""
    # Testa med ett giltigt PR-nummer
    result = await git_agent.review_pull_request("PR #3")
    assert isinstance(result, str)
    assert len(result) > 0
    
    # Testa med ett ogiltigt PR-nummer
    result = await git_agent.review_pull_request("PR #999999")
    assert "kunde inte hämta pull request #999999" in result.lower()

@pytest.mark.asyncio
async def test_analyze_commit(git_agent):
    """Testa commit-analys."""
    result = await git_agent.analyze_commit("98fc5b6")
    assert isinstance(result, str)
    assert len(result) > 0
    assert "commit" in result.lower() or "ändring" in result.lower()

@pytest.mark.asyncio
async def test_handle(git_agent):
    """Testa den allmänna hanteringen av uppgifter."""
    # Testa olika typer av uppgifter
    result = await git_agent.handle("git: explain app.py")
    assert isinstance(result, str)
    assert len(result) > 0
    
    result = await git_agent.handle("git: review PR #3")
    assert isinstance(result, str)
    assert len(result) > 0
    
    result = await git_agent.handle("git: analyze commit 98fc5b6")
    assert isinstance(result, str)
    assert len(result) > 0
    
    # Testa ogiltig uppgift
    result = await git_agent.handle("git: invalid command")
    assert "kunde inte hantera" in result.lower()

def test_github_token():
    """Testa att GitHub-token finns."""
    token = os.getenv("GITHUB_AGENT_TOKEN")
    assert token is not None, "GITHUB_AGENT_TOKEN saknas i .env-filen"
    assert len(token) > 0, "GITHUB_AGENT_TOKEN är tom"

if __name__ == '__main__':
    unittest.main() 