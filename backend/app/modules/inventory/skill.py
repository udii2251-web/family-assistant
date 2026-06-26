"""Inventory module skill.

Migrated from app/skills/shopping.py.

Handles:
- Inventory tracking (purchase/consumption records)
- Restock alerts
- Product comparison
"""

import json
from datetime import date

from sqlalchemy.orm import Session

from app.skills.base import BaseSkill
from app.modules.inventory.models import Item, ItemCategory, PurchaseRecord, ConsumptionRecord, RestockAlert, FamilyMember
from app.modules.inventory.services import (
    get_remaining_for_item,
    get_avg_daily_rate,
    get_inventory_overview,
    get_items_needing_restock,
    generate_restock_alerts,
)
from app.services.product_search import ProductSearchService
from app.feishu.card_builder import CardBuilder, ProductLink


class InventorySkill(BaseSkill):
    """Handles household inventory: tracking, alerts, and product comparison."""

    @property
    def name(self) -> str:
        return "inventory"

    @property
    def description(self) -> str:
        return "家庭日用品的库存追踪、消耗记录、补货提醒和商品比价购买"

    @property
    def system_prompt(self) -> str:
        return """你是家庭购物助手，帮助用户追踪日用品库存和消耗，预测补货时机，提供商品比价和购买建议。

家庭构成：4个大人、1个小孩、2只小狗。

你的职责：
1. 记录购买和消耗（准确提取数量和单位）
2. 查询库存情况
3. 检查补货提醒
4. 当用户提到需要购买某物品时，搜索并比较各平台价格
5. 用自然、亲切的语言回复

重要规则：
- 数量要精确提取，不要猜测
- 单位要统一（用户说"斤"时，1斤=0.5kg）
- 提到狗粮、狗零食等时，只关联2只狗的消耗
- 提到儿童用品时，只关联1个小孩
- 搜索商品时，提供淘宝、京东、拼多多三个平台的比价信息"""

    def _find_or_create_item(
        self,
        db: Session,
        name: str,
        unit: str,
        category: str = None,
        target_audience: str = "all",
    ) -> Item:
        """Find existing item by name, or create a new one."""
        item = db.query(Item).filter(Item.name == name).first()
        if item:
            return item

        cat_id = None
        if category:
            cat = db.query(ItemCategory).filter(ItemCategory.name == category).first()
            if not cat:
                cat = ItemCategory(name=category)
                db.add(cat)
                db.commit()
                db.refresh(cat)
            cat_id = cat.id

        item = Item(name=name, unit=unit, category_id=cat_id, target_audience=target_audience)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def get_tools(self) -> list[dict]:
        """Return inventory-related Agent Tools."""
        from app.modules.inventory.tools import get_inventory_tools
        return get_inventory_tools()

    def execute_tool(self, db: Session, tool_name: str, tool_args: dict) -> str:
        """Execute a tool call and return the result as a JSON string."""
        today = date.today().isoformat()

        if tool_name == "record_purchase":
            item = self._find_or_create_item(db, tool_args["item_name"], tool_args["unit"])
            purchase_date_str = tool_args.get("purchase_date", today)
            purchase = PurchaseRecord(
                item_id=item.id,
                quantity=tool_args["quantity"],
                unit=tool_args["unit"],
                purchase_date=date.fromisoformat(purchase_date_str),
            )
            db.add(purchase)
            db.commit()

            remaining = get_remaining_for_item(db, item.id)
            avg_rate = get_avg_daily_rate(db, item.id)
            days_info = ""
            if avg_rate and avg_rate > 0 and remaining > 0:
                days_info = f"，按消耗速度大概够用{int(remaining / avg_rate)}天"
            return json.dumps({
                "item": item.name,
                "quantity": tool_args["quantity"],
                "unit": tool_args["unit"],
                "remaining": round(remaining, 2),
                "days_info": days_info,
            })

        elif tool_name == "record_consumption":
            item = self._find_or_create_item(db, tool_args["item_name"], tool_args["unit"])
            record_date_str = tool_args.get("record_date", today)
            consumption = ConsumptionRecord(
                item_id=item.id,
                quantity=tool_args["quantity"],
                unit=tool_args["unit"],
                record_date=date.fromisoformat(record_date_str),
                note=tool_args.get("note", ""),
                source="chat_import",
            )
            db.add(consumption)
            db.commit()

            remaining = get_remaining_for_item(db, item.id)
            avg_rate = get_avg_daily_rate(db, item.id)
            urgency = ""
            if avg_rate and avg_rate > 0 and remaining > 0:
                days = int(remaining / avg_rate)
                if days <= 3:
                    urgency = "，建议尽快补货！"
                elif days <= 7:
                    urgency = "，注意补货哦。"
            return json.dumps({
                "item": item.name,
                "quantity": tool_args["quantity"],
                "unit": tool_args["unit"],
                "remaining": round(remaining, 2),
                "urgency": urgency,
            })

        elif tool_name == "query_inventory":
            if tool_args.get("item_name"):
                item = db.query(Item).filter(Item.name.contains(tool_args["item_name"])).first()
                if not item:
                    return json.dumps({"found": False, "message": f"没找到{tool_args['item_name']}，可能还没录入系统"})
                remaining = get_remaining_for_item(db, item.id)
                avg_rate = get_avg_daily_rate(db, item.id)
                days_until = None
                if avg_rate and avg_rate > 0 and remaining > 0:
                    days_until = int(remaining / avg_rate)
                return json.dumps({
                    "item": item.name,
                    "remaining": round(remaining, 2),
                    "unit": item.unit,
                    "avg_daily_rate": round(avg_rate or 0, 3),
                    "days_until_empty": days_until,
                })
            else:
                overview = get_inventory_overview(db)
                items_info = [
                    {
                        "name": i.item_name,
                        "remaining": round(i.remaining, 2),
                        "unit": i.unit,
                        "days_until_empty": i.days_until_empty,
                    }
                    for i in overview
                ]
                return json.dumps({"items": items_info})

        elif tool_name == "check_restock_alerts":
            generate_restock_alerts(db)
            needing = get_items_needing_restock(db)
            alerts_info = [
                {
                    "name": i.item_name,
                    "remaining": round(i.remaining, 2),
                    "unit": i.unit,
                    "days_until_empty": i.days_until_empty,
                }
                for i in needing
            ]
            return json.dumps({"need_restock": alerts_info})

        elif tool_name == "add_item":
            item = self._find_or_create_item(
                db,
                tool_args["name"],
                tool_args["unit"],
                tool_args.get("category"),
                tool_args.get("target_audience", "all"),
            )
            return json.dumps({"id": item.id, "name": item.name, "unit": item.unit})

        elif tool_name == "list_items":
            items = db.query(Item).all()
            items_info = [
                {"id": i.id, "name": i.name, "unit": i.unit, "target_audience": i.target_audience}
                for i in items
            ]
            return json.dumps({"items": items_info})

        elif tool_name in ("search_products", "compare_products"):
            # Product search — delegates to ProductSearchService
            item_name = tool_args["item_name"]
            quantity = tool_args.get("quantity")
            unit = tool_args.get("unit")

            service = ProductSearchService()

            import asyncio
            try:
                loop = asyncio.get_running_loop()
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, service.search(item_name, quantity, unit))
                    product_links = future.result(timeout=60)
            except RuntimeError:
                product_links = asyncio.run(service.search(item_name, quantity, unit))

            # Convert ProductLink objects to dicts for JSON serialization
            products_data = [
                {
                    "platform": p.platform,
                    "product_name": p.product_name,
                    "price": p.price,
                    "url": p.url,
                    "display_url": p.display_url,
                }
                for p in product_links
            ]
            return json.dumps({"products": products_data})

        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    def get_triggers(self) -> list[dict]:
        """Daily restock check trigger."""
        return [{"type": "periodic", "interval": "daily", "handler": "check_restock_and_notify"}]

    async def check_restock_and_notify(self, db: Session, feishu_client) -> list[str]:
        """Proactive trigger: check items needing restock, search products, send Feishu cards."""
        generate_restock_alerts(db)
        needing = get_items_needing_restock(db)

        notified_open_ids = []

        search_service = ProductSearchService()

        for inv_item in needing:
            # Find the active alert for this item
            alert = db.query(RestockAlert).filter(
                RestockAlert.item_id == inv_item.item_id,
                RestockAlert.status.in_(["pending", "notified"]),
            ).first()

            alert_id = alert.id if alert else 0

            # Search products for comparison
            suggested_qty = round(inv_item.avg_daily_rate * 14, 1) if inv_item.avg_daily_rate else 1
            product_links = await search_service.search(
                inv_item.item_name, suggested_qty, inv_item.unit
            )

            # Build card
            card = CardBuilder.restock_alert_card(
                item_name=inv_item.item_name,
                remaining=inv_item.remaining,
                unit=inv_item.unit,
                days_until_empty=inv_item.days_until_empty or 0,
                suggested_quantity=suggested_qty,
                products=product_links,
                alert_id=alert_id,
            )

            # Find who to notify — family members responsible for 采购
            members = db.query(FamilyMember).filter(
                FamilyMember.type == "adult",
            ).all()

            # Filter by responsibilities if available
            responsible_members = [
                m for m in members
                if m.responsibilities and (
                    "食品" in m.responsibilities
                    or "购物" in m.responsibilities
                    or "采购" in m.responsibilities
                )
            ]

            # Fallback: notify all adults with feishu_open_id
            target_members = responsible_members if responsible_members else members

            for member in target_members:
                if member.feishu_open_id:
                    await feishu_client.send_card_message(member.feishu_open_id, card)
                    notified_open_ids.append(member.feishu_open_id)

            # Update alert status to "notified"
            if alert and alert.status == "pending":
                alert.status = "notified"
                db.commit()

        return notified_open_ids

    def format_response(self, reply: str, actions: list[dict], context: dict) -> dict:
        """Format inventory responses. If product search was done, return card; otherwise text."""
        # Check if any action was a product search
        has_product_search = any(
            a.get("tool") in ("search_products", "compare_products")
            for a in actions
        )

        if has_product_search:
            # Find the product search result and build a comparison card
            for action in reversed(actions):
                if action.get("tool") in ("search_products", "compare_products"):
                    try:
                        result_data = json.loads(action.get("result", "{}"))
                        products_raw = result_data.get("products", [])
                    except json.JSONDecodeError:
                        products_raw = []

                    product_links = [
                        ProductLink(
                            platform=p.get("platform", ""),
                            product_name=p.get("product_name", ""),
                            price=p.get("price", 0),
                            url=p.get("url", ""),
                            display_url=p.get("display_url", ""),
                        )
                        for p in products_raw
                    ]

                    # Build comparison card
                    item_name = ""
                    for a2 in actions:
                        if a2.get("tool") in ("search_products", "compare_products"):
                            item_name = a2.get("args", {}).get("item_name", "")

                    card = CardBuilder.simple_text_card(
                        f"🔍 {item_name} — 价格对比",
                        reply,
                        "blue",
                    )
                    # If we have product links, use the restock-style card
                    if product_links:
                        card = CardBuilder.restock_alert_card(
                            item_name=item_name,
                            remaining=0,
                            unit="",
                            days_until_empty=0,
                            suggested_quantity=0,
                            products=product_links,
                            alert_id=0,
                        )
                    return {"type": "card", "content": card}

        return {"type": "text", "content": reply}