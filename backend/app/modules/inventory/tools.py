"""Inventory module Agent Tools.

Extracted from app/skills/shopping.py get_tools() method.

Contains 8 Agent Tools for inventory management:
1. record_purchase - 记录购买（增加库存）
2. record_consumption - 记录消耗（减少库存）
3. query_inventory - 查询库存
4. check_restock_alerts - 查看补货提醒
5. add_item - 添加物品类型
6. list_items - 列出所有物品
7. search_products - 搜索商品比价
8. compare_products - 对比商品价格
"""


def get_inventory_tools():
    """Return inventory-related Agent Tools for LLM function calling.

    Returns:
        List of tool definitions in OpenAI-compatible format.
    """
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
        {
            "type": "function",
            "function": {
                "name": "search_products",
                "description": "搜索商品并比较各平台价格，返回淘宝、京东、拼多多的比价信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item_name": {"type": "string", "description": "物品名称"},
                        "quantity": {"type": "number", "description": "建议购买数量(可选)"},
                        "unit": {"type": "string", "description": "单位(可选)"},
                    },
                    "required": ["item_name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "compare_products",
                "description": "对比商品在不同平台的价格，提供购买建议和链接",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item_name": {"type": "string", "description": "物品名称"},
                        "quantity": {"type": "number", "description": "购买数量(可选)"},
                        "unit": {"type": "string", "description": "单位(可选)"},
                    },
                    "required": ["item_name"],
                },
            },
        },
    ]