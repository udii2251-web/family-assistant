"""Taobao Agent Tools — sync_orders, query_orders, login, etc.

Provides Agent Tools for Feishu integration:
- sync_taobao_orders: Sync last 7 days orders
- query_taobao_orders: Query synced orders
- check_taobao_login: Check login status
- login_taobao: Trigger QR code login
"""

import logging
from typing import List, Dict, Any

from sqlalchemy.orm import Session

from app.modules.taobao.auth import taobao_auth_manager
from app.modules.taobao.sync import taobao_sync_manager

logger = logging.getLogger(__name__)


def get_taobao_tools() -> List[Dict[str, Any]]:
    """Return Taobao-related Agent Tools.

    Returns:
        List of tool definitions for LLM
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "sync_taobao_orders",
                "description": "同步最近7天的淘宝订单，将订单数据保存到数据库。用户请求同步淘宝订单时调用此工具。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "number",
                            "description": "同步最近N天的订单，默认7天"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_taobao_orders",
                "description": "查询已同步的淘宝订单数据。用户想查看淘宝订单时调用此工具。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "number",
                            "description": "查询最近N天的订单，默认7天"
                        },
                        "status": {
                            "type": "string",
                            "description": "订单状态筛选（可选）：pending_payment（待付款）、pending_shipment（待发货）、shipped（已发货）、completed（已完成）、closed（已关闭）"
                        },
                        "limit": {
                            "type": "number",
                            "description": "返回订单数量上限，默认10"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "check_taobao_login",
                "description": "检查淘宝账号登录状态。用户想了解淘宝登录情况时调用此工具。",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "login_taobao",
                "description": "触发淘宝账号登录（会显示二维码供用户扫码）。用户需要登录淘宝或登录已失效时调用此工具。",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    ]


async def execute_taobao_tool(db: Session, tool_name: str, tool_args: Dict[str, Any]) -> str:
    """Execute a Taobao tool and return result.

    Args:
        db: Database session
        tool_name: Name of tool to execute
        tool_args: Tool arguments

    Returns:
        str: Result message
    """
    try:
        if tool_name == "sync_taobao_orders":
            return await _sync_taobao_orders(db, tool_args)
        elif tool_name == "query_taobao_orders":
            return await _query_taobao_orders(db, tool_args)
        elif tool_name == "check_taobao_login":
            return await _check_taobao_login(db, tool_args)
        elif tool_name == "login_taobao":
            return await _login_taobao(db, tool_args)
        else:
            return f"未知的淘宝工具: {tool_name}"

    except Exception as e:
        logger.error(f"Error executing Taobao tool {tool_name}: {e}")
        return f"执行工具失败: {str(e)}"


async def _sync_taobao_orders(db: Session, args: Dict[str, Any]) -> str:
    """Sync Taobao orders.

    Args:
        db: Database session
        args: Tool arguments (days)

    Returns:
        str: Sync result message
    """
    days = args.get('days', 7)

    logger.info(f"Syncing Taobao orders for last {days} days")

    result = await taobao_sync_manager.sync_orders(days=days)

    if result['success']:
        return (
            f"✅ 淘宝订单同步成功！\n\n"
            f"同步时间范围：最近{days}天\n"
            f"总订单数：{result['total_orders']}个\n"
            f"新增订单：{result['new_orders']}个\n"
            f"更新订单：{result['updated_orders']}个"
        )
    else:
        return f"❌ 订单同步失败：{result['message']}"


async def _query_taobao_orders(db: Session, args: Dict[str, Any]) -> str:
    """Query Taobao orders from database.

    Args:
        db: Database session
        args: Tool arguments (days, status, limit)

    Returns:
        str: Query result message
    """
    days = args.get('days', 7)
    status = args.get('status')
    limit = args.get('limit', 10)

    logger.info(f"Querying Taobao orders: days={days}, status={status}, limit={limit}")

    orders = taobao_sync_manager.get_orders_from_db(
        days=days,
        status=status,
        limit=limit
    )

    if not orders:
        return f"未查询到最近{days}天的淘宝订单数据"

    # Format response
    status_names = {
        'pending_payment': '待付款',
        'pending_shipment': '待发货',
        'shipped': '已发货',
        'received': '已签收',
        'completed': '已完成',
        'closed': '已关闭',
        'refunding': '退款中',
    }

    message_lines = [
        f"📦 最近{days}天淘宝订单（共{len(orders)}个）：\n"
    ]

    for i, order in enumerate(orders[:10], 1):
        status_name = status_names.get(order['status'], order['status'])
        order_time = order['order_time']
        if order_time:
            # Format datetime
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(order_time)
                order_time_str = dt.strftime('%Y-%m-%d %H:%M')
            except:
                order_time_str = order_time[:16]
        else:
            order_time_str = '未知时间'

        message_lines.append(
            f"{i}. 【{status_name}】{order['product_name'][:30]}\n"
            f"   店铺：{order['shop_name']}\n"
            f"   金额：¥{order['total_price']:.2f}\n"
            f"   时间：{order_time_str}\n"
            f"   订单号：{order['order_id']}\n"
        )

    if len(orders) > 10:
        message_lines.append(f"... 还有 {len(orders) - 10} 个订单未显示")

    return "\n".join(message_lines)


async def _check_taobao_login(db: Session, args: Dict[str, Any]) -> str:
    """Check Taobao login status.

    Args:
        db: Database session
        args: Tool arguments (empty)

    Returns:
        str: Login status message
    """
    logger.info("Checking Taobao login status")

    status = await taobao_auth_manager.check_login_status()

    if status['is_logged_in'] and not status['needs_reauth']:
        message = (
            f"✅ 淘宝账号已登录\n\n"
            f"账号：{status['user_nick'] or '未知'}\n"
        )

        if status['last_login_time']:
            from datetime import datetime
            login_time = status['last_login_time']
            if isinstance(login_time, datetime):
                login_time_str = login_time.strftime('%Y-%m-%d %H:%M')
            else:
                login_time_str = str(login_time)
            message += f"登录时间：{login_time_str}\n"

        if status['expiry_time']:
            from datetime import datetime
            expiry_time = status['expiry_time']
            if isinstance(expiry_time, datetime):
                expiry_time_str = expiry_time.strftime('%Y-%m-%d %H:%M')
            else:
                expiry_time_str = str(expiry_time)
            message += f"过期时间：{expiry_time_str}\n"

        return message

    elif status['needs_reauth']:
        return (
            f"⚠️ 淘宝账号登录已失效\n\n"
            f"状态：{status['message']}\n\n"
            f"请回复「登录淘宝」重新授权。"
        )

    else:
        return (
            f"❌ 淘宝账号未登录\n\n"
            f"请回复「登录淘宝」进行授权。"
        )


async def _login_taobao(db: Session, args: Dict[str, Any]) -> str:
    """Trigger Taobao login.

    Args:
        db: Database session
        args: Tool arguments (empty)

    Returns:
        str: Login instruction message
    """
    logger.info("Triggering Taobao login")

    # Check if already logged in
    status = await taobao_auth_manager.check_login_status()

    if status['is_logged_in'] and not status['needs_reauth']:
        return (
            f"✅ 淘宝账号已登录\n\n"
            f"账号：{status['user_nick'] or '未知'}\n"
            f"无需重复登录。如需切换账号，请先登出。"
        )

    # 直接在当前async上下文中运行登录流程
    # execute_tool的ThreadPoolExecutor已经处理了async到sync的转换
    try:
        result = await taobao_auth_manager.login_with_qrcode(headless=False)
        logger.info(f"Login result: {result}")

        if result['success']:
            return (
                f"✅ 淘宝登录成功！\n\n"
                f"账号：{result.get('user_nick', '未知')}\n\n"
                f"💡 系统会自动同步最近7天的订单。"
            )
        else:
            return (
                f"❌ 淘宝登录失败\n\n"
                f"原因：{result['message']}\n\n"
                f"请重试或检查网络连接。"
            )
    except Exception as e:
        logger.error(f"Login failed: {e}", exc_info=True)
        return f"❌ 登录过程出错：{str(e)}"


class TaobaoSkill:
    """Taobao skill for integration with orchestrator.

    This class provides the interface expected by the orchestrator
    for handling Taobao-related tasks.
    """

    @property
    def name(self) -> str:
        """Skill name."""
        return "taobao"

    @property
    def description(self) -> str:
        """Skill description."""
        return "淘宝订单同步与查询功能"

    @property
    def system_prompt(self) -> str:
        """System prompt for this skill."""
        return """你是家庭管家助手，负责处理淘宝订单相关的任务。

