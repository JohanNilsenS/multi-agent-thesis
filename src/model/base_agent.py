# src/model/base_agent.py

class BaseAgent:
    def __init__(self, name: str):
        self.name = name

    def can_handle(self, task: str) -> bool:
        """Determine if this agent can handle the given task."""
        raise NotImplementedError("Subclasses must implement this method.")

    def handle(self, task: str, **kwargs):
        """Handle the task and return a response."""
        raise NotImplementedError("Subclasses must implement this method.")
