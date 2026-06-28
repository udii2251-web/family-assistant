"""Inventory module skill.

Migrated from app/skills/shopping.py.

Handles:
- Inventory tracking (purchase/consumption records)
- Restock alerts
- Product comparison

Updated to use UniversalCardRenderer for platform-agnostic card format.
"""

import json
import logging
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.skills.base import BaseSkill
from app.modules.inventory.models import Item, ItemCategory, PurchaseRecord, ConsumptionRecord, RestockAlert, FamilyMember
from app.modules.inventory.services import (
    get_remaining_for_item,
    get_avg_daily_rate,
    get_inventory_overview,
    get_items_needing_restock,
    generate_restock_alerts,
    convert_unit,
)
from app.services.product_search import ProductSearchService
from app.services.universal_card import UniversalCardRenderer, ProductInfo, AlertLevel
from app.feishu.card_adapter import convert_universal_to_feishu

logger = logging.getLogger(__name__)


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
5. **同步淘宝订单到库存**（自动将淘宝订单商品匹配到库存系统）
6. 用自然、亲切的语言回复

重要规则：
- 数量要精确提取，不要猜测
- 单位要统一（用户说"斤"时，1斤=0.5kg）
- 提到狗粮、狗零食等时，只关联2只狗的消耗
- 提到儿童用品时，只关联1个小孩
- 搜索商品时，提供淘宝、京东、拼多多三个平台的比价信息
- 用户提到"同步订单"、"订单转库存"、"淘宝订单记入库存"时，调用sync_orders_to_inventory工具"""

    def _find_or_create_item(
        self,
        db: Session,
        name: str,
        unit: str,
        category: str = None,
        target_audience: str = "all",
        family_id: str = None,
    ) -> Item:
        """Find existing item by name (within family), or create a new one."""
        # Query with family isolation
        query_filter = [Item.name == name]
        if family_id:
            query_filter.append(Item.family_id == family_id)

        item = db.query(Item).filter(*query_filter).first()
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

        item = Item(
            name=name,
            unit=unit,
            category_id=cat_id,
            target_audience=target_audience,
            family_id=family_id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def _match_order_to_item(self, db: Session, product_name: str) -> Optional[Item]:
        """Match Taobao order product name to existing Item.

        Strategy:
        1. Exact match
        2. Contains match (Item name in product name)
        3. Fuzzy match (keywords)

        Returns:
            Item or None if no match found
        """
        if not product_name:
            return None

        # Clean product name (remove shop prefixes, promo text)
        # e.g., "俏伊朵假发旗舰店龙须丸子头假发..." -> "假发"
        cleaned_name = self._clean_product_name(product_name)

        # 1. Exact match
        item = db.query(Item).filter(Item.name == cleaned_name).first()
        if item:
            logger.info(f"🎯 Exact match: '{product_name}' -> '{item.name}'")
            return item

        # 2. Contains match (Item name in cleaned product name)
        all_items = db.query(Item).all()
        for item in all_items:
            if item.name in cleaned_name or cleaned_name in item.name:
                logger.info(f"🎯 Contains match: '{product_name}' -> '{item.name}'")
                return item

        # 3. Keyword fuzzy match (e.g., "大米" matches "东北大米5kg")
        # Use keywords from item names
        keywords_map = {
            "大米": ["大米", "米", "糙米", "精米", "东北米", "泰国米"],
            "食用油": ["油", "食用油", "菜油", "花生油", "橄榄油", "玉米油"],
            "牛奶": ["牛奶", "奶", "纯牛奶", "鲜奶", "奶粉"],
            "洗衣液": ["洗衣液", "洗衣", "洗衣粉", "洗衣皂"],
            "洗发水": ["洗发", "洗发水", "洗发露", "护发"],
            "牙膏": ["牙膏", "牙", "口腔", "漱口水"],
            "狗粮": ["狗粮", "犬粮", "宠物粮", "狗食"],
            "狗零食": ["狗零食", "狗咬胶", "狗骨头", "宠物零食"],
            "洗洁精": ["洗洁精", "洗碗", "洗碗液"],
            "卫生纸": ["卫生纸", "纸巾", "手纸", "厕纸", "卷纸"],
        }

        for item in all_items:
            keywords = keywords_map.get(item.name, [item.name])
            for keyword in keywords:
                if keyword in cleaned_name:
                    logger.info(f"🎯 Keyword match: '{product_name}' -> '{item.name}' (keyword: '{keyword}')")
                    return item

        # No match found
        logger.info(f"❌ No match for: '{product_name}' (cleaned: '{cleaned_name}')")
        return None

    def _clean_product_name(self, product_name: str) -> str:
        """Clean Taobao product name by removing shop prefixes and promo text.

        Examples:
        - "俏伊朵假发旗舰店龙须丸子头假发..." -> "假发"
        - "金龙鱼东北大米5kg..." -> "东北大米"
        """
        import re

        # Remove common shop suffixes
        name = re.sub(r'旗舰店|专营店|专卖店|官方店|官方', '', product_name)

        # Remove promo text
        name = re.sub(r'\[.*?\]|【.*?】|促销|优惠|包邮|赠品', '', name)

        # Remove brand prefixes (keep product type)
        # e.g., "金龙鱼东北大米" -> "东北大米"
        common_brands = [
            '金龙鱼', '福临门', '海天', '蓝月亮', '立白', '舒肤佳',
            '高露洁', '佳洁士', '飘柔', '海飞丝', '沙宣',
            '伊利', '蒙牛', '光明', '雀巢', '惠氏',
            '宝路', '伟嘉', '皇家', '比瑞吉',
        ]
        for brand in common_brands:
            name = name.replace(brand, '')

        # Remove extra whitespace
        name = re.sub(r'\s+', '', name)

        # Remove special characters
        name = re.sub(r'[^\w一-鿿]', '', name)

        return name.strip()

    def get_tools(self) -> list[dict]:
        """Return inventory-related Agent Tools."""
        from app.modules.inventory.tools import get_inventory_tools
        return get_inventory_tools()

    def execute_tool(self, db: Session, tool_name: str, tool_args: dict, context: dict = None) -> str:
        """Execute a tool call and return the result as a JSON string.

        Enhanced with:
        - Detailed logging for each tool call
        - Unit conversion support
        - Better error handling
        - Family isolation (filter by family_id)
        """
        logger.info(f"🔧 Executing tool: {tool_name} with args: {tool_args}")

        # Get family_id from context (for data isolation)
        family_id = None
        if context:
            from app.models.family import FamilyMember
            user_open_id = context.get("open_id")
            if user_open_id:
                family_member = db.query(FamilyMember).filter(
                    FamilyMember.feishu_open_id == user_open_id
                ).first()
                if family_member:
                    family_id = family_member.family_id

        # If no family_id, user must create/join a family first
        if tool_name not in ["sync_orders_to_inventory"] and not family_id:
            return json.dumps({
                "success": False,
                "error": "你还没有加入家庭，请先创建或加入家庭后再使用库存管理功能。",
                "hint": "发送'创建家庭'或'加入家庭'开始使用。",
            })

        today = date.today().isoformat()

        try:
            if tool_name == "record_purchase":
                # Convert unit if needed
                quantity = tool_args["quantity"]
                unit = tool_args["unit"]
                converted_qty, converted_unit = convert_unit(quantity, unit)

                item = self._find_or_create_item(db, tool_args["item_name"], converted_unit, family_id=family_id)
                purchase_date_str = tool_args.get("purchase_date", today)

                # Get buyer_open_id from context
                buyer_open_id = context.get("open_id") if context else None

                purchase = PurchaseRecord(
                    item_id=item.id,
                    family_id=family_id,
                    quantity=converted_qty,
                    unit=converted_unit,
                    purchase_date=date.fromisoformat(purchase_date_str),
                    buyer_open_id=buyer_open_id,
                    source="chat_import",
                )
                db.add(purchase)
                db.commit()
                logger.info(f"✅ Purchase recorded: {converted_qty:.2f}{converted_unit} of {item.name}")

                remaining = get_remaining_for_item(db, item.id)
                avg_rate = get_avg_daily_rate(db, item.id)
                days_info = ""
                if avg_rate and avg_rate > 0 and remaining > 0:
                    days_info = f"，按消耗速度大概够用{int(remaining / avg_rate)}天"

                return json.dumps({
                    "item": item.name,
                    "quantity": converted_qty,
                    "unit": converted_unit,
                    "remaining": round(remaining, 2),
                    "days_info": days_info,
                    "success": True,
                })

            elif tool_name == "record_consumption":
                # Convert unit if needed
                quantity = tool_args["quantity"]
                unit = tool_args["unit"]
                converted_qty, converted_unit = convert_unit(quantity, unit)

                item = self._find_or_create_item(db, tool_args["item_name"], converted_unit, family_id=family_id)
                record_date_str = tool_args.get("record_date", today)

                # Get buyer_open_id from context
                buyer_open_id = context.get("open_id") if context else None

                consumption = ConsumptionRecord(
                    item_id=item.id,
                    family_id=family_id,
                    quantity=converted_qty,
                    unit=converted_unit,
                    record_date=date.fromisoformat(record_date_str),
                    note=tool_args.get("note", ""),
                    source="chat_import",
                )
                db.add(consumption)
                db.commit()
                logger.info(f"✅ Consumption recorded: {converted_qty:.2f}{converted_unit} of {item.name}")

                remaining = get_remaining_for_item(db, item.id)
                avg_rate = get_avg_daily_rate(db, item.id)
                urgency = ""
                if avg_rate and avg_rate > 0 and remaining > 0:
                    days = int(remaining / avg_rate)
                    if days <= 3:
                        urgency = "，建议尽快补货！"
                    elif days <= 7:
                        urgency = "，注意补货哦。"
                elif remaining <= 0:
                    urgency = "，库存已不足或为负数，请检查是否漏记采购！"

                return json.dumps({
                    "item": item.name,
                    "quantity": converted_qty,
                    "unit": converted_unit,
                    "remaining": round(remaining, 2),
                    "urgency": urgency,
                    "success": True,
                })

            elif tool_name == "query_inventory":
                if tool_args.get("item_name"):
                    # Query specific item (with family isolation)
                    item = db.query(Item).filter(
                        Item.name.contains(tool_args["item_name"]),
                        Item.family_id == family_id
                    ).first()
                    if not item:
                        logger.warning(f"❌ Item not found: {tool_args['item_name']}")
                        return json.dumps({
                            "found": False,
                            "message": f"没找到{tool_args['item_name']}，可能还没录入系统",
                            "success": False,
                        })
                    remaining = get_remaining_for_item(db, item.id)
                    avg_rate = get_avg_daily_rate(db, item.id)
                    days_until = None
                    if avg_rate and avg_rate > 0 and remaining > 0:
                        days_until = int(remaining / avg_rate)
                    logger.info(f"📊 Queried {item.name}: {remaining:.1f}{item.unit} remaining")
                    return json.dumps({
                        "item": item.name,
                        "remaining": round(remaining, 2),
                        "unit": item.unit,
                        "avg_daily_rate": round(avg_rate or 0, 3),
                        "days_until_empty": days_until,
                        "success": True,
                    })
                else:
                    # Query all items (with family isolation)
                    overview = get_inventory_overview(db, family_id=family_id)
                    items_info = [
                        {
                            "name": i.item_name,
                            "remaining": round(i.remaining, 2),
                            "unit": i.unit,
                            "days_until_empty": i.days_until_empty,
                        }
                        for i in overview
                    ]
                    logger.info(f"📊 Queried {len(overview)} items")
                    return json.dumps({"items": items_info, "success": True})

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
                logger.info(f"⚠️ {len(needing)} items need restocking")
                return json.dumps({"need_restock": alerts_info, "success": True})

            elif tool_name == "add_item":
                item = self._find_or_create_item(
                    db,
                    tool_args["name"],
                    tool_args["unit"],
                    tool_args.get("category"),
                    tool_args.get("target_audience", "all"),
                )
                logger.info(f"✅ Item added: {item.name} (unit={item.unit})")
                return json.dumps({"id": item.id, "name": item.name, "unit": item.unit, "success": True})

            elif tool_name == "list_items":
                items = db.query(Item).all()
                items_info = [
                    {"id": i.id, "name": i.name, "unit": i.unit, "target_audience": i.target_audience}
                    for i in items
                ]
                logger.info(f"📋 Listed {len(items)} items")
                return json.dumps({"items": items_info, "success": True})

            elif tool_name in ("search_products", "compare_products"):
                # Product search — delegates to ProductSearchService
                item_name = tool_args["item_name"]
                quantity = tool_args.get("quantity")
                unit = tool_args.get("unit")
                logger.info(f"🔍 Searching products for: {item_name}")

                service = ProductSearchService()

                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        future = pool.submit(asyncio.run, service.search(item_name, quantity, unit))
                        product_infos = future.result(timeout=60)
                except RuntimeError:
                    product_infos = asyncio.run(service.search(item_name, quantity, unit))
                except Exception as e:
                    logger.error(f"❌ Product search failed: {e}")
                    return json.dumps({
                        "products": [],
                        "success": False,
                        "error": f"搜索失败: {str(e)}",
                    })

                # Convert ProductInfo objects to dicts for JSON serialization
                products_data = [
                    {
                        "platform": p.platform,
                        "product_name": p.product_name,
                        "price": p.price,
                        "url": p.deep_link,
                        "display_url": p.web_url,
                    }
                    for p in product_infos
                ]
                logger.info(f"✅ Found {len(product_infos)} products")
                return json.dumps({"products": products_data, "success": True})

            elif tool_name == "sync_orders_to_inventory":
                """Sync Taobao orders to inventory (create PurchaseRecords)."""
                from app.modules.taobao.models import TaobaoOrder, TaobaoOrderItem
                from datetime import timedelta

                days = tool_args.get("days", 30)
                auto_confirm = tool_args.get("auto_confirm", False)

                logger.info(f"🔧 Syncing Taobao orders to inventory (last {days} days)")

                # Query unsynced orders
                cutoff_date = date.today() - timedelta(days=days)
                orders = db.query(TaobaoOrder).filter(
                    TaobaoOrder.synced_to_inventory == False,
                    TaobaoOrder.order_time >= cutoff_date
                ).all()

                if not orders:
                    return json.dumps({
                        "success": True,
                        "message": "没有需要同步的订单",
                        "synced_count": 0,
                    })

                synced_items = []
                unmatched_items = []

                for order in orders:
                    # Get order items
                    order_items = db.query(TaobaoOrderItem).filter(
                        TaobaoOrderItem.order_id == order.order_id
                    ).all()

                    # If no items in taobao_order_items, use main order product_name
                    if not order_items:
                        # Try to match from main order
                        matched_item = self._match_order_to_item(db, order.product_name)
                        if matched_item:
                            # Extract quantity from order (default to 1)
                            quantity = 1
                            unit = matched_item.unit

                            # Create purchase record
                            purchase = PurchaseRecord(
                                item_id=matched_item.id,
                                quantity=quantity,
                                unit=unit,
                                purchase_date=order.order_time.date() if order.order_time else date.today(),
                            )
                            db.add(purchase)

                            # Mark order as synced
                            order.synced_to_inventory = True

                            synced_items.append({
                                "order_id": order.order_id,
                                "product_name": order.product_name,
                                "matched_item": matched_item.name,
                                "quantity": quantity,
                                "unit": unit,
                            })
                            logger.info(f"✅ Synced order {order.order_id} to {matched_item.name}")
                        else:
                            unmatched_items.append({
                                "order_id": order.order_id,
                                "product_name": order.product_name,
                                "shop_name": order.shop_name,
                                "price": order.total_price,
                            })
                    else:
                        # Process each order item
                        for order_item in order_items:
                            matched_item = self._match_order_to_item(db, order_item.product_name)
                            if matched_item:
                                quantity = order_item.quantity or 1
                                unit = matched_item.unit

                                # Create purchase record
                                purchase = PurchaseRecord(
                                    item_id=matched_item.id,
                                    quantity=quantity,
                                    unit=unit,
                                    purchase_date=order.order_time.date() if order.order_time else date.today(),
                                )
                                db.add(purchase)

                                synced_items.append({
                                    "order_id": order.order_id,
                                    "product_name": order_item.product_name,
                                    "matched_item": matched_item.name,
                                    "quantity": quantity,
                                    "unit": unit,
                                })
                                logger.info(f"✅ Synced order item {order_item.product_name} to {matched_item.name}")
                            else:
                                unmatched_items.append({
                                    "order_id": order.order_id,
                                    "product_name": order_item.product_name,
                                    "sku_name": order_item.sku_name,
                                    "quantity": order_item.quantity,
                                    "price": order_item.total_price,
                                })

                # Mark orders as synced if all items processed
                for order in orders:
                    if not any(u["order_id"] == order.order_id for u in unmatched_items):
                        order.synced_to_inventory = True

                db.commit()

                result = {
                    "success": True,
                    "synced_count": len(synced_items),
                    "unmatched_count": len(unmatched_items),
                    "synced_items": synced_items,
                    "unmatched_items": unmatched_items,
                }

                if unmatched_items and not auto_confirm:
                    result["message"] = f"成功同步{len(synced_items)}个商品到库存，有{len(unmatched_items)}个商品未能自动匹配，请确认是否需要添加新物品类型。"
                else:
                    result["message"] = f"成功同步{len(synced_items)}个商品到库存"

                logger.info(f"✅ Order sync complete: {len(synced_items)} synced, {len(unmatched_items)} unmatched")
                return json.dumps(result)

            logger.error(f"❌ Unknown tool: {tool_name}")
            return json.dumps({"error": f"Unknown tool: {tool_name}", "success": False})

        except Exception as e:
            logger.error(f"❌ Tool execution failed: {tool_name} - {e}", exc_info=True)
            return json.dumps({
                "error": str(e),
                "success": False,
                "tool": tool_name,
            })

    def get_triggers(self) -> list[dict]:
        """Daily restock check trigger."""
        return [{"type": "periodic", "interval": "daily", "handler": "check_restock_and_notify"}]

    async def check_restock_and_notify(self, db: Session, feishu_client) -> list[str]:
        """Proactive trigger: check items needing restock, search products, send Feishu cards.

        Updated to use UniversalCardRenderer and card_adapter.
        """
        from app.feishu.card_adapter import convert_universal_to_feishu

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
            product_infos = await search_service.search(
                inv_item.item_name, suggested_qty, inv_item.unit
            )

            # Find cheapest price for marking
            prices = [p.price for p in product_infos if p.price > 0]
            cheapest_price = min(prices) if prices else 0

            # Update is_best_price flag
            for p in product_infos:
                p.is_best_price = (p.price == cheapest_price and p.price > 0)

            # Build universal card
            universal_card = UniversalCardRenderer.restock_alert_card(
                item_name=inv_item.item_name,
                remaining=inv_item.remaining,
                unit=inv_item.unit,
                days_until_empty=inv_item.days_until_empty or 0,
                suggested_quantity=suggested_qty,
                products=product_infos,
                alert_id=alert_id,
            )

            # Convert to Feishu format
            feishu_card = convert_universal_to_feishu(universal_card)

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
                    await feishu_client.send_card_message(member.feishu_open_id, feishu_card)
                    notified_open_ids.append(member.feishu_open_id)

            # Update alert status to "notified"
            if alert and alert.status == "pending":
                alert.status = "notified"
                db.commit()

        return notified_open_ids

    def format_response(self, reply: str, actions: list[dict], context: dict) -> dict:
        """Format inventory responses. If product search was done, return UniversalCard; otherwise text.

        Returns:
            {"type": "text" | "card", "content": str | UniversalCard}
        """
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

                    # Convert to ProductInfo
                    # Find cheapest price
                    prices = [p.get("price", 0) for p in products_raw if p.get("price", 0) > 0]
                    cheapest_price = min(prices) if prices else 0

                    product_infos = [
                        ProductInfo(
                            platform=p.get("platform", ""),
                            product_name=p.get("product_name", ""),
                            price=p.get("price", 0),
                            deep_link=p.get("url", ""),
                            web_url=p.get("display_url", ""),
                            is_best_price=(p.get("price", 0) == cheapest_price and p.get("price", 0) > 0),
                        )
                        for p in products_raw
                    ]

                    # Build comparison card
                    item_name = ""
                    for a2 in actions:
                        if a2.get("tool") in ("search_products", "compare_products"):
                            item_name = a2.get("args", {}).get("item_name", "")

                    # Use product_comparison_card for manual search
                    universal_card = UniversalCardRenderer.product_comparison_card(
                        item_name=item_name,
                        products=product_infos,
                        reply_text=reply,
                    )
                    return {"type": "card", "content": universal_card}

        return {"type": "text", "content": reply}