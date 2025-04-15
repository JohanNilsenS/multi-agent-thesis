import unittest
import os
import asyncio
from src.model.agents.research_agent import ResearchAgent
from src.model.supervisor import SupervisorAgent
from src.model.llm_client import LLMClient
import pytest
from dotenv import load_dotenv
from unittest.mock import AsyncMock, MagicMock, patch
import json

# Ladda miljövariabler
load_dotenv()

class TestResearchAgent(unittest.TestCase):
    def setUp(self):
        self.llm = LLMClient()
        self.agent = ResearchAgent(self.llm)
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
        self.assertTrue(self.agent.can_handle("research: find information about python"))
        self.assertTrue(self.agent.can_handle("research: search for machine learning"))
        self.assertTrue(self.agent.can_handle("research: what is artificial intelligence"))
        self.assertFalse(self.agent.can_handle("git: explain app.py"))
        self.assertFalse(self.agent.can_handle("random command"))

    def test_basic_research(self):
        """Testar grundläggande research-funktionalitet."""
        async def test():
            result = await self.agent.handle("research: find information about python")
            self.assertIsInstance(result, dict)
            self.assertIn("content", result)
            self.assertGreater(len(result["content"]), 0)
        self.run_async_test(test())

    def test_research_with_specific_topic(self):
        """Testar research med specifika ämnen."""
        async def test():
            result = await self.agent.handle("research: what is machine learning")
            self.assertIsInstance(result, dict)
            self.assertIn("content", result)
            self.assertGreater(len(result["content"]), 0)
        self.run_async_test(test())

    def test_research_with_context(self):
        """Testar research med kontext från filer."""
        async def test():
            result = await self.agent.handle("research: find information about python in current files")
            self.assertIsInstance(result, dict)
            self.assertIn("content", result)
            self.assertGreater(len(result["content"]), 0)
        self.run_async_test(test())

    def test_research_with_multiple_topics(self):
        """Testar research med flera ämnen."""
        async def test():
            result = await self.agent.handle("research: compare python and javascript")
            self.assertIsInstance(result, dict)
            self.assertIn("content", result)
            self.assertGreater(len(result["content"]), 0)
        self.run_async_test(test())

    def test_error_handling(self):
        """Testar felhantering för olika scenarion."""
        async def test():
            test_cases = [
                ("research:", "Kunde inte hantera research-kommandot"),
                ("research: ", "Kunde inte hantera research-kommandot"),
                ("invalid command", "Kunde inte hantera research-kommandot")
            ]

            for task, expected_error in test_cases:
                result = await self.agent.handle(task)
                self.assertIsInstance(result, dict)
                self.assertIn("content", result)
                self.assertIn(expected_error, result["content"])
        self.run_async_test(test())

if __name__ == '__main__':
    unittest.main() 