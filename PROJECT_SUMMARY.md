# 家庭管家系统 - 项目完整文档

> 本文档为新接手的AI或开发者提供项目的全面背景，包括产品目标、实现情况、踩坑总结和开发经验。

---

## 一、产品目标

### 核心定位
家庭日用品智能管理助手，通过飞书机器人交互，帮助家庭追踪库存、预测补货时机、提供商品比价建议。

### 目标用户
- **核心用户场景**：飞书机器人聊天交互（Web前端仅用于管理员调试）
- **家庭构成**：4个大人、1个小孩、2只小狗（配置示例）

### 核心价值
1. **智能库存追踪**：自动计算采购-消耗，预测耗尽日期
2. **主动补货提醒**：每日定时检查，发现库存不足主动推送飞书卡片
3. **商品比价建议**：搜索淘宝/京东/拼多多，提供最划算的购买链接
4. **自然语言交互**：用户说"买了5kg大米"，系统自动记录并更新库存

### 交互方式
- **主要界面**：飞书机器人聊天框（私聊）
- **次要界面**：Web前端（仅管理员调试，用户不使用）
- **触发方式**：
  - 用户主动消息（聊天）
  - 定时主动提醒（每日检查）

---

## 二、实现情况

### 已完成功能 ✅

#### 1. 后端核心功能
| 模块 | 功能 | 完成度 |
|------|------|--------|
| 数据模型 | 7个完整模型（FamilyMember, Item, PurchaseRecord, ConsumptionRecord, RestockAlert等） | 100% |
| API路由 | 6个完整路由（family, items, inventory, alerts, consumption, purchases） | 100% |
| 库存计算 | 自动计算采购-消耗，预测耗尽日期 | 100% |
| 补货提醒 | 生成提醒（threshold=3天），建议补货量（14天用量） | 100% |

#### 2. 飞书机器人集成 ✅
| 功能 | 完成度 | 备注 |
|------|--------|------|
| WebSocket连接 | 100% | 双模式支持（websocket/webhook） |
| 消息接收处理 | 100% | 自然语言解析+LLM调度 |
| 交互式卡片 | 100% | 补货提醒卡片+商品比价卡片 |
| 卡片按钮回调 | 100% | **已修复关键bug** |
| 定时提醒 | 100% | 每日自动检查推送 |

#### 3. LLM Agent ✅
- OpenAI兼容接口（DeepSeek实际使用）
- 6个基础工具：record_purchase, record_consumption, query_inventory, check_restock_alerts, add_item, list_items
- 2个商品搜索工具：search_products, compare_products（占位实现）

#### 4. 技能框架 ✅
- ShoppingSkill：购物相关所有功能
- 可扩展架构：BaseSkill抽象类

### 部分完成功能 🔄

| 功能 | 状态 | 说明 |
|------|------|------|
| 商品搜索API | 70% | 卡片UI完成，真实API待接入（Bing搜索占位） |
| 单位转换 | 0% | 用户说"2斤"无法识别为"1kg"，需添加映射 |

### 未实现功能 ❌

- 高级分析：消耗趋势图表、异常检测
- 智能推荐：批量采购建议、价格历史监控
- 多人协作：任务分配、审核流程
- 数据管理：Excel导入导出、备份恢复

---

## 三、技术架构

### 后端架构
```
backend/
├── app/
│   ├── main.py               # FastAPI入口，lifespan管理
│   ├── routers/              # REST API路由（6个模块）
│   ├── models/               # SQLAlchemy数据模型（7个）
│   ├── services/
│   │   ├── orchestrator.py   # 飞书消息调度器
│   │   ├── agent.py          # LLM Agent（旧版）
│   │   ├── inventory.py      # 库存计算核心逻辑
│   │   ├── alert_scheduler.py # 提醒生成逻辑
│   │   ├── trigger_engine.py # 定时触发引擎
│   │   ├── product_search.py # 商品搜索（占位）
│   │   └── session.py        # 会话管理
│   ├── skills/
│   │   ├── base.py           # 技能抽象基类
│   │   └ shopping.py         # 购物技能（主要实现）
│   ├── feishu/
│   │   ├── client.py         # 飞书API客户端
│   │   ├── dispatcher.py     # WebSocket/Webhook事件分发 **关键模块**
│   │   ├── event_handler.py  # 事件处理 **关键模块**
│   │   ├── card_builder.py   # 卡片构建器
│   │   ├── webhook.py        # Webhook路由（备用）
│   └── database.py           # SQLite数据库
```

