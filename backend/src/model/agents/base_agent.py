from typing import Optional
from src.model.llm_client import LLMClient

class BaseAgent:
    def __init__(self, llm: LLMClient):
        self.llm = llm
        self.debug = True

    def log(self, message: str):
        if self.debug:
            print(f"[{self.__class__.__name__}][DEBUG] {message}")

    def can_handle(self, task: str) -> bool:
        """Kontrollerar om agenten kan hantera uppgiften."""
        return False

    async def handle(self, task: str) -> str:
        """Hanterar en uppgift."""
        raise NotImplementedError("Subclasses must implement handle()") 