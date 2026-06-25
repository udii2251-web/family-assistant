"""Taobao Connector module — order sync and login automation.

This module provides:
- Taobao login authorization (via Playwright)
- Order synchronization (last 7 days)
- Agent Tools for Feishu integration
"""

__all__ = ['get_taobao_tools', 'TaobaoSkill']