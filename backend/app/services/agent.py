import json
from datetime import date

from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL
from app.models.item import Item, ItemCategory
from app.models.family import FamilyMember
from app.models.consumption import ConsumptionRecord
from app.models.purchase import PurchaseRecord
from app.models.alert import RestockAlert
from app.services.inventory import get_inventory_overview, get_remaining_for_item, get_avg_daily_rate, get_items_needing_restock
from app.services.alert_scheduler import generate_restock_alerts

def _get_client():
    if not LLM_API_KEY:
        raise ValueError("LLM_API_KEY is not set. Please set it in environment variables.")
    return OpenAI(base_url=LLM_API_BASE, api_key=LLM_API_KEY)


SYSTEM_PROMPT = """你是一个家庭开支管理助手，帮助用户追踪家庭日用品的消耗情况，预测补货时机，并及时提醒。

家庭构成：4个大人、1个小孩、2只小狗。

你的职责：
1. 当用户告诉你购买了什么物品或用了多少时，准确记录下来
2. 当用户询问库存情况时，查询并给出清晰的回答
3. 当用户询问什么东西快用完时，检查并给出提醒
4. 用自然、亲切的语言回复，像家人之间的对话

重要规则：
- 数量要精确提取，不要猜测
- 单位要统一（用户说"斤"时，1斤=0.5kg）
- 提到狗粮、狗零食等时，只关联2只狗的消耗
- 提到儿童用品时，只关联1个小孩
"""


def _build_tools():
    return [
        {
            "type": "function",
            "function": {
                "name": "record_purchase",
                "description": "记录购买了一个物品，增加库存",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item_name": {"type": "string", "description": "物品名称"},
                        "quantity": {"type": "number", "description": "购买数量"},
                        "unit": {"type": "string", "description": "单位(kg/L/包/瓶/个等)"},
                        "purchase_date": {"type": "string", "description": "购买日期, YYYY-MM-DD格式, 默认今天"},
                    },
                    "required": ["item_name", "quantity", "unit"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "record_consumption",
                "description": "记录消耗了一个物品，减少库存",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item_name": {"type": "string", "description": "物品名称"},
                        "quantity": {"type": "number", "description": "消耗数量"},
                        "unit": {"type": "string", "description": "单位(kg/L/包/瓶/个等)"},
                        "record_date": {"type": "string", "description": "记录日期, YYYY-MM-DD格式, 默认今天"},
                        "note": {"type": "string", "description": "备注(可选)"},
                    },
                    "required": ["item_name", "quantity", "unit"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "query_inventory",
                "description": "查询所有物品的库存情况，包括剩余量和预计耗尽日期",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item_name": {"type": "string", "description": "指定查询某个物品(可选), 留空查询所有"},
                    },
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "check_restock_alerts",
                "description": "查看哪些物品需要补货",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "add_item",
                "description": "添加一个新的物品类型到系统中",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "物品名称"},
                        "unit": {"type": "string", "description": "默认单位"},
                        "category": {"type": "string", "description": "分类(食品/洗护/宠物用品/清洁/其他)"},
                        "target_audience": {"type": "string", "description": "适用对象: all/child/dog"},
                    },
                    "required": ["name", "unit"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_items",
                "description": "列出系统中所有物品类型",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
    ]


def _find_or_create_item(db: Session, name: str, unit: str, category: str = None, target_audience: str = "all") -> Item:
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


def _execute_tool(db: Session, tool_name: str, tool_args: dict) -> str:
    """Execute a tool call and return the result as a string."""
    today = date.today().isoformat()

    if tool_name == "record_purchase":
        item = _find_or_create_item(db, tool_args["item_name"], tool_args["unit"])
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
            days_info = f"，按消耗速度大概够用{int(remaining/avg_rate)}天"
        return json.dumps({"item": item.name, "quantity": tool_args["quantity"], "unit": tool_args["unit"], "remaining": round(remaining, 2), "days_info": days_info})

    elif tool_name == "record_consumption":
        item = _find_or_create_item(db, tool_args["item_name"], tool_args["unit"])
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
        return json.dumps({"item": item.name, "quantity": tool_args["quantity"], "unit": tool_args["unit"], "remaining": round(remaining, 2), "urgency": urgency})

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
            return json.dumps({"item": item.name, "remaining": round(remaining, 2), "unit": item.unit, "avg_daily_rate": round(avg_rate or 0, 3), "days_until_empty": days_until})
        else:
            overview = get_inventory_overview(db)
            items_info = [
                {"name": i.item_name, "remaining": round(i.remaining, 2), "unit": i.unit, "days_until_empty": i.days_until_empty}
                for i in overview
            ]
            return json.dumps({"items": items_info})

    elif tool_name == "check_restock_alerts":
        generate_restock_alerts(db)
        needing = get_items_needing_restock(db)
        alerts_info = [
            {"name": i.item_name, "remaining": round(i.remaining, 2), "unit": i.unit, "days_until_empty": i.days_until_empty}
            for i in needing
        ]
        return json.dumps({"need_restock": alerts_info})

    elif tool_name == "add_item":
        item = _find_or_create_item(db, tool_args["name"], tool_args["unit"], tool_args.get("category"), tool_args.get("target_audience", "all"))
        return json.dumps({"id": item.id, "name": item.name, "unit": item.unit})

    elif tool_name == "list_items":
        items = db.query(Item).all()
        items_info = [{"id": i.id, "name": i.name, "unit": i.unit, "target_audience": i.target_audience} for i in items]
        return json.dumps({"items": items_info})

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


def chat(db: Session, user_message: str) -> dict:
    """Process a chat message through the LLM agent."""
    client = _get_client()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    actions = []

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        tools=_build_tools(),
        tool_choice="auto",
    )

    # Handle tool calls
    while response.choices[0].message.tool_calls:
        tool_calls = response.choices[0].message.tool_calls
        messages.append(response.choices[0].message)

        for tc in tool_calls:
            tool_name = tc.function.name
            tool_args = json.loads(tc.function.arguments)
            result = _execute_tool(db, tool_name, tool_args)
            actions.append({"tool": tool_name, "args": tool_args, "result": result})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            tools=_build_tools(),
            tool_choice="auto",
        )

    reply = response.choices[0].message.content or ""
    return {"reply": reply, "actions": actions}
