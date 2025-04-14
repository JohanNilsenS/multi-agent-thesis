import unittest
import os
import asyncio
from src.model.agents.git_agent import GitAgent
from src.model.supervisor import SupervisorAgent
from src.model.llm_client import LLMClient

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

    def test_get_relevant_files(self):
        """Testar att hitta relevanta filer."""
        async def test():
            await self.agent.initialize()
            relevant_files = self.agent._get_relevant_files("app.py")
            self.assertIsInstance(relevant_files, str)
            self.assertGreater(len(relevant_files), 0)
        self.run_async_test(test())

    def test_find_and_explain_file(self):
        """Testar att hitta och förklara en specifik fil."""
        async def test():
            await self.agent.initialize()
            response = await self.agent.find_and_explain_file("visa filen app.py")
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 0)
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

if __name__ == '__main__':
    unittest.main() 