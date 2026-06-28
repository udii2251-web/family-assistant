"""Feishu Card Adapter - Converts UniversalCard to Feishu Interactive Card V2 JSON.

This module provides the translation layer between platform-agnostic card data
and Feishu-specific card JSON format.
"""

from typing import Dict, Any
from datetime import datetime

from app.services.universal_card import (
    UniversalCard,
    CardType,
    AlertLevel,
    ButtonActionType,
)


# Map alert levels to Feishu header templates
ALERT_LEVEL_TO_TEMPLATE = {
    AlertLevel.INFO: "blue",
    AlertLevel.WARNING: "orange",
    AlertLevel.ERROR: "red",
    AlertLevel.SUCCESS: "green",
}

# Platform display names
PLATFORM_DISPLAY = {
    "taobao": "淘宝",
    "jd": "京东",
    "pdd": "拼多多",
}


def convert_universal_to_feishu(card: UniversalCard) -> Dict[str, Any]:
    """Convert UniversalCard to Feishu Interactive Card V2 JSON.

    Args:
        card: UniversalCard instance

    Returns:
        Feishu card JSON dict
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
    """Convert restock alert card to Feishu format."""
    content = card.content
    elements = []

    # Status summary
    remaining = content.get("remaining", 0)
    unit = content.get("unit", "")
    days_until_empty = content.get("days_until_empty", 0)
    suggested_quantity = content.get("suggested_quantity", 0)

    summary_text = (
        f"**当前库存**：{remaining:.1f}{unit}\n"
        f"**预计耗尽**：{days_until_empty}天后\n"
        f"**建议购买**：{suggested_quantity:.1f}{unit}"
    )
    elements.append({
        "tag": "div",
        "text": {"tag": "lark_md", "content": summary_text},
    })

    # Product comparison
    products = content.get("products", [])
    if products:
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "**💰 价格对比**"},
        })

        # Find cheapest
        prices = [p.get("price", 0) for p in products if p.get("price", 0) > 0]
        cheapest_price = min(prices) if prices else 0

        comparison_lines = []
        for p in products:
            platform = p.get("platform", "")
            platform_name = PLATFORM_DISPLAY.get(platform, platform)
            price = p.get("price", 0)
            product_name = p.get("product_name", "")
            price_str = f"¥{price:.1f}" if price > 0 else "暂无价格"
            best_tag = " 🏆最划算" if price == cheapest_price and price > 0 else ""
            comparison_lines.append(f"- **{platform_name}**：{price_str} · {product_name}{best_tag}")

        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "\n".join(comparison_lines)},
        })

        # Action buttons
        action_buttons = []
        for p in products:
            platform = p.get("platform", "")
            platform_name = PLATFORM_DISPLAY.get(platform, platform)
            price = p.get("price", 0)
            btn_type = "primary" if (price == cheapest_price and price > 0) else "default"

            action_buttons.append({
                "tag": "button",
                "text": {"tag": "plain_text", "content": f"一键下单·{platform_name}"},
                "type": btn_type,
                "multi_url": {
                    "url": p.get("web_url", ""),
                    "android_url": p.get("deep_link", ""),
                    "ios_url": p.get("deep_link", ""),
                    "pc_url": p.get("web_url", ""),
                },
            })

        # Add callback button for mark done
        alert_id = card.metadata.get("alert_id", 0)
        if alert_id > 0:
            action_buttons.append({
                "tag": "button",
                "text": {"tag": "plain_text", "content": "已补货 ✓"},
                "type": "default",
                "value": {"action": "mark_done", "alert_id": str(alert_id)},
            })

        elements.append({
            "tag": "action",
            "actions": action_buttons,
        })
    else:
        # No products found
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "暂未找到比价信息，请手动搜索购买。"},
        })

        # Still add mark done button
        alert_id = card.metadata.get("alert_id", 0)
        if alert_id > 0:
            elements.append({
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "已补货 ✓"},
                        "type": "default",
                        "value": {"action": "mark_done", "alert_id": str(alert_id)},
                    },
                ],
            })

    # Footer
    elements.append({
        "tag": "note",
        "elements": [
            {"tag": "plain_text", "content": f"家庭管家 · {card.timestamp}"},
        ],
    })

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": card.title},
            "template": ALERT_LEVEL_TO_TEMPLATE.get(card.alert_level, "blue"),
        },
        "elements": elements,
    }


def _convert_inventory_summary(card: UniversalCard) -> Dict[str, Any]:
    """Convert inventory summary card to Feishu format."""
    items = card.content.get("items", [])
    elements = []

    for item in items:
        days = item.get("days_until_empty")
        remaining = item.get("remaining", 0)
        unit = item.get("unit", "")
        name = item.get("name", "未知")

        if days is not None and days <= 3:
            icon = "⚠️"
        elif days is not None and days <= 7:
            icon = "⏰"
        elif days is not None:
            icon = "✅"
        else:
            icon = "❓"

        days_str = f"{days}天后用完" if days is not None else "未知耗尽时间"
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"{icon} **{name}**：剩余 {remaining:.1f}{unit}，{days_str}"},
        })

    if not items:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "暂无库存数据"},
        })

    elements.append({
        "tag": "note",
        "elements": [
            {"tag": "plain_text", "content": f"家庭管家 · {card.timestamp}"},
        ],
    })

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": card.title},
            "template": ALERT_LEVEL_TO_TEMPLATE.get(card.alert_level, "blue"),
        },
        "elements": elements,
    }


def _convert_simple_text(card: UniversalCard) -> Dict[str, Any]:
    """Convert simple text card to Feishu format."""
    content = card.content.get("text", "")

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": card.title},
            "template": ALERT_LEVEL_TO_TEMPLATE.get(card.alert_level, "blue"),
        },
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": content}},
            {
                "tag": "note",
                "elements": [
                    {"tag": "plain_text", "content": f"家庭管家 · {card.timestamp}"},
                ],
            },
        ],
    }


def _convert_product_comparison(card: UniversalCard) -> Dict[str, Any]:
    """Convert product comparison card to Feishu format.

    Similar to restock alert but without inventory info.
    """
    content = card.content
    elements = []

    # Optional reply text from LLM
    reply_text = content.get("reply_text")
    if reply_text:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": reply_text},
        })

    # Product comparison
    products = content.get("products", [])
    if products:
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "**💰 价格对比**"},
        })

        # Find cheapest
        prices = [p.get("price", 0) for p in products if p.get("price", 0) > 0]
        cheapest_price = min(prices) if prices else 0

        comparison_lines = []
        for p in products:
            platform = p.get("platform", "")
            platform_name = PLATFORM_DISPLAY.get(platform, platform)
            price = p.get("price", 0)
            product_name = p.get("product_name", "")
            price_str = f"¥{price:.1f}" if price > 0 else "暂无价格"
            best_tag = " 🏆最划算" if price == cheapest_price and price > 0 else ""
            comparison_lines.append(f"- **{platform_name}**：{price_str} · {product_name}{best_tag}")

        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "\n".join(comparison_lines)},
        })

        # Action buttons
        action_buttons = []
        for p in products:
            platform = p.get("platform", "")
            platform_name = PLATFORM_DISPLAY.get(platform, platform)
            price = p.get("price", 0)
            btn_type = "primary" if (price == cheapest_price and price > 0) else "default"

            action_buttons.append({
                "tag": "button",
                "text": {"tag": "plain_text", "content": f"一键下单·{platform_name}"},
                "type": btn_type,
                "multi_url": {
                    "url": p.get("web_url", ""),
                    "android_url": p.get("deep_link", ""),
                    "ios_url": p.get("deep_link", ""),
                    "pc_url": p.get("web_url", ""),
                },
            })

        elements.append({
            "tag": "action",
            "actions": action_buttons,
        })

    # Footer
    elements.append({
        "tag": "note",
        "elements": [
            {"tag": "plain_text", "content": f"家庭管家 · {card.timestamp}"},
        ],
    })

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": card.title},
            "template": ALERT_LEVEL_TO_TEMPLATE.get(card.alert_level, "blue"),
        },
        "elements": elements,
    }