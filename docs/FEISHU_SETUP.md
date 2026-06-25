# 飞书 Bot 搭建指南

本指南帮助你从零开始搭建家庭管家 Agent 的飞书机器人。

## 1. 创建飞书开发者账号

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 使用飞书账号登录（如没有飞书账号，先注册一个）
3. 进入开发者后台

## 2. 创建企业自建应用

1. 在开发者后台点击 **创建应用**
2. 选择 **企业自建应用** 类型
3. 填写应用信息：
   - 应用名称：`家庭管家`（或你喜欢的名称）
   - 应用描述：`家庭日用品库存管理、补货提醒和商品比价助手`
   - 应用图标：选择一个合适的图标

## 3. 添加机器人能力

1. 进入应用管理页面
2. 点击 **添加应用能力**
3. 选择 **机器人** 能力
4. 设置机器人名称和描述

## 4. 配置权限

1. 进入 **权限管理** 页面
2. 添加以下权限：
   - `im:message` — 获取与发送单聊、群组消息
   - `im:message:send_as_bot` — 以应用的身份发消息
   - `im:chat` — 获取群组信息
3. 点击 **发布新版本** 使权限生效

## 5. 配置事件订阅

1. 进入 **开发配置 → 事件订阅**
2. 添加事件：
   - `im.message.receive_v1` — 接收消息
   - `card.action.trigger` — 卡片按钮回调
3. 配置请求地址：
   - **Webhook 模式**：填入 `https://your-domain/feishu/webhook`
   - **WebSocket 模式**：无需公网地址，适合本地开发
4. URL 验证：Feishu 会发送一个验证请求，你的服务器需要返回 `challenge` 响应

## 6. 获取应用凭证

1. 进入 **凭证与基础信息** 页面
2. 记录以下信息：
   - **App ID**（格式如 `cli_xxxxx`）
   - **App Secret**
3. 在 **事件订阅** 页面记录：
   - **Verification Token**
   - **Encrypt Key**（可选）

## 7. 配置环境变量

1. 复制 `.env.example` 为 `.env`：
   ```bash
   cp .env.example .env
   ```
2. 填入你的实际凭证值：
   ```env
   FEISHU_APP_ID=cli_你的AppID
   FEISHU_APP_SECRET=你的AppSecret
   FEISHU_VERIFICATION_TOKEN=你的Token
   SEARCH_API_KEY=你的BingSearchKey
   LLM_API_KEY=你的LLM_API密钥
   ```

## 8. 启动服务

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

## 9. 测试

1. 在飞书桌面端/移动端搜索你创建的机器人
2. 发送一条私聊消息，如 "大米还剩多少"
3. 验证收到回复

## 10. WebSocket 模式（本地开发推荐）

如果暂时没有公网域名，可以使用 WebSocket 模式进行本地开发：

1. 在 `.env` 中设置 `FEISHU_MODE=websocket`
2. 使用飞书 SDK 的 WebSocket 客户端连接
3. 无需配置 webhook URL

## Bing Search API 配置

1. 访问 [Azure Portal](https://portal.azure.com/)
2. 创建 Bing Search v7 资源
3. 获取 API Key
4. 填入 `.env` 的 `SEARCH_API_KEY`

## 注意事项

- 飞书应用需要发布版本后权限才能生效
- 机器人必须被用户搜索并添加后才能私聊
- 深链接（`taobao://`、`openapp.jdmobile://`）需要手机上安装对应 App 才能跳转
- Feishu 可能会在某些环境下拦截 URL Scheme，此时会 fallback 到 web URL
