"""Per-user conversation session manager.

In-memory for MVP. Could be migrated to Redis later for persistence
and multi-instance support.
"""

from typing import Optional
from dataclasses import dataclass, field

from app.shared.config import SESSION_MAX_HISTORY


@dataclass
class UserSession:
    """Conversation state for a single Feishu user."""
    open_id: str
    history: list[dict] = field(default_factory=list)  # [{role, content}]
    active_skill: Optional[str] = None
    context: dict = field(default_factory=dict)  # skill-specific context


class SessionManager:
    """Manage per-user conversation sessions. In-memory for MVP."""

    def __init__(self, max_history: int = SESSION_MAX_HISTORY):
        self.sessions: dict[str, UserSession] = {}
        self.max_history = max_history

    def get_or_create(self, open_id: str) -> UserSession:
        """Get existing session or create a new one."""
        if open_id not in self.sessions:
            self.sessions[open_id] = UserSession(open_id=open_id)
        return self.sessions[open_id]

    def add_message(self, open_id: str, role: str, content: str) -> None:
        """Add a message to session history, trimming to max_history."""
        session = self.get_or_create(open_id)
        session.history.append({"role": role, "content": content})
        # Trim to max_history
        if len(session.history) > self.max_history:
            session.history = session.history[-self.max_history:]

    def set_active_skill(self, open_id: str, skill_name: str) -> None:
        """Set the currently active skill for this user's session."""
        session = self.get_or_create(open_id)
        session.active_skill = skill_name

    def clear(self, open_id: str) -> None:
        """Reset a user's session."""
        if open_id in self.sessions:
            del self.sessions[open_id]

    def get_all_sessions(self) -> dict[str, UserSession]:
        """Return all active sessions."""
        return self.sessions