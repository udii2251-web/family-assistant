# Web适配器 API 文档

## 概述

Web适配器提供REST API和WebSocket两种交互方式，支持Web前端与家庭管家系统进行实时交互。

## 架构设计

```
Web Frontend
    ↓ (REST/WebSocket)
Chat Router (backend/app/routers/chat.py)
    ↓
Orchestrator (意图路由)
    ↓
Skills (技能模块)
    ↓
UniversalCard (通用卡片格式)
    ↓
Web Adapter (backend/app/adapters/web_adapter.py)
    ↓
Web JSON (Web前端渲染)
```

## 文件结构

```
backend/
├── app/
│   ├── adapters/
│   │   ├── __init__.py
│   │   └── web_adapter.py          # Web卡片转换器
│   ├── routers/
│   │   └── chat.py                  # REST API + WebSocket
│   └── services/
│       ├── universal_card.py       # 通用卡片格式
│       └── orchestrator.py         # 意图路由
└── web_example.html                # 前端示例页面
```

## REST API

### 1. 发送消息

**POST** `/chat/web`

发送消息并获取响应。

**请求体：**
```json
{
  "message": "帮我查一下洗衣液的库存"
}
```

**响应：**
```json
{
  "success": true,
  "data": {
    "type": "restock_alert",
    "title": "🛒 补货提醒 — 洗衣液",
    "timestamp": "2024-01-15 14:30",
    "level": "warning",
    "color": "#fa8c16",
    "content": {
      "summary": {
        "remaining": 0.5,
        "unit": "L",
        "daysUntilEmpty": 3,
        "suggestedQuantity": 5.0
      },
      "products": [
        {
          "platform": "taobao",
          "platformName": "淘宝",
          "productName": "蓝月亮深层洁净洗衣液 5L装",
          "price": 59.9,
          "priceText": "¥59.9",
          "isBestPrice": true,
          "webUrl": "https://item.taobao.com/...",
          "deepLink": "taobao://..."
        }
      ]
    },
    "actions": [
      {
        "type": "link",
        "text": "一键下单·淘宝",
        "url": "https://item.taobao.com/...",
        "deepLink": "taobao://...",
        "style": "primary"
      },
      {
        "type": "callback",
        "text": "已补货 ✓",
        "style": "default",
        "data": {
          "action": "mark_done",
          "alert_id": "123"
        }
      }
    ]
  }
}
```

### 2. 处理卡片操作

**POST** `/chat/web/action`

处理用户点击卡片按钮的操作。

**请求体：**
```json
{
  "action": "mark_done",
  "alert_id": "123"
}
```

**响应：**
```json
{
  "success": true,
  "data": {
    "type": "simple_text",
    "title": "已补货",
    "timestamp": "2024-01-15 14:35",
    "level": "success",
    "color": "#52c41a",
    "content": {
      "text": "补货提醒\n\n已由家人确认补货完成。"
    },
    "actions": []
  }
}
```

## WebSocket API

### 连接

**WebSocket URL:** `ws://localhost:8000/chat/ws/{user_id}`

### 消息格式

#### 发送消息
```json
{
  "type": "message",
  "content": "帮我比价洗衣液"
}
```

#### 接收响应（卡片）
```json
{
  "type": "card",
  "data": { /* 卡片JSON */ }
}
```

#### 接收响应（文本）
```json
{
  "type": "text",
  "data": "好的，我来帮你查一下..."
}
```

#### 发送卡片操作
```json
{
  "type": "action",
  "data": {
    "action": "mark_done",
    "alert_id": "123"
  }
}
```

#### 接收错误
```json
{
  "type": "error",
  "data": "处理消息时出错: ..."
}
```

### 健康检查

**GET** `/chat/ws/health`

检查WebSocket服务状态。

**响应：**
```json
{
  "status": "healthy",
  "active_connections": 5
}
```

## 卡片类型

### 1. 补货提醒卡片 (restock_alert)

```json
{
  "type": "restock_alert",
  "title": "🛒 补货提醒 — 洗衣液",
  "timestamp": "2024-01-15 14:30",
  "level": "warning",
  "color": "#fa8c16",
  "content": {
    "summary": {
      "remaining": 0.5,
      "unit": "L",
      "daysUntilEmpty": 3,
      "suggestedQuantity": 5.0
    },
    "products": [...]
  },
  "actions": [...]
}
```

**Level:**
- `info` (蓝色): 7天以上
- `warning` (橙色): 3-7天
- `error` (红色): 3天以内

### 2. 库存概览卡片 (inventory_summary)

```json
{
  "type": "inventory_summary",
  "title": "📦 库存概览",
  "timestamp": "2024-01-15 14:30",
  "level": "info",
  "color": "#1890ff",
  "content": {
    "items": [
      {
        "name": "洗衣液",
        "remaining": 0.5,
        "unit": "L",
        "daysUntilEmpty": 3,
        "status": "urgent",
        "icon": "⚠️",
        "displayText": "⚠️ 洗衣液：剩余 0.5L，3天后用完"
      }
    ]
  },
  "actions": []
}
```

**Status:**
- `urgent`: 3天以内（红色）
- `warning`: 3-7天（橙色）
- `normal`: 7天以上（绿色）
- `unknown`: 未知（灰色）

### 3. 简单文本卡片 (simple_text)

```json
{
  "type": "simple_text",
  "title": "消息",
  "timestamp": "2024-01-15 14:30",
  "level": "info",
  "color": "#1890ff",
  "content": {
    "text": "好的，我来帮你查一下洗衣液的库存..."
  },
  "actions": []
}
```

### 4. 产品比价卡片 (product_comparison)

