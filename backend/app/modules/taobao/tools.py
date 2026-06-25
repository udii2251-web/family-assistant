"""Taobao Agent Tools — sync_orders, query_orders, login, etc.

Provides Agent Tools for Feishu integration:
- sync_taobao_orders: Sync last 7 days orders
- query_taobao_orders: Query synced orders
- check_taobao_login: Check login status
- login_taobao: Trigger QR code login
"""

def get_taobao_tools():
    """Return Taobao-related Agent Tools.

    Placeholder implementation — Session B will implement actual tools.

    Returns:
        Empty list (placeholder)
    """
    return []

# Placeholder tool definitions (Session B will implement):
# tools = [
#     {
#         "type": "function",
#         "function": {
#             "name": "sync_taobao_orders",
#             "description": "同步最近7天的淘宝订单",
#             "parameters": {"type": "object", "properties": {}, "required": []}
#         }
#     },
#     {
#         "type": "function",
#         "function": {
#             "name": "query_taobao_orders",
#             "description": "查询已同步的淘宝订单",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "days": {"type": "number", "description": "查询最近N天订单"}
#                 },
#                 "required": []
#             }
#         }
#     },
#     {
#         "type": "function",
#         "function": {
#             "name": "check_taobao_login",
#             "description": "检查淘宝登录状态",
#             "parameters": {"type": "object", "properties": {}, "required": []}
#         }
#     },
#     {
#         "type": "function",
#         "function": {
#             "name": "login_taobao",
#             "description": "重新登录淘宝账号（触发二维码展示）",
#             "parameters": {"type": "object", "properties": {}, "required": []}
#         }
#     }
# ]