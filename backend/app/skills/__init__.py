"""Skill framework — base class and registry for all agent skills."""

from typing import Optional

from app.skills.base import BaseSkill
from app.skills.shopping import ShoppingSkill

# Registry of all available skills
SKILLS: dict[str, BaseSkill] = {}


def register_skill(skill: BaseSkill):
    """Register a skill module in the global registry."""
    SKILLS[skill.name] = skill


def get_skill(name: str) -> Optional[BaseSkill]:
    """Retrieve a skill by name, or None if not found."""
    return SKILLS.get(name)


def get_all_skills() -> dict[str, BaseSkill]:
    """Return all registered skills."""
    return SKILLS


# Auto-register known skills
register_skill(ShoppingSkill())