### 前端架构（不重要）
```
frontend/  # 仅管理员调试，用户不使用
├── src/pages/
│   ├── ChatPage.tsx
│   ├── InventoryPage.tsx
│   ├── AlertsPage.tsx  # 此页面修改对用户无用
│   ├── ItemsPage.tsx
│   └ SettingsPage.tsx
```

### 飞书交互流程
```
用户消息 → WebSocket → dispatcher → event_handler → orchestrator → skill →
LLM调用 → 工具执行 → 返回结果 → 飞书client → 卡片回复
```

---

## 四、开发踩坑总结 ⚠️（重点）

> 本节详细记录开发过程中踩过的坑，供后来者参考，避免重复踩坑。

### 踩坑1: 前端页面修改对用户无用 ❌

**问题描述**：
- 初始开发时，修改了前端AlertsPage.tsx，添加Toast提示、动画效果
- 用户反馈："我的主要界面在飞书机器人的聊天框，你那几个前端页面对我没什么用"

**根本原因**：
- 没理解产品定位：用户只通过飞书交互，Web前端仅用于管理员查看数据
- 浪费开发时间在用户不使用的地方

**正确做法**：
- ✅ 所有交互优化集中在飞书机器人
- ✅ Web前端保持简单，仅用于数据展示和调试
- ✅ 遇到前端bug，优先检查飞书机器人是否有相同问题

**经验教训**：
> **永远先理解用户的使用场景**，不要假设用户会用Web界面。

---

### 踩坑2: 飞书卡片按钮点击后状态不更新 ❌❌❌（最严重）

**问题描述**：
- 用户点击飞书卡片"已补货 ✓"按钮
- 按钮loading一会后，恢复到原始状态，卡片无任何变化
- 后端日志显示PATCH API返回200，但飞书客户端卡片不变

**排查过程**（历时2小时，反复尝试）：

#### 阶段1: 误以为是API调用问题
- 添加详细日志，确认API调用
- 添加try-catch错误处理
- 发现API确实被调用了，返回200

#### 阶段2: 误以为是异步调用问题
- 修改dispatcher，使用`run_until_complete`同步等待
- 报错：`This event loop is already running`
- 发现WebSocket线程已有running loop，不能再用run_until_complete

#### 阶段3: 误以为是event loop问题
- 改用`loop.create_task()`创建任务
- 报错：`Future attached to a different loop`
- WebSocket连接崩溃断开

#### 阶段4: 最终发现根本原因 ✅
- 添加日志打印`open_message_id`的值
- 发现：`ERROR: open_message_id is empty, cannot update card`
- **根本原因**：飞书payload中，`open_message_id`在`event.context.open_message_id`，而不是`event.open_message_id`

**错误代码**：
```python
# dispatcher.py 第134行（错误）
open_message_id = event.get("open_message_id", "")  # 找不到，返回空字符串
```

**正确代码**：
```python
# dispatcher.py 第134-145行（修复后）
context = event.get("context", {}) if isinstance(event, dict) else {}
open_message_id = context.get("open_message_id", "") if isinstance(context, dict) else ""

# 或通过对象属性提取
if hasattr(evt_obj, 'context') and evt_obj.context:
    open_message_id = evt_obj.context.open_message_id if hasattr(evt_obj.context, 'open_message_id') else ""
```

**飞书实际payload结构**：
```json
{
  "event": {
    "operator": {"open_id": "ou_xxx"},
    "action": {"value": {"action": "mark_done", "alert_id": "0"}},
    "context": {
      "open_message_id": "om_x100b6cfb57e6cca4b1547081d9e189e",  // ← 正确位置
      "open_chat_id": "oc_c6e4ef8a92fed22add8cf3dc3fd8f096"
    }
  }
}
```

**修复文件**：
- `/Users/cocawinnie/family-assistant/backend/app/feishu/dispatcher.py` 第134-145行

