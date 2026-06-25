"""Abstract base class for all agent skills.

Each skill is a self-contained module with its own:
- System prompt fragment
- Tool definitions for LLM function calling
- Tool execution logic
- Trigger definitions for proactive notifications
- Response formatting for Feishu output
"""

from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.orm import Session


class BaseSkill(ABC):
    """Abstract base class for all agent skills.

    To add a new skill, create a subclass that implements all abstract
    methods and register it in app/skills/__init__.py.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique skill identifier, e.g. 'shopping', 'pet_care'."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Brief description of what this skill handles, used by orchestrator for routing."""
        pass

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt fragment for this skill. Appended to orchestrator's base prompt."""
        pass

    @abstractmethod
    def get_tools(self) -> list[dict]:
        """Return OpenAI function-calling tool definitions for this skill."""
        pass

    @abstractmethod
    def execute_tool(self, db: Session, tool_name: str, tool_args: dict) -> str:
        """Execute a tool call and return the result as a JSON string."""
        pass

    @abstractmethod
    def get_triggers(self) -> list[dict]:
        """Return trigger definitions for proactive notifications.

        Each trigger: {"type": "periodic", "interval": "daily"/"hourly", "handler": "method_name"}
        """
        pass

    @abstractmethod
    def format_response(self, reply: str, actions: list[dict], context: dict) -> dict:
        """Format the LLM's response into a Feishu message payload.

        Returns: {"type": "text" | "card", "content": str | dict}
        """
        pass
