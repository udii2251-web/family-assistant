"""独立测试脚本：验证飞书 WebSocket 长连接是否能成功建立。

用法：
  python3 test_ws_connection.py

脚本会自动从 .env 文件加载凭证，也支持通过环境变量覆盖。
"""

import os
import sys
import time
import asyncio

from dotenv import load_dotenv
from pathlib import Path

# Load .env file
load_dotenv(Path(__file__).parent / ".env")

import lark_oapi as lark

APP_ID = os.getenv("FEISHU_APP_ID", "")
APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")

if not APP_ID or not APP_SECRET:
    print("❌ 请先设置环境变量 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
    print("   例如：export FEISHU_APP_ID='cli_xxxx'")
    print("   例如：export FEISHU_APP_SECRET='xxxx'")
    sys.exit(1)

print(f"App ID: {APP_ID}")
print(f"正在建立飞书 WebSocket 长连接...")

# 注册一个简单的消息处理器，用来确认连接是否工作
def on_message(data):
    """收到消息时打印日志"""
    print(f"✅ 收到消息事件！连接正常工作。")
    print(f"   来自: {data.event.sender.sender_id.open_id}")
    print(f"   内容: {data.event.message.content[:100]}")

event_handler = lark.EventDispatcherHandler.builder("", "") \
    .register_p2_im_message_receive_v1(on_message) \
    .build()

# 创建 WebSocket 客户端
ws_client = lark.ws.Client(
    app_id=APP_ID,
    app_secret=APP_SECRET,
    log_level=lark.LogLevel.DEBUG,
    event_handler=event_handler,
)

# 在新 event loop 中启动（避免与 uvicorn 冲突）
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

try:
    loop.run_until_complete(ws_client._connect())
    print("✅ WebSocket 连接已建立！")
    print("   现在可以在飞书开放平台点击 '验证连接状态' 了。")
    print("   验证成功后，可以 Ctrl+C 停止此脚本。")
    print("   连接保持活跃中，等待消息...")
    loop.run_forever()
except Exception as e:
    print(f"❌ 连接失败: {e}")
    print("   可能原因:")
    print("   1. App ID 或 App Secret 不正确")
    print("   2. 应用未发布版本")
    print("   3. 机器人能力未添加")
    print("   4. 事件订阅未配置长连接模式")
    sys.exit(1)