**经验教训**：
> 1. **先查看实际payload结构**，不要猜测字段位置
> 2. **添加详细日志打印关键字段的值**，确认是否为空
> 3. **飞书的event结构经常有嵌套**，注意`context`、`operator`等层级
> 4. **不要盲目修改event loop处理方式**，先确认数据提取是否正确

---

### 踩坑3: alert_id=0的问题

**问题描述**：
- 日志显示：`WARNING: Alert 0 not found`
- 查询alert时使用`alert_id=0`，数据库中没有这条记录

**原因分析**：
- 用户主动搜索商品（"帮我搜索大米的价格"）时，生成比价卡片
- 此时没有关联到具体的RestockAlert记录，所以`alert_id=0`
- 定时提醒场景才有真实的alert_id

**修复方案**：
```python
# event_handler.py
if alert_id_str and alert_id_str != "0":
    # 有真实alert_id，更新数据库状态
    alert = db.query(RestockAlert).filter(RestockAlert.id == alert_id).first()
    if alert:
        alert.status = "done"
else:
    # alert_id=0（主动搜索），不查数据库，直接更新卡片
    logger.info("Manual purchase confirmation")
```

**经验教训**：
> 区分不同场景：主动搜索vs定时提醒，alert_id可能为0

---

### 踩坑4: WebSocket线程的event loop冲突

**问题描述**：
- 尝试在WebSocket线程中调用`loop.run_until_complete()`同步执行handler
- 报错：`This event loop is already running`

**原因**：
- WebSocket线程有自己的running loop用于接收消息
- 不能在running loop上调用`run_until_complete()`（会冲突）

**正确做法**：
```python
# WebSocket回调中，使用create_task()而不是run_until_complete()
loop = asyncio.get_running_loop()
task = loop.create_task(handler())
task.add_done_callback(callback)  # 通过回调处理结果
```

**错误做法**：
```python
# ❌ 错误：在running loop上调用run_until_complete
loop = asyncio.get_running_loop()
loop.run_until_complete(handler())  # 报错：This event loop is already running
```

**经验教训**：
> WebSocket线程已有running loop，只能用`create_task()`异步调度，不能同步等待

---

### 踩坑5: 飞书API文档与实际不符

**问题描述**：
- 参考飞书官方文档，假设字段在某个位置
- 实际payload中字段位置不同

**正确做法**：
- ✅ **先打印完整的payload JSON**，看实际结构
- ✅ 使用飞书开放平台的调试工具查看实际请求
- ✅ 添加日志打印关键字段，验证提取逻辑

**示例调试方法**：
```python
logger.debug(f"Full payload: {json.dumps(payload, indent=2)}")
logger.info(f"Extracted fields: event={event}, context={context}, open_message_id={open_message_id}")
```

**经验教训**：
> 不要信任文档，要看实际数据。飞书payload结构经常变化或有不同版本。

---

### 踩坑6: 用户测试反馈的重要性

**问题描述**：
- 反复修改代码，后端日志显示"API成功"
- 用户反馈："还是不行，卡片没变化"
- 开发者以为修复了，但实际没修复

**正确做法**：
- ✅ **每次修改后立即让用户测试**
- ✅ **不要只看后端日志**，要看用户实际体验
- ✅ **询问用户具体现象**：卡片是否变化、是否有其他异常
- ✅ **用户说"没修复"就是没修复**，不要争论

**经验教训**：
> 后端日志显示"成功"不代表真的修复了，要看用户实际反馈。

---

### 踩坑7: WebSocket连接意外断开

**问题描述**：
- 修改dispatcher的event loop处理方式后
- WebSocket连接突然断开：`receive message loop exit, err: internal error`
- 飞书机器人无响应，用户发消息不回复

**原因**：
- asyncio loop冲突：Future attached to different loop
- WebSocket接收线程的loop与主线程loop不兼容

**修复**：
- 重启后端，恢复WebSocket连接
- 使用正确的`create_task()`方式，不破坏WebSocket loop

**经验教训**：
> 修改asyncio逻辑时，要小心WebSocket线程的loop，避免冲突导致连接断开

---

## 五、开发易错点总结（单独部分）

### 1. 飞书开发易错点

