"""Web Adapter - Converts UniversalCard to Web-friendly JSON format.

This module provides the translation layer between platform-agnostic card data
and web frontend JSON format.
"""

from typing import Dict, Any, List
from datetime import datetime

from app.services.universal_card import (
    UniversalCard,
    CardType,
    AlertLevel,
    ButtonActionType,
)


# Map alert levels to web UI theme colors
ALERT_LEVEL_TO_COLOR = {
    AlertLevel.INFO: "#1890ff",      # Blue
    AlertLevel.WARNING: "#fa8c16",   # Orange
    AlertLevel.ERROR: "#f5222d",     # Red
    AlertLevel.SUCCESS: "#52c41a",   # Green
}

# Map alert levels to web UI semantic types
ALERT_LEVEL_TO_TYPE = {
    AlertLevel.INFO: "info",
    AlertLevel.WARNING: "warning",
    AlertLevel.ERROR: "error",
    AlertLevel.SUCCESS: "success",
}

# Platform display names
PLATFORM_DISPLAY = {
    "taobao": "淘宝",
    "jd": "京东",
    "pdd": "拼多多",
}


def convert_universal_to_web(card: UniversalCard) -> Dict[str, Any]:
    """Convert UniversalCard to Web-friendly JSON format.

    Args:
        card: UniversalCard instance

    Returns:
        Web card JSON dict with structure:
        {
            "type": "card_type",
            "title": "Card title",
            "timestamp": "2024-01-01 12:00",
            "level": "info|warning|error|success",
            "color": "#1890ff",
            "content": { ... },
            "actions": [ ... ]
        }
    """
    # Route to specific converter based on card type
    converters = {
        CardType.RESTOCK_ALERT: _convert_restock_alert,
        CardType.INVENTORY_SUMMARY: _convert_inventory_summary,
        CardType.SIMPLE_TEXT: _convert_simple_text,
        CardType.PRODUCT_COMPARISON: _convert_product_comparison,
    }

    converter = converters.get(card.card_type)
    if not converter:
        # Fallback to simple text
        return _convert_simple_text(card)

    return converter(card)


def _convert_restock_alert(card: UniversalCard) -> Dict[str, Any]:
    """Convert restock alert card to web format."""
    content = card.content

    # Status summary
    remaining = content.get("remaining", 0)
    unit = content.get("unit", "")
    days_until_empty = content.get("days_until_empty", 0)
    suggested_quantity = content.get("suggested_quantity", 0)

    summary = {
        "remaining": remaining,
        "unit": unit,
        "daysUntilEmpty": days_until_empty,
        "suggestedQuantity": suggested_quantity,
    }

    # Product comparison
    products = content.get("products", [])
    product_items = []

    if products:
        # Find cheapest
        prices = [p.get("price", 0) for p in products if p.get("price", 0) > 0]
        cheapest_price = min(prices) if prices else 0

        for p in products:
            platform = p.get("platform", "")
            price = p.get("price", 0)
            is_best = (price == cheapest_price and price > 0)

            product_items.append({
                "platform": platform,
                "platformName": PLATFORM_DISPLAY.get(platform, platform),
                "productName": p.get("product_name", ""),
                "price": price,
                "priceText": f"¥{price:.1f}" if price > 0 else "暂无价格",
                "isBestPrice": is_best,
                "imageUrl": p.get("image_url"),
                "webUrl": p.get("web_url"),
                "deepLink": p.get("deep_link"),
            })

    # Actions
    actions = []
    alert_id = card.metadata.get("alert_id", 0)

    for p in products:
        platform = p.get("platform", "")
        price = p.get("price", 0)
        is_best = (price == cheapest_price and price > 0)

        actions.append({
            "type": "link",
            "text": f"一键下单·{PLATFORM_DISPLAY.get(platform, platform)}",
            "url": p.get("web_url"),
            "deepLink": p.get("deep_link"),
            "style": "primary" if is_best else "default",
        })

    # Add mark done action
    if alert_id > 0:
        actions.append({
            "type": "callback",
            "text": "已补货 ✓",
            "style": "default",
            "data": {
                "action": "mark_done",
                "alert_id": str(alert_id),
            },
        })

    return {
        "type": "restock_alert",
        "title": card.title,
        "timestamp": card.timestamp,
        "level": ALERT_LEVEL_TO_TYPE.get(card.alert_level, "info"),
        "color": ALERT_LEVEL_TO_COLOR.get(card.alert_level, "#1890ff"),
        "content": {
            "summary": summary,
            "products": product_items,
        },
        "actions": actions,
    }