你可以帮助用户：
1. 同步淘宝订单数据（最近7天）
2. 查询已同步的淘宝订单
3. 检查淘宝账号登录状态
4. 触发淘宝账号登录

使用工具时请注意：
- sync_taobao_orders：同步订单数据，会从淘宝网站抓取最近N天的订单
- query_taobao_orders：查询已保存的订单数据，不会访问淘宝网站
- check_taobao_login：检查登录状态，确认是否能同步订单
- login_taobao：触发登录流程，需要用户扫码授权

如果用户未登录或登录已失效，提示用户先登录再同步订单。"""

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tool definitions for this skill."""
        return get_taobao_tools()

    def execute_tool(self, db: Session, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """Execute a tool for this skill.

        Args:
            db: Database session
            tool_name: Name of tool to execute
            tool_args: Tool arguments

        Returns:
            str: Tool execution result
        """
        import asyncio

        # Check if we're already in an async context
        try:
            loop = asyncio.get_running_loop()
            # We're in async context - need to run in thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    execute_taobao_tool(db, tool_name, tool_args)
                )
                return future.result()
        except RuntimeError:
            # No running loop - safe to create new one
            return asyncio.run(execute_taobao_tool(db, tool_name, tool_args))

    def format_response(self, reply: str, actions: List[Dict], context: Dict) -> Dict:
        """Format response for Feishu.

        Args:
            reply: LLM reply text
            actions: List of tool actions taken
            context: Context information (e.g., open_id)

        Returns:
            Dict: Formatted response for Feishu
        """
        # Simple text response
        return {
            "type": "text",
            "content": reply
        }


# Export for module interface
__all__ = [
    'get_taobao_tools',
    'execute_taobao_tool',
    'TaobaoSkill'
]