#### 易错点1: payload字段提取错误 ⚠️
**常见错误**：直接从`event`提取字段，实际字段在嵌套的`context`中

**检查方法**：
```python
# ✅ 正确：打印完整payload看结构
logger.debug(f"Full payload: {json.dumps(payload, indent=2)}")

# ❌ 错误：猜测字段位置
open_message_id = event.get("open_message_id")  # 可能找不到
```

**飞书常见嵌套结构**：
- `event.context.open_message_id` - 卡片消息ID
- `event.operator.open_id` - 用户ID
- `event.action.value` - 按钮value

#### 易错点2: WebSocket vs Webhook模式混淆 ⚠️
**区别**：
- WebSocket：长连接，适合本地开发，SDK自动处理
- Webhook：HTTP回调，适合生产部署，需要公网HTTPS

**易错**：
- WebSocket模式下，回调函数不能返回值（只能异步调用API）
- Webhook模式下，回调函数可以直接返回新卡片内容

#### 易错点3: 卡片更新API调用成功但客户端不显示 ⚠️
**现象**：PATCH返回200，飞书客户端卡片不变

**检查清单**：
1. ✅ `open_message_id`是否正确提取？
2. ✅ 卡片JSON格式是否符合飞书规范？
3. ✅ 是否有权限更新这条消息？
4. ✅ 客户端是否需要刷新（滑动聊天列表）？

#### 易错点4: 异步任务调度错误 ⚠️
**WebSocket线程限制**：
- 已有running loop，不能用`run_until_complete()`
- 只能用`create_task()`异步调度
- 不要尝试获取主线程的loop（会冲突）

**正确调度方式**：
```python
# ✅ 正确：create_task + done_callback
loop = asyncio.get_running_loop()
task = loop.create_task(handler())
task.add_done_callback(lambda t: logger.info(f"Done: {t.result()}"))

# ❌ 错误：run_until_complete（会报错）
loop.run_until_complete(handler())
```

---

### 2. 产品开发易错点

#### 易错点1: 理解用户真实使用场景 ⚠️⚠️⚠️
**教训**：本项目用户只通过飞书交互，Web前端无用

**正确做法**：
- ✅ 第一步：询问用户"主要用什么界面"
- ✅ 第二步：了解用户实际操作流程
- ✅ 第三步：集中开发用户使用的功能
- ❌ 不要假设用户会用Web界面

#### 易错点2: 功能优先级错误 ⚠️
**教训**：花时间优化前端UI，但用户不看

**正确优先级**：
- 🔥 P0：飞书机器人核心交互（卡片、按钮、消息处理）
- 🔥 P0：飞书卡片按钮回调处理
- ⭐ P1：后端业务逻辑（库存计算、提醒生成）
- 💡 P2：Web前端（仅调试用途）

#### 易错点3: 测试依赖后端日志 ⚠️
**教训**：后端日志显示"API成功"，但用户说"没修复"

**正确测试方法**：
- ✅ 修改代码后立即让用户测试
- ✅ 不只看日志，要看用户实际体验
- ✅ 问用户具体现象："卡片是否变绿？标题是否变化？"

---

### 3. 数据处理易错点

#### 易错点1: 库存负数情况 ⚠️
**问题**：消耗记录超过采购记录，库存显示负数

**原因**：用户记录消耗但忘记记录采购

**建议**：
```python
# 添加边界检查
remaining = purchased_sum - consumed_sum
if remaining < 0:
    logger.warning(f"Negative inventory for item {item_id}")
    # 生成提醒让用户补充采购记录
```

#### 易错点2: 单位转换缺失 ⚠️
**问题**：用户说"2斤大米"，系统无法识别"斤"

**建议**：添加单位转换映射
```python
UNIT_CONVERSIONS = {
    "斤": 0.5,  # 1斤 = 0.5kg
    "两": 0.05,
    "ml": 0.001,
}
```

---

## 六、最佳实践

### 1. 开发流程最佳实践

```
1. 理解用户使用场景 → 2. 查看实际数据结构 → 3. 添加详细日志 → 
4. 小步修改验证 → 5. 立即用户测试 → 6. 看实际现象而非日志
```

### 2. 飞书开发最佳实践

