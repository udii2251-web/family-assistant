"""Skills module.

This module provides skill implementations for the agent.
"""

# Delayed import to avoid circular dependency
_skills_registry = None


def get_all_skills():
    """Get all registered skills (delayed import)."""
    global _skills_registry
    if _skills_registry is None:
        from app.modules.inventory.skill import InventorySkill
        from app.modules.taobao.tools import TaobaoSkill
        from app.modules.family.tools import FamilySkill
        _skills_registry = {
            "inventory": InventorySkill(),
            "taobao": TaobaoSkill(),
            "family": FamilySkill(),  # 新增家庭管理skill
        }
    return _skills_registry


def get_skill(name: str):
    """Get a specific skill by name (delayed import)."""
    skills = get_all_skills()
    # Support both "inventory" and legacy "shopping" name
    if name == "shopping":
        name = "inventory"
    return skills.get(name)


def register_skill(skill):
    """Register a new skill."""
    global _skills_registry
    if _skills_registry is None:
        _skills_registry = {}
    _skills_registry[skill.name] = skill