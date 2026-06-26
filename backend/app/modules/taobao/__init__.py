"""Taobao Connector module — order sync and login automation.

This module provides:
- Taobao login authorization (via Playwright)
- Order synchronization (last 7 days)
- Agent Tools for Feishu integration

Usage:
    from app.modules.taobao import get_taobao_tools, TaobaoSkill

    # Get tools for LLM
    tools = get_taobao_tools()

    # Use skill in orchestrator
    taobao_skill = TaobaoSkill()
"""

from app.modules.taobao.tools import get_taobao_tools, execute_taobao_tool, TaobaoSkill

__all__ = [
    'get_taobao_tools',
    'execute_taobao_tool',
    'TaobaoSkill'
]

# Module metadata
MODULE_NAME = 'taobao'
MODULE_VERSION = '1.0.0'
MODULE_DESCRIPTION = '淘宝订单同步与查询功能模块'