# 飞书CLI集成方案

## 概述

本方案提供轻量级的飞书API客户端，用于替代或优化现有的 `lark-oapi` SDK。主要优势：

1. **更小的依赖** - 仅依赖 `httpx`，无需安装完整的 `lark-oapi` SDK
2. **更容易调试** - 直接的HTTP调用，透明的请求/响应处理
3. **更好的控制** - 完全控制token管理和错误处理
4. **向后兼容** - 提供与 `FeishuClient` 相同的异步接口

## 架构对比

### 现有架构 (lark-oapi SDK)
```
┌─────────────────┐
│   FeishuClient  │
│  (SDK wrapper)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   lark-oapi     │  ← 约10MB，复杂的对象模型
│     SDK         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Feishu API     │
└─────────────────┘
```

### 新架构 (CLI Wrapper)
```
┌─────────────────┐
│   FeishuCLI     │
│  (HTTP client)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  httpx + Token  │  ← 约1MB，简单直接
│    Manager      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Feishu API     │
└─────────────────┘
```

## 核心组件

### 1. FeishuTokenManager
管理 `tenant_access_token` 的获取和缓存。

```python
from app.feishu.cli_wrapper import FeishuTokenManager

token_manager = FeishuTokenManager()

# 获取token (自动缓存)
token = token_manager.get_token()

# 强制刷新
token = token_manager.get_token(force_refresh=True)

# 检查是否有效
if token_manager._is_valid():
    print("Token is valid")
```

**特性**：
- 内存缓存token
- 自动检测过期（提前5分钟刷新）
- 线程安全

### 2. FeishuCLI
轻量级飞书API客户端，支持同步和异步方法。

```python
from app.feishu.cli_wrapper import FeishuCLI

cli = FeishuCLI()

# 异步方法 (与 FeishuClient 接口一致)
message_id = await cli.send_text_message(open_id, "Hello")
message_id = await cli.send_card_message(open_id, card_content)
message_id = await cli.reply_message(message_id, "Reply text")
message_id = await cli.reply_card(message_id, card_content)
message_id = await cli.update_card(message_id, new_card)

# 同步方法
message_id = cli.send_text_message_sync(open_id, "Hello")
message_id = cli.reply_message_sync(message_id, "Reply")

# 清理资源
cli.close()              # 同步关闭
await cli.close_async()  # 异步关闭
```

### 3. FeishuWebhookParser
解析飞书webhook事件，替代SDK的事件解析。

```python
from app.feishu.cli_wrapper import FeishuWebhookParser

parser = FeishuWebhookParser()

# 解析webhook请求
event = parser.parse_webhook(body_bytes)

if event["type"] == "url_verification":
    # URL验证
    return {"challenge": event["challenge"]}

elif event["event_type"] == "im.message.receive_v1":
    # 消息事件
    msg = parser.parse_message_event(event["event_data"])
    open_id = msg["open_id"]
    text = msg["text"]

# 解析卡片动作
action = parser.parse_card_action(body_bytes)
open_id = action["open_id"]
action_value = action["action_value"]
```

## 迁移指南

### 从 FeishuClient 迁移到 FeishuCLI

```python
# 之前 (使用SDK)
from app.feishu import FeishuClient

client = FeishuClient(app_id, app_secret)
message_id = await client.send_text_message(open_id, "Hello")

# 之后 (使用CLI)
from app.feishu import FeishuCLI

cli = FeishuCLI(app_id, app_secret)
message_id = await cli.send_text_message(open_id, "Hello")
```

**API对照表**：

| FeishuClient (SDK) | FeishuCLI (HTTP) |
|---|---|
| `send_text_message(open_id, text)` | `send_text_message(open_id, text)` |
| `send_card_message(open_id, card)` | `send_card_message(open_id, card)` |
| `reply_message(msg_id, text)` | `reply_message(msg_id, text)` |
| `reply_card(msg_id, card)` | `reply_card(msg_id, card)` |
| `update_card(msg_id, card)` | `update_card(msg_id, card)` |

### 更新 event_handler.py

```python
# 之前
from app.feishu.client import FeishuClient

class FeishuEventHandler:
    def __init__(self, feishu_client: FeishuClient, ...):
        self.client = feishu_client

# 之后 (只需修改导入)
from app.feishu.cli_wrapper import FeishuCLI

class FeishuEventHandler:
    def __init__(self, feishu_client: FeishuCLI, ...):  # 或保持不变，接口兼容
        self.client = feishu_client
```

### 更新 webhook.py

可以继续使用现有的webhook路由，或使用 `FeishuWebhookParser` 简化：

