# test_supervisor.py
from src.model.supervisor import SupervisorAgent
from src.model.tools.internet_search import search_duckduckgo
import unittest
import os
import asyncio
from src.model.llm_client import LLMClient
import pytest
from dotenv import load_dotenv
from unittest.mock import AsyncMock, MagicMock, patch
import json

# Ladda miljövariabler
load_dotenv()

class TestSupervisorAgent(unittest.TestCase):
    def setUp(self):
        self.llm = LLMClient()
        self.supervisor = SupervisorAgent(self.llm)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def run_async_test(self, coro):
        """Kör en asynkron testfunktion."""
        return self.loop.run_until_complete(coro)

    def test_delegate_to_git_agent(self):
        """Testar att uppgifter delegeras till GitAgent."""
        async def test():
            test_cases = [
                "git: explain app.py",
                "git: förklara koden i app.py",
                "visa filen app.py",
                "git: review PR #3",
                "git: analyze commit 98fc5b6"
            ]
            
            for task in test_cases:
                result = await self.supervisor.delegate(task)
                self.assertEqual(result['source'], 'GitAgent', f"Task '{task}' should be delegated to GitAgent")

        self.run_async_test(test())

    def test_delegate_to_research_agent(self):
        """Testar att uppgifter delegeras till ResearchAgent."""
        async def test():
            test_cases = [
                "research: vad är python?",
                "research: förklara machine learning",
                "sök information om AI",
                "hitta information om python",
                "vad är artificiell intelligens?"
            ]
            
            for task in test_cases:
                result = await self.supervisor.delegate(task)
                self.assertEqual(result['source'], 'ResearchAgent', f"Task '{task}' should be delegated to ResearchAgent")

        self.run_async_test(test())

    def test_error_handling(self):
        """Testar felhantering för olika scenarion."""
        async def test():
            test_cases = [
                ("", "Kunde inte hantera uppgiften"),
                ("   ", "Kunde inte hantera uppgiften"),
                ("invalid command", "Kunde inte hantera uppgiften")
            ]
            
            for task, expected_error in test_cases:
                result = await self.supervisor.delegate(task)
                self.assertIn(expected_error, result['content'])

        self.run_async_test(test())

    def test_combined_commands(self):
        """Testar kombinerade kommandon."""
        async def test():
            test_cases = [
                "git: explain app.py and research: what is python",
                "research: python and git: explain app.py"
            ]
            
            for task in test_cases:
                result = await self.supervisor.delegate(task)
                # Kontrollera att minst en agent kunde hantera uppgiften
                self.assertTrue(result['source'] in ['GitAgent', 'ResearchAgent'])

        self.run_async_test(test())

if __name__ == '__main__':
    unittest.main()