```json
{
  "type": "product_comparison",
  "title": "🔍 洗衣液 — 价格对比",
  "timestamp": "2024-01-15 14:30",
  "level": "info",
  "color": "#1890ff",
  "content": {
    "replyText": "我为你找到了以下选项：",
    "products": [
      {
        "platform": "taobao",
        "platformName": "淘宝",
        "productName": "蓝月亮深层洁净洗衣液 5L装",
        "price": 59.9,
        "priceText": "¥59.9",
        "isBestPrice": true,
        "webUrl": "https://item.taobao.com/...",
        "deepLink": "taobao://..."
      }
    ]
  },
  "actions": [...]
}
```

## 动作类型

### 1. 链接动作 (link)

打开URL或深度链接。

```json
{
  "type": "link",
  "text": "一键下单·淘宝",
  "url": "https://item.taobao.com/...",
  "deepLink": "taobao://...",
  "style": "primary"
}
```

**前端处理：**
```javascript
if (action.type === 'link') {
  // 优先尝试深度链接
  if (action.deepLink) {
    window.location.href = action.deepLink;
  } else {
    window.open(action.url, '_blank');
  }
}
```

### 2. 回调动作 (callback)

触发服务器端处理。

```json
{
  "type": "callback",
  "text": "已补货 ✓",
  "style": "default",
  "data": {
    "action": "mark_done",
    "alert_id": "123"
  }
}
```

**前端处理：**
```javascript
if (action.type === 'callback') {
  fetch('/chat/web/action', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(action.data),
  });
}
```

## 前端示例

### 1. REST API 示例

```javascript
async function sendMessage(message) {
  const response = await fetch('http://localhost:8000/chat/web', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message }),
  });

  const data = await response.json();
  if (data.success) {
    displayCard(data.data);
  }
}
```

### 2. WebSocket 示例

```javascript
// 连接WebSocket
const ws = new WebSocket('ws://localhost:8000/chat/ws/user123');

ws.onopen = () => {
  console.log('WebSocket connected');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'card') {
    displayCard(data.data);
  } else if (data.type === 'text') {
    displayText(data.data);
  }
};

// 发送消息
ws.send(JSON.stringify({
  type: 'message',
  content: '帮我查一下洗衣液的库存',
}));

// 发送卡片操作
ws.send(JSON.stringify({
  type: 'action',
  data: {
    action: 'mark_done',
    alert_id: '123',
  },
}));
```

## 测试

### 1. 启动后端服务

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 2. 打开前端示例

在浏览器中打开 `backend/web_example.html`

### 3. 测试场景

1. **库存查询**
   - 输入："帮我查一下洗衣液的库存"
   - 预期：返回库存概览卡片

2. **产品比价**
   - 输入："帮我比价洗衣液"
   - 预期：返回产品比价卡片，带有购买链接

3. **补货确认**
   - 点击卡片上的"已补货"按钮
   - 预期：调用回调API，更新卡片为"已补货"状态

4. **WebSocket模式**
   - 切换到WebSocket模式
   - 输入消息，观察实时响应

## 集成到现有项目

### 1. React组件示例

```jsx
import React, { useState, useEffect } from 'react';

function FamilyAssistant() {
  const [ws, setWs] = useState(null);
  const [messages, setMessages] = useState([]);

  useEffect(() => {
    const websocket = new WebSocket('ws://localhost:8000/chat/ws/user123');

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMessages(prev => [...prev, data]);
    };

    setWs(websocket);

    return () => websocket.close();
  }, []);

  const sendMessage = (message) => {
    ws.send(JSON.stringify({
      type: 'message',
      content: message,
    }));
  };

  return (
    <div>
      {/* 渲染消息列表 */}
      {messages.map((msg, idx) => (
        <Card key={idx} data={msg.data} />
      ))}

      {/* 输入框 */}
      <input
        onKeyPress={(e) => {
          if (e.key === 'Enter') {
            sendMessage(e.target.value);
            e.target.value = '';
          }
        }}
      />
    </div>
  );
}
```

### 2. Vue组件示例

```vue
<template>
  <div>
    <!-- 消息列表 -->
    <div v-for="(msg, idx) in messages" :key="idx">
      <Card :data="msg.data" />
    </div>

    <!-- 输入框 -->
    <input
      @keypress.enter="sendMessage"
      v-model="inputMessage"
    />
  </div>
</template>

<script>
export default {
  data() {
    return {
      ws: null,
      messages: [],
      inputMessage: '',
    };
  },
  mounted() {
    this.ws = new WebSocket('ws://localhost:8000/chat/ws/user123');

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.messages.push(data);
    };
  },
  methods: {
    sendMessage() {
      this.ws.send(JSON.stringify({
        type: 'message',
        content: this.inputMessage,
      }));
      this.inputMessage = '';
    },
  },
};
</script>
```

## 注意事项

1. **用户身份认证**
   - 当前示例使用简单的user_id
   - 生产环境需要集成真实的用户认证系统

2. **会话管理**
   - 每个用户有独立的会话历史
   - 会话存储在内存中，重启服务会丢失

3. **错误处理**
   - 所有API都有try-catch错误处理
   - WebSocket连接断开会自动重连（需要前端实现）

4. **性能优化**
   - 会话历史限制在最近10条消息
   - WebSocket连接有健康检查端点

## 后续优化方向

1. **持久化存储**
   - 使用Redis存储会话，支持多实例部署

2. **用户认证**
   - 集成JWT或OAuth认证

3. **消息队列**
   - 使用RabbitMQ处理异步任务

4. **流式响应**
   - 支持Server-Sent Events (SSE)
   - 实现打字机效果的流式响应

5. **富文本支持**
   - 支持Markdown渲染
   - 支持图片、文件等多媒体内容

6. **多语言支持**
   - 国际化卡片内容
   - 根据用户语言偏好调整响应