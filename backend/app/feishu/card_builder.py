"""Builder for Feishu Interactive Card V2 JSON payloads."""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class ProductLink:
    """A product listing from an e-commerce platform."""
    platform: str       # "taobao", "jd", "pdd"
    product_name: str
    price: float
    url: str            # deep link (taobao://..., openapp.jdmobile://..., pinduoduo://...)
    display_url: str    # web fallback URL
    image_url: Optional[str] = None


PLATFORM_DISPLAY = {
    "taobao": "淘宝",
    "jd": "京东",
    "pdd": "拼多多",
}


class CardBuilder:
    """Constructs Feishu Interactive Card V2 JSON payloads.

    Cards are the primary UI for the agent — product comparisons, inventory
    summaries, and general responses are all delivered as interactive cards
    with buttons that can deep-link into e-commerce apps or trigger callbacks.
    """

    @staticmethod
    def restock_alert_card(
        item_name: str,
        remaining: float,
        unit: str,
        days_until_empty: int,
        suggested_quantity: float,
        products: list[ProductLink],
        alert_id: int,
    ) -> dict:
        """Build a restock alert card with product comparison and buy buttons.

        Card structure:
        - Header: red template with urgency emoji + item name
        - Body: remaining amount, days until empty, suggested quantity
        - Product comparison: each platform's price
        - Action buttons: "一键下单" per platform (multi_url deep links)
        - Callback button: "已补货" to mark alert as done
        """
        elements = []

        # Status summary
        summary_text = (
            f"**当前库存**：{remaining:.1f}{unit}\n"
            f"**预计耗尽**：{days_until_empty}天后\n"
            f"**建议购买**：{suggested_quantity:.1f}{unit}"
        )
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": summary_text},
        })

        # Product comparison if available
        if products:
            elements.append({"tag": "hr"})
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**💰 价格对比**"},
            })

            # Find cheapest
            cheapest_price = min(p.price for p in products if p.price > 0) if any(p.price > 0 for p in products) else 0

            comparison_lines = []
            for p in products:
                platform_name = PLATFORM_DISPLAY.get(p.platform, p.platform)
                price_str = f"¥{p.price:.1f}" if p.price > 0 else "暂无价格"
                best_tag = " 🏆最划算" if p.price == cheapest_price and p.price > 0 else ""
                comparison_lines.append(f"- **{platform_name}**：{price_str} · {p.product_name}{best_tag}")

            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": "\n".join(comparison_lines)},
            })

            # Buy buttons
            action_buttons = []
            for p in products:
                platform_name = PLATFORM_DISPLAY.get(p.platform, p.platform)
                btn_type = "primary" if (p.price == cheapest_price and p.price > 0) else "default"

                action_buttons.append({
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": f"一键下单·{platform_name}"},
                    "type": btn_type,
                    "multi_url": {
                        "url": p.display_url,
                        "android_url": p.url,
                        "ios_url": p.url,
                        "pc_url": p.display_url,
                    },
                })

            # Callback button for marking done
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
            # No products found — still show a "已补货" callback button
            elements.append({"tag": "hr"})
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": "暂未找到比价信息，请手动搜索购买。"},
            })
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

        # Footer note with timestamp
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        elements.append({
            "tag": "note",
            "elements": [
                {"tag": "plain_text", "content": f"家庭管家 · {now}"},
            ],
        })

        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"🛒 补货提醒 — {item_name}"},
                "template": "red",
            },
            "elements": elements,
        }

    @staticmethod
    def inventory_summary_card(items: list[dict]) -> dict:
        """Build a summary card showing inventory overview.

        Args:
            items: list of dicts with keys: name, remaining, unit, days_until_empty
        """
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
                {"tag": "plain_text", "content": f"家庭管家 · {datetime.now().strftime('%Y-%m-%d %H:%M')}"},
            ],
        })

        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "📦 库存概览"},
                "template": "blue",
            },
            "elements": elements,
        }

    @staticmethod
    def simple_text_card(title: str, content: str, template: str = "blue") -> dict:
        """Build a simple card with title and text content."""
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": template,
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": content}},
                {
                    "tag": "note",
                    "elements": [
                        {"tag": "plain_text", "content": f"家庭管家 · {datetime.now().strftime('%Y-%m-%d %H:%M')}"},
                    ],
                },
            ],
        }