**收到飞书事件时**：
```python
# Step 1: 打印完整payload
logger.debug(f"Full payload: {json.dumps(payload, indent=2)}")

# Step 2: 提取字段时添加日志验证
context = event.get("context", {})
open_message_id = context.get("open_message_id", "")
logger.info(f"Extracted open_message_id: {open_message_id}")

# Step 3: 调用API前确认参数不为空
if not open_message_id:
    logger.error("open_message_id is empty, cannot proceed")
    return
```

**WebSocket模式下**：
```python
# 正确的异步调度方式
loop = asyncio.get_running_loop()
task = loop.create_task(handler())
# 通过done_callback处理结果，而不是run_until_complete
task.add_done_callback(on_task_done)
```

### 3. 调试飞书卡片问题最佳实践

**问题排查步骤**：
```
1. 打印payload看字段位置
2. 打印提取的关键字段值（是否为空）
3. 打印API调用参数
4. 打印API返回的完整响应
5. 让用户测试，看客户端现象
6. 检查飞书客户端是否需要刷新
```

### 4. 代码修改原则

- ✅ 每次修改后立即重启后端（uvicorn --reload）
- ✅ 修改飞书相关代码后，测试WebSocket连接是否正常
- ✅ 修改asyncio相关代码后，检查是否有loop冲突
- ❌ 不要批量修改多个模块，小步验证

---

## 七、技术债务与待优化

### 高优先级待完成
1. ✅ 飞书卡片按钮回调（已修复）
2. 🔄 商品搜索真实API接入（Bing/其他）
3. 🔄 单位转换支持（斤→kg）
4. 🔄 库存负数处理（添加提醒）

### 低优先级待完成
5. ❌ 消耗趋势图表
6. ❌ 多人协作功能
7. ❌ Excel导入导出

---

## 八、快速上手指南

### 新接手开发者的第一步

1. **阅读本文档**（重点看踩坑总结）
2. **理解核心交互**：飞书机器人聊天框（不看Web前端）
3. **查看关键文件**：
   - `backend/app/feishu/dispatcher.py` - 事件分发（最易出错）
   - `backend/app/feishu/event_handler.py` - 事件处理
   - `backend/app/skills/shopping.py` - 主要业务逻辑

4. **运行项目**：
```bash
# 后端
cd backend
python3 -m uvicorn app.main:app --reload --port 8000

# 前端（可选，仅调试）
cd frontend
npm run dev
```

5. **测试飞书机器人**：
   - 发送消息："大米"
   - 检查是否收到回复和比价卡片
   - 点击"已补货"按钮，看卡片是否变绿

### 遇到问题时的排查方法

1. **查看日志**：`tail -100 /tmp/backend.log`
2. **检查WebSocket连接**：看日志是否有"connected to wss://"
3. **打印payload**：在dispatcher添加`logger.debug(json.dumps(payload))`
4. **立即用户测试**：不要只看日志，让用户测试实际效果

---

## 九、关键文件索引

| 文件 | 作用 | 易错点 |
|------|------|--------|
| `dispatcher.py` | 飞书事件分发 | **payload字段提取位置错误** |
| `event_handler.py` | 处理飞书事件 | alert_id=0的处理 |
| `card_builder.py` | 构建飞书卡片 | 卡片JSON格式规范 |
| `shopping.py` | 购物技能实现 | 商品搜索API占位 |
| `orchestrator.py` | 消息调度 | LLM调用和工具执行 |
| `trigger_engine.py` | 定时提醒 | 每日触发逻辑 |

---

## 十、附录

### 飞书开发文档参考
- [飞书开放平台](https://open.feishu.cn/document/)
- [卡片消息指南](https://open.feishu.cn/document/client-docs/bot-v3/bot-overview)
- [WebSocket开发指南](https://open.feishu.cn/document/client-docs/ws/ws-overview)

### 项目配置文件
- `.env`: 飞书APP_ID, APP_SECRET, LLM_API_KEY
- `backend/app/config.py`: 配置加载
- `backend/data/family_assistant.db`: SQLite数据库

---

**文档版本**: 2026-06-25
**维护者**: Claude Code
**适用对象**: 新接手的AI或开发者

**重要提醒**：⚠️ 阅读本文档的踩坑总结部分（第四节），避免重复踩坑！