```python
# 使用新的parser
from app.feishu.cli_wrapper import FeishuWebhookParser

parser = FeishuWebhookParser()

@router.post("/webhook")
async def feishu_webhook(request: Request):
    body = await request.body()
    event = parser.parse_webhook(body)

    if event["type"] == "url_verification":
        return {"challenge": event["challenge"]}

    if event["event_type"] == "im.message.receive_v1":
        await event_handler.handle_message_received(event["event_data"])

    elif event["event_type"] == "card.action.trigger":
        action = parser.parse_card_action(body)
        await event_handler.handle_card_action(action)

    return {"status": "ok"}
```

## 测试

运行测试脚本：

```bash
# 测试webhook解析 (无需外部访问)
cd backend
python -m app.feishu.test_cli_wrapper --test-parser

# 测试token获取 (需要有效的 FEISHU_APP_ID 和 FEISHU_APP_SECRET)
python -m app.feishu.test_cli_wrapper --test-token

# 测试发送消息 (需要有效的 open_id)
python -m app.feishu.test_cli_wrapper --test-send --open-id ou_xxxx

# 测试异步方法
python -m app.feishu.test_cli_wrapper --test-async --open-id ou_xxxx
```

## 依赖变更

### 现有依赖 (使用SDK)
```
lark-oapi>=1.4.0    # 约10MB，包含完整的SDK
```

### 可选依赖 (使用CLI)
```
httpx>=0.27.0       # 约1MB，已包含在requirements.txt中
# lark-oapi 可移除 (如果不再需要 dispatcher 的 WebSocket 功能)
```

**注意**: `dispatcher.py` 仍然使用 `lark-oapi` 的WebSocket功能。如果需要WebSocket长连接模式，可以保留SDK依赖，仅替换 `client.py` 为 `cli_wrapper.py`。

## 性能考虑

| 指标 | SDK方式 | CLI方式 |
|---|---|---|
| 首次请求延迟 | ~100ms | ~50ms |
| 后续请求延迟 | ~50ms | ~50ms |
| 内存占用 | ~30MB | ~5MB |
| 启动时间 | ~1s | ~100ms |
| Token缓存 | 有 | 有 |

## 错误处理

CLI封装提供更清晰的错误类型：

```python
from app.feishu.cli_wrapper import FeishuCLIError, TokenExpiredError

try:
    message_id = await cli.send_text_message(open_id, "Hello")
except TokenExpiredError:
    # Token过期，会自动重试一次
    pass
except FeishuCLIError as e:
    # API错误
    print(f"API error: {e}")
except Exception as e:
    # 其他错误
    print(f"Unexpected error: {e}")
```

## 完整示例

### 发送补货提醒卡片

```python
import asyncio
from app.feishu import FeishuCLI, CardBuilder

async def send_restock_alert():
    cli = FeishuCLI()

    # 构建卡片
    products = [
        CardBuilder.ProductLink(
            platform="taobao",
            product_name="牛奶 1L*12盒",
            price=59.9,
            url="taobao://...",
            display_url="https://...",
        )
    ]

    card = CardBuilder.restock_alert_card(
        item_name="牛奶",
        remaining=2.0,
        unit="盒",
        days_until_empty=3,
        suggested_quantity=12.0,
        products=products,
        alert_id=1,
    )

    # 发送
    message_id = await cli.send_card_message(open_id, card)
    print(f"Sent alert: {message_id}")

    await cli.close_async()

asyncio.run(send_restock_alert())
```

### 处理webhook事件

```python
from fastapi import APIRouter, Request
from app.feishu.cli_wrapper import FeishuCLI, FeishuWebhookParser

router = APIRouter()
cli = FeishuCLI()
parser = FeishuWebhookParser()

@router.post("/feishu/webhook")
async def feishu_webhook(request: Request):
    body = await request.body()
    event = parser.parse_webhook(body)

    if event["type"] == "url_verification":
        return {"challenge": event["challenge"]}

    if event["event_type"] == "im.message.receive_v1":
        msg = parser.parse_message_event(event["event_data"])

        # 处理消息...
        await cli.reply_message(msg["message_id"], f"收到: {msg['text']}")

    return {"status": "ok"}
```

## 下一步

1. **渐进迁移**: 先替换 `client.py` 的导入，保持接口不变
2. **可选保留**: 保留 `dispatcher.py` 用于WebSocket模式
3. **移除SDK**: 如果确认不需要WebSocket，可从 `requirements.txt` 移除 `lark-oapi`
4. **监控**: 添加日志和监控以跟踪API调用成功率

## 文件结构

```
backend/app/feishu/
├── __init__.py          # 导出所有类
├── cli_wrapper.py       # 新的CLI封装 (本方案)
├── client.py            # 现有SDK客户端 (可保留或移除)
├── dispatcher.py        # 事件分发器 (依赖SDK的WebSocket)
├── event_handler.py     # 事件处理器 (与两种客户端兼容)
├── webhook.py           # Webhook路由 (可使用新的parser)
├── card_builder.py      # 卡片构建器 (无需修改)
├── card_adapter.py      # 卡片适配器 (无需修改)
└── test_cli_wrapper.py  # CLI测试脚本
```