def _convert_inventory_summary(card: UniversalCard) -> Dict[str, Any]:
    """Convert inventory summary card to web format."""
    items = card.content.get("items", [])
    item_list = []

    for item in items:
        days = item.get("days_until_empty")
        remaining = item.get("remaining", 0)
        unit = item.get("unit", "")
        name = item.get("name", "未知")

        if days is not None and days <= 3:
            icon = "⚠️"
            status = "urgent"
        elif days is not None and days <= 7:
            icon = "⏰"
            status = "warning"
        elif days is not None:
            icon = "✅"
            status = "normal"
        else:
            icon = "❓"
            status = "unknown"

        days_str = f"{days}天后用完" if days is not None else "未知耗尽时间"

        item_list.append({
            "name": name,
            "remaining": remaining,
            "unit": unit,
            "daysUntilEmpty": days,
            "status": status,
            "icon": icon,
            "displayText": f"{icon} {name}：剩余 {remaining:.1f}{unit}，{days_str}",
        })

    return {
        "type": "inventory_summary",
        "title": card.title,
        "timestamp": card.timestamp,
        "level": ALERT_LEVEL_TO_TYPE.get(card.alert_level, "info"),
        "color": ALERT_LEVEL_TO_COLOR.get(card.alert_level, "#1890ff"),
        "content": {
            "items": item_list,
        },
        "actions": [],
    }


def _convert_simple_text(card: UniversalCard) -> Dict[str, Any]:
    """Convert simple text card to web format."""
    content = card.content.get("text", "")

    return {
        "type": "simple_text",
        "title": card.title,
        "timestamp": card.timestamp,
        "level": ALERT_LEVEL_TO_TYPE.get(card.alert_level, "info"),
        "color": ALERT_LEVEL_TO_COLOR.get(card.alert_level, "#1890ff"),
        "content": {
            "text": content,
        },
        "actions": [],
    }


def _convert_product_comparison(card: UniversalCard) -> Dict[str, Any]:
    """Convert product comparison card to web format."""
    content = card.content

    # Optional reply text from LLM
    reply_text = content.get("reply_text")

    # Product comparison
    products = content.get("products", [])
    product_items = []

    if products:
        # Find cheapest
        prices = [p.get("price", 0) for p in products if p.get("price", 0) > 0]
        cheapest_price = min(prices) if prices else 0

        for p in products:
            platform = p.get("platform", "")
            price = p.get("price", 0)
            is_best = (price == cheapest_price and price > 0)

            product_items.append({
                "platform": platform,
                "platformName": PLATFORM_DISPLAY.get(platform, platform),
                "productName": p.get("product_name", ""),
                "price": price,
                "priceText": f"¥{price:.1f}" if price > 0 else "暂无价格",
                "isBestPrice": is_best,
                "imageUrl": p.get("image_url"),
                "webUrl": p.get("web_url"),
                "deepLink": p.get("deep_link"),
            })

    # Actions
    actions = []
    for p in products:
        platform = p.get("platform", "")
        price = p.get("price", 0)
        is_best = (price == cheapest_price and price > 0)

        actions.append({
            "type": "link",
            "text": f"一键下单·{PLATFORM_DISPLAY.get(platform, platform)}",
            "url": p.get("web_url"),
            "deepLink": p.get("deep_link"),
            "style": "primary" if is_best else "default",
        })

    return {
        "type": "product_comparison",
        "title": card.title,
        "timestamp": card.timestamp,
        "level": ALERT_LEVEL_TO_TYPE.get(card.alert_level, "info"),
        "color": ALERT_LEVEL_TO_COLOR.get(card.alert_level, "#1890ff"),
        "content": {
            "replyText": reply_text,
            "products": product_items,
        },
        "actions": actions,
    }


def convert_text_to_web(text: str, title: str = "消息") -> Dict[str, Any]:
    """Convert plain text to web card format.

    Args:
        text: Plain text message
        title: Card title

    Returns:
        Web card JSON dict
    """
    return {
        "type": "text",
        "title": title,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "level": "info",
        "color": "#1890ff",
        "content": {
            "text": text,
        },
        "actions": [],
    }