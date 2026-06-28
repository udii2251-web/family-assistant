"""Universal Card Format - Platform-agnostic card data structure.

This module defines a universal card format that can be rendered to different
platforms (Feishu, Web, WeChat, etc.) via platform-specific adapters.

Design Principles:
- Simple, JSON-serializable data structure
- Platform-agnostic (no Feishu-specific or Web-specific fields)
- Extensible (easy to add new card types)
- Type-safe using dataclasses
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class CardType(Enum):
    """Card type enumeration."""
    RESTOCK_ALERT = "restock_alert"
    INVENTORY_SUMMARY = "inventory_summary"
    SIMPLE_TEXT = "simple_text"
    PRODUCT_COMPARISON = "product_comparison"


class ButtonActionType(Enum):
    """Button action types."""
    DEEP_LINK = "deep_link"  # Open URL/app
    CALLBACK = "callback"    # Trigger callback
    DISMISS = "dismiss"      # Dismiss card


class AlertLevel(Enum):
    """Alert level for styling."""
    INFO = "info"        # Blue theme
    WARNING = "warning"  # Orange/yellow theme
    ERROR = "error"      # Red theme
    SUCCESS = "success"  # Green theme


@dataclass
class ProductInfo:
    """Product information for price comparison."""
    platform: str           # "taobao", "jd", "pdd"
    product_name: str
    price: float
    deep_link: str          # Platform-specific deep link (taobao://...)
    web_url: str            # Web fallback URL
    image_url: Optional[str] = None
    is_best_price: bool = False  # Marked as cheapest

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Button:
    """A button in a card."""
    text: str
    action_type: ButtonActionType
    style: str = "default"  # "primary", "default", "danger"

    # For DEEP_LINK actions
    deep_link: Optional[str] = None
    web_url: Optional[str] = None

    # For CALLBACK actions
    callback_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "action_type": self.action_type.value,
            "style": self.style,
            "deep_link": self.deep_link,
            "web_url": self.web_url,
            "callback_data": self.callback_data,
        }


@dataclass
class UniversalCard:
    """Universal card data structure.

    This is the platform-agnostic representation of a card.
    Platform adapters convert this to their specific JSON format.
    """
    card_type: CardType
    title: str
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

    # Content varies by card_type
    content: Dict[str, Any] = field(default_factory=dict)

    # Styling
    alert_level: AlertLevel = AlertLevel.INFO

    # Interactive elements
    buttons: List[Button] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)  # e.g., alert_id for callbacks

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "card_type": self.card_type.value,
            "title": self.title,
            "timestamp": self.timestamp,
            "content": self.content,
            "alert_level": self.alert_level.value,
            "buttons": [btn.to_dict() for btn in self.buttons],
            "metadata": self.metadata,
        }


class UniversalCardRenderer:
    """Builds universal card data structures.

    This class provides static methods to create UniversalCard instances
    for various use cases. Skills and orchestrators use this class to
    generate platform-agnostic card data.
    """

    @staticmethod
    def restock_alert_card(
        item_name: str,
        remaining: float,
        unit: str,
        days_until_empty: int,
        suggested_quantity: float,
        products: List[ProductInfo],
        alert_id: int = 0,
    ) -> UniversalCard:
        """Build a restock alert card.

        Args:
            item_name: Name of the item to restock
            remaining: Current stock amount
            unit: Unit of measurement (kg, L, etc.)
            days_until_empty: Days until stock runs out
            suggested_quantity: Suggested purchase quantity
            products: List of product options from different platforms
            alert_id: ID for callback tracking (0 for manual search)

        Returns:
            UniversalCard with restock alert data
        """
        # Build content dict
        content = {
            "item_name": item_name,
            "remaining": remaining,
            "unit": unit,
            "days_until_empty": days_until_empty,
            "suggested_quantity": suggested_quantity,
            "products": [p.to_dict() for p in products],
        }

        # Determine alert level
        if days_until_empty <= 3:
            alert_level = AlertLevel.ERROR
        elif days_until_empty <= 7:
            alert_level = AlertLevel.WARNING
        else:
            alert_level = AlertLevel.INFO

        # Build buttons
        buttons = []

        # Add product buttons
        for product in products:
            btn = Button(
                text=f"一键下单·{product.platform}",
                action_type=ButtonActionType.DEEP_LINK,
                style="primary" if product.is_best_price else "default",
                deep_link=product.deep_link,
                web_url=product.web_url,
            )
            buttons.append(btn)

        # Add "Mark as Done" button
        if alert_id > 0:
            mark_done_btn = Button(
                text="已补货 ✓",
                action_type=ButtonActionType.CALLBACK,
                style="default",
                callback_data={"action": "mark_done", "alert_id": str(alert_id)},
            )
            buttons.append(mark_done_btn)

        return UniversalCard(
            card_type=CardType.RESTOCK_ALERT,
            title=f"🛒 补货提醒 — {item_name}",
            content=content,
            alert_level=alert_level,
            buttons=buttons,
            metadata={"alert_id": alert_id},
        )

    @staticmethod
    def inventory_summary_card(items: List[Dict[str, Any]]) -> UniversalCard:
        """Build an inventory summary card.

        Args:
            items: List of item dicts with keys: name, remaining, unit, days_until_empty

        Returns:
            UniversalCard with inventory summary data
        """
        content = {
            "items": items,
        }

        return UniversalCard(
            card_type=CardType.INVENTORY_SUMMARY,
            title="📦 库存概览",
            content=content,
            alert_level=AlertLevel.INFO,
            buttons=[],
        )

    @staticmethod
    def simple_text_card(
        title: str,
        content: str,
        alert_level: AlertLevel = AlertLevel.INFO,
    ) -> UniversalCard:
        """Build a simple text card.

        Args:
            title: Card title
            content: Text content (can include markdown)
            alert_level: Alert level for styling

        Returns:
            UniversalCard with simple text content
        """
        return UniversalCard(
            card_type=CardType.SIMPLE_TEXT,
            title=title,
            content={"text": content},
            alert_level=alert_level,
            buttons=[],
        )

    @staticmethod
    def product_comparison_card(
        item_name: str,
        products: List[ProductInfo],
        reply_text: Optional[str] = None,
    ) -> UniversalCard:
        """Build a product comparison card (without restock alert).

        This is used when user manually searches for products.

        Args:
            item_name: Name of the product
            products: List of product options
            reply_text: Optional LLM-generated text to include

        Returns:
            UniversalCard with product comparison data
        """
        content = {
            "item_name": item_name,
            "products": [p.to_dict() for p in products],
            "reply_text": reply_text,
        }

        # Build product buttons
        buttons = []
        for product in products:
            btn = Button(
                text=f"一键下单·{product.platform}",
                action_type=ButtonActionType.DEEP_LINK,
                style="primary" if product.is_best_price else "default",
                deep_link=product.deep_link,
                web_url=product.web_url,
            )
            buttons.append(btn)

        return UniversalCard(
            card_type=CardType.PRODUCT_COMPARISON,
            title=f"🔍 {item_name} — 价格对比",
            content=content,
            alert_level=AlertLevel.INFO,
            buttons=buttons,
        )