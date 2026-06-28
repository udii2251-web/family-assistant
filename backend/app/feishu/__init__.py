"""Feishu integration package for the Family Steward Agent.

Updated to export new card system:
- UniversalCardRenderer: Platform-agnostic card builder (from services)
- CardAdapterFactory: Multi-platform adapter factory (from services)
- CardBuilder: Legacy class (backward compatible, delegates to UniversalCardRenderer)
- ProductLink: Legacy class (backward compatible)
"""

from app.feishu.client import FeishuClient
from app.feishu.card_builder_v2 import CardBuilder, ProductLink  # Legacy exports for backward compat
from app.feishu.dispatcher import FeishuDispatcher
from app.feishu.cli_wrapper import FeishuCLI, FeishuTokenManager, FeishuWebhookParser
from app.feishu.card_adapter import convert_universal_to_feishu

__all__ = [
    "FeishuClient",
    "CardBuilder",        # Legacy (backward compatible)
    "ProductLink",        # Legacy (backward compatible)
    "FeishuDispatcher",
    "FeishuCLI",
    "FeishuTokenManager",
    "FeishuWebhookParser",
    "convert_universal_to_feishu",  # New adapter function
]
