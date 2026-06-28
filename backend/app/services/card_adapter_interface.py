"""Platform Card Adapter Interface - Abstract adapter for multi-platform card rendering.

This module defines the abstract interface for platform-specific card adapters.
Each platform (Feishu, DingTalk, WeChat, etc.) should implement its own adapter.

Usage:
    from app.services.card_adapter_interface import CardAdapterFactory
    from app.services.universal_card import UniversalCard

    adapter = CardAdapterFactory.get_adapter("feishu")
    feishu_json = adapter.render(universal_card)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum

from app.services.universal_card import UniversalCard


class PlatformType(Enum):
    """Supported platforms."""
    FEISHU = "feishu"
    DINGTALK = "dingtalk"
    WECHAT = "wechat"
    WEB = "web"


class BaseCardAdapter(ABC):
    """Abstract base class for platform-specific card adapters.

    Each platform adapter must implement the render() method to convert
    UniversalCard to platform-specific format.
    """

    @property
    @abstractmethod
    def platform(self) -> PlatformType:
        """Return the platform type this adapter handles."""
        pass

    @abstractmethod
    def render(self, card: UniversalCard) -> Dict[str, Any]:
        """Convert UniversalCard to platform-specific format.

        Args:
            card: UniversalCard instance

        Returns:
            Platform-specific card data (JSON dict, XML, etc.)
        """
        pass

    @abstractmethod
    def render_text(self, text: str) -> Dict[str, Any]:
        """Render plain text message for this platform.

        Args:
            text: Plain text content

        Returns:
            Platform-specific text message format
        """
        pass


class FeishuCardAdapter(BaseCardAdapter):
    """Feishu platform adapter using existing card_adapter.py logic."""

    @property
    def platform(self) -> PlatformType:
        return PlatformType.FEISHU

    def render(self, card: UniversalCard) -> Dict[str, Any]:
        """Convert UniversalCard to Feishu Interactive Card V2 JSON."""
        from app.feishu.card_adapter import convert_universal_to_feishu
        return convert_universal_to_feishu(card)

    def render_text(self, text: str) -> Dict[str, Any]:
        """Render plain text for Feishu."""
        return {"type": "text", "content": text}


class DingTalkCardAdapter(BaseCardAdapter):
    """DingTalk platform adapter (placeholder for future implementation).

    DingTalk uses ActionCard format for interactive cards.
    Reference: https://open.dingtalk.com/document/orgapp/types-of-messages-sent-by-robots
    """

    @property
    def platform(self) -> PlatformType:
        return PlatformType.DINGTALK

    def render(self, card: UniversalCard) -> Dict[str, Any]:
        """Convert UniversalCard to DingTalk ActionCard format.

        DingTalk ActionCard structure:
        {
            "msgtype": "actionCard",
            "actionCard": {
                "title": "...",
                "text": "...",
                "btnOrientation": "0",
                "btns": [...]
            }
        }
        """
        from app.services.universal_card import CardType, AlertLevel

        # Map alert level to title color/theme
        alert_color_map = {
            AlertLevel.INFO: "blue",
            AlertLevel.WARNING: "orange",
            AlertLevel.ERROR: "red",
            AlertLevel.SUCCESS: "green",
        }

        # Build text content based on card type
        text_content = self._build_text_content(card)

        # Build buttons
        buttons = []
        for btn in card.buttons:
            if btn.action_type.value == "deep_link":
                buttons.append({
                    "title": btn.text,
                    "actionURL": btn.web_url or btn.deep_link or "",
                })
            elif btn.action_type.value == "callback":
                # DingTalk callback requires special handling
                buttons.append({
                    "title": btn.text,
                    "actionURL": "",  # DingTalk doesn't support pure callbacks
                })

        return {
            "msgtype": "actionCard",
            "actionCard": {
                "title": card.title,
                "text": text_content,
                "btnOrientation": "0",  # Vertical layout
                "btns": buttons,
            }
        }

    def render_text(self, text: str) -> Dict[str, Any]:
        """Render plain text for DingTalk."""
        return {"msgtype": "text", "text": {"content": text}}

    def _build_text_content(self, card: UniversalCard) -> str:
        """Build text content for DingTalk card."""
        from app.services.universal_card import CardType

        lines = [f"### {card.title}", ""]

        if card.card_type == CardType.RESTOCK_ALERT:
            content = card.content
            remaining = content.get("remaining", 0)
            unit = content.get("unit", "")
            days = content.get("days_until_empty", 0)
            suggested = content.get("suggested_quantity", 0)

            lines.append(f"**当前库存**: {remaining:.1f}{unit}")
            lines.append(f"**预计耗尽**: {days}天后")
            lines.append(f"**建议购买**: {suggested:.1f}{unit}")
            lines.append("")

            products = content.get("products", [])
            if products:
                lines.append("---")
                lines.append("**价格对比**:")
                for p in products:
                    platform = p.get("platform", "")
                    name = p.get("product_name", "")
                    price = p.get("price", 0)
                    price_str = f"¥{price:.1f}" if price > 0 else "暂无价格"
                    lines.append(f"- {platform}: {price_str} ({name})")

        elif card.card_type == CardType.INVENTORY_SUMMARY:
            items = card.content.get("items", [])
            for item in items:
                name = item.get("name", "")
                remaining = item.get("remaining", 0)
                unit = item.get("unit", "")
                days = item.get("days_until_empty")
                days_str = f"{days}天后用完" if days else "未知耗尽时间"
                lines.append(f"- {name}: {remaining:.1f}{unit}, {days_str}")

        elif card.card_type == CardType.SIMPLE_TEXT:
            text = card.content.get("text", "")
            lines.append(text)

        lines.append("")
        lines.append(f"家庭管家 · {card.timestamp}")

        return "\n".join(lines)


class WeChatCardAdapter(BaseCardAdapter):
    """WeChat Work platform adapter (placeholder for future implementation).

    WeChat Work uses Markdown format for rich messages.
    Reference: https://developer.work.weixin.qq.com/document/path/90236
    """

    @property
    def platform(self) -> PlatformType:
        return PlatformType.WECHAT

    def render(self, card: UniversalCard) -> Dict[str, Any]:
        """Convert UniversalCard to WeChat Work markdown format."""
        # Build markdown content
        markdown_content = self._build_markdown(card)

        return {
            "msgtype": "markdown",
            "markdown": {
                "content": markdown_content,
            }
        }

    def render_text(self, text: str) -> Dict[str, Any]:
        """Render plain text for WeChat Work."""
        return {"msgtype": "text", "text": {"content": text}}

    def _build_markdown(self, card: UniversalCard) -> str:
        """Build markdown content for WeChat card."""
        from app.services.universal_card import CardType

        lines = [f"## {card.title}", ""]

        if card.card_type == CardType.RESTOCK_ALERT:
            content = card.content
            remaining = content.get("remaining", 0)
            unit = content.get("unit", "")
            days = content.get("days_until_empty", 0)
            suggested = content.get("suggested_quantity", 0)

            lines.append(f"> 当前库存: **{remaining:.1f}{unit}**")
            lines.append(f"> 预计耗尽: **{days}天后**")
            lines.append(f"> 建议购买: **{suggested:.1f}{unit}**")
            lines.append("")

            products = content.get("products", [])
            if products:
                lines.append("---")
                lines.append("### 价格对比")
                for p in products:
                    platform = p.get("platform", "")
                    name = p.get("product_name", "")
                    price = p.get("price", 0)
                    web_url = p.get("web_url", "")
                    price_str = f"¥{price:.1f}" if price > 0 else "暂无价格"
                    if web_url:
                        lines.append(f"- [{platform}]({web_url}): {price_str} ({name})")
                    else:
                        lines.append(f"- {platform}: {price_str} ({name})")

        elif card.card_type == CardType.INVENTORY_SUMMARY:
            items = card.content.get("items", [])
            for item in items:
                name = item.get("name", "")
                remaining = item.get("remaining", 0)
                unit = item.get("unit", "")
                days = item.get("days_until_empty")
                days_str = f"{days}天后用完" if days else "未知耗尽时间"
                lines.append(f"- **{name}**: {remaining:.1f}{unit}, {days_str}")

        elif card.card_type == CardType.SIMPLE_TEXT:
            text = card.content.get("text", "")
            lines.append(text)

        lines.append("")
        lines.append(f"<font color=\"comment\">家庭管家 · {card.timestamp}</font>")

        return "\n".join(lines)


class WebCardAdapter(BaseCardAdapter):
    """Web/HTML platform adapter for frontend rendering.

    This adapter returns a JSON structure suitable for React/Vue frontend.
    """

    @property
    def platform(self) -> PlatformType:
        return PlatformType.WEB

    def render(self, card: UniversalCard) -> Dict[str, Any]:
        """Convert UniversalCard to frontend-friendly JSON."""
        return {
            "type": "card",
            "cardType": card.card_type.value,
            "title": card.title,
            "timestamp": card.timestamp,
            "alertLevel": card.alert_level.value,
            "content": card.content,
            "buttons": [
                {
                    "text": btn.text,
                    "actionType": btn.action_type.value,
                    "style": btn.style,
                    "webUrl": btn.web_url,
                    "deepLink": btn.deep_link,
                    "callbackData": btn.callback_data,
                }
                for btn in card.buttons
            ],
            "metadata": card.metadata,
        }

    def render_text(self, text: str) -> Dict[str, Any]:
        """Render plain text for Web."""
        return {"type": "text", "content": text}


class CardAdapterFactory:
    """Factory for creating platform-specific card adapters.

    Usage:
        adapter = CardAdapterFactory.get_adapter("feishu")
        feishu_json = adapter.render(universal_card)

        # Or with platform enum
        adapter = CardAdapterFactory.get_adapter(PlatformType.FEISHU)
    """

    _adapters = {
        PlatformType.FEISHU: FeishuCardAdapter(),
        PlatformType.DINGTALK: DingTalkCardAdapter(),
        PlatformType.WECHAT: WeChatCardAdapter(),
        PlatformType.WEB: WebCardAdapter(),
    }

    @staticmethod
    def get_adapter(platform: str | PlatformType) -> BaseCardAdapter:
        """Get adapter for the specified platform.

        Args:
            platform: Platform name string or PlatformType enum

        Returns:
            Platform-specific adapter instance

        Raises:
            ValueError: If platform is not supported
        """
        if isinstance(platform, str):
            platform_map = {
                "feishu": PlatformType.FEISHU,
                "dingtalk": PlatformType.DINGTALK,
                "wechat": PlatformType.WECHAT,
                "web": PlatformType.WEB,
            }
            platform = platform_map.get(platform.lower())
            if not platform:
                raise ValueError(f"Unsupported platform: {platform}")

        adapter = CardAdapterFactory._adapters.get(platform)
        if not adapter:
            raise ValueError(f"No adapter registered for platform: {platform}")

        return adapter

    @staticmethod
    def register_adapter(adapter: BaseCardAdapter) -> None:
        """Register a custom adapter for a platform.

        Args:
            adapter: Custom adapter instance
        """
        CardAdapterFactory._adapters[adapter.platform] = adapter

    @staticmethod
    def supported_platforms() -> list[str]:
        """Return list of supported platform names."""
        return [p.value for p in PlatformType]