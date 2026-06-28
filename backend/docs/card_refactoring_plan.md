# 卡片格式统一重构 - 实施方案

## 目标
重构卡片格式为统一数据结构，支持多平台（飞书、钉钉、微信、Web等）。

---

## 实施结果

### 1. 已创建的新文件

#### `backend/app/services/card_adapter_interface.py`
多平台卡片适配器抽象接口，包含：

- **`PlatformType`** - 支持的平台类型枚举（FEISHU, DINGTALK, WECHAT, WEB）
- **`BaseCardAdapter`** - 抽象基类，定义 `render()` 和 `render_text()` 方法
- **`FeishuCardAdapter`** - 飞书适配器（委托给 `convert_universal_to_feishu`）
- **`DingTalkCardAdapter`** - 钉钉适配器（ActionCard 格式，待实现）
- **`WeChatCardAdapter`** - 微信适配器（Markdown 格式，待实现）
- **`WebCardAdapter`** - Web 前端适配器（JSON 格式）
- **`CardAdapterFactory`** - 工厂类，获取/注册适配器

**使用示例：**
```python
from app.services.card_adapter_interface import CardAdapterFactory
from app.services.universal_card import UniversalCard

# 获取飞书适配器
adapter = CardAdapterFactory.get_adapter("feishu")
feishu_json = adapter.render(universal_card)

# 获取钉钉适配器
adapter = CardAdapterFactory.get_adapter("dingtalk")
dingtalk_json = adapter.render(universal_card)

# 支持的平台列表
platforms = CardAdapterFactory.supported_platforms()
# ['feishu', 'dingtalk', 'wechat', 'web']
```

---

### 2. 已更新的文件

#### `backend/app/services/universal_card.py` (已存在)
统一卡片数据结构：
- **`CardType`** - 卡片类型（RESTOCK_ALERT, INVENTORY_SUMMARY, SIMPLE_TEXT, PRODUCT_COMPARISON）
- **`AlertLevel`** - 警告级别（INFO, WARNING, ERROR, SUCCESS）
- **`ProductInfo`** - 商品信息（替代旧的 ProductLink）
- **`UniversalCard`** - 平台无关的卡片数据结构
- **`UniversalCardRenderer`** - 卡片渲染器（静态方法构建卡片）

#### `backend/app/services/product_search.py`
已迁移：
- 将 `ProductLink` 替换为 `ProductInfo`
- `search()` 和 `compare()` 方法返回 `List[ProductInfo]`
- `_raw_to_product_infos()` 替代 `_raw_to_product_links()`
- `_fallback_products()` 返回 `List[ProductInfo]`

#### `backend/app/modules/inventory/skill.py`
已更新：
- 导入 `UniversalCardRenderer, ProductInfo, AlertLevel` 和 `convert_universal_to_feishu`
- `execute_tool()` 中使用 `product_infos`
- `check_restock_and_notify()` 使用 `UniversalCardRenderer.restock_alert_card()`
- `format_response()` 返回 `{"type": "card", "content": UniversalCard}`

#### `backend/app/skills/shopping.py`
已更新（与 inventory/skill.py 保持一致）：
- 导入 `UniversalCardRenderer, ProductInfo, AlertLevel` 和 `convert_universal_to_feishu`
- 所有方法使用新系统

#### `backend/app/feishu/__init__.py`
已更新导出：
```python
from app.feishu.card_builder_v2 import CardBuilder, ProductLink  # 向后兼容
from app.feishu.card_adapter import convert_universal_to_feishu
```

#### `backend/app/feishu/card_adapter.py` (已存在)
飞书适配转换层：
- `convert_universal_to_feishu()` - 主入口函数
- 四个卡片类型转换器：`_convert_restock_alert`, `_convert_inventory_summary`, `_convert_simple_text`, `_convert_product_comparison`

#### `backend/app/feishu/card_builder_v2.py` (已存在)
向后兼容层：
- `CardBuilder` 类委托给 `UniversalCardRenderer`
- `ProductLink` 类可转换为 `ProductInfo`
- 旧代码无需修改即可继续使用

#### `backend/app/feishu/event_handler.py`
已更新：
- 导入 `UniversalCardRenderer` 和 `convert_universal_to_feishu`
- 支持三种响应格式：
  - `UniversalCard` (新格式)
  - `str` (纯文本)
  - `dict` (旧格式向后兼容)
- `handle_card_action()` 使用 `UniversalCardRenderer.simple_text_card()`

---

## 架构设计

### 数据流向

```
Skills (shopping.py, inventory/skill.py)
    ↓ 调用 UniversalCardRenderer 构建卡片
    ↓ 返回 UniversalCard 或 str
    
Orchestrator
    ↓ 传递 skills 返回的 response
    
FeishuEventHandler
    ↓ 判断 response 类型
    ↓ UniversalCard → convert_universal_to_feishu() → Feishu JSON
    ↓ str → 直接发送文本
    
FeishuClient
    ↓ send_card_message() 或 reply_card()
    
飞书 API
```

### 多平台扩展

```
UniversalCard (平台无关数据结构)
    ↓
CardAdapterFactory.get_adapter("feishu" | "dingtalk" | "wechat" | "web")
    ↓
FeishuCardAdapter / DingTalkCardAdapter / WeChatCardAdapter / WebCardAdapter
    ↓
平台特定格式 (Feishu JSON / DingTalk ActionCard / WeChat Markdown / Web JSON)
```

---

## 向后兼容性

### 旧代码继续工作的方式

1. **旧的 `CardBuilder` 导入**
   ```python
   from app.feishu import CardBuilder  # 仍然可用
   ```
   实际导入的是 `card_builder_v2.CardBuilder`，内部委托给 `UniversalCardRenderer`

2. **旧的 `ProductLink` 导入**
   ```python
   from app.feishu import ProductLink  # 仍然可用
   ```
   实际导入的是 `card_builder_v2.ProductLink`，有 `to_product_info()` 方法

3. **旧的 dict 格式响应**
   ```python
   {"type": "card", "content": {...}}  # 仍然被 event_handler 支持
   ```

---

## 新代码编写指南

### 创建卡片

```python
from app.services.universal_card import UniversalCardRenderer, ProductInfo, AlertLevel

# 补货提醒卡片
card = UniversalCardRenderer.restock_alert_card(
    item_name="洗衣液",
    remaining=2.5,
    unit="L",
    days_until_empty=5,
    suggested_quantity=5.0,
    products=[
        ProductInfo(platform="taobao", product_name="立白洗衣液", price=29.9, 
                    deep_link="taobao://...", web_url="https://..."),
    ],
    alert_id=123,
)

# 简单文本卡片
card = UniversalCardRenderer.simple_text_card(
    title="提示",
    content="操作已完成",
    alert_level=AlertLevel.SUCCESS,
)

# 商品比价卡片
card = UniversalCardRenderer.product_comparison_card(
    item_name="纸巾",
    products=[...],
    reply_text="找到了以下选项...",
)
```

### 发送卡片到飞书

```python
from app.feishu.card_adapter import convert_universal_to_feishu
from app.feishu.client import FeishuClient

client = FeishuClient()
feishu_json = convert_universal_to_feishu(card)
await client.send_card_message(open_id, feishu_json)
```

### 发送卡片到其他平台（未来）

```python
from app.services.card_adapter_interface import CardAdapterFactory

adapter = CardAdapterFactory.get_adapter("dingtalk")
dingtalk_card = adapter.render(card)
# 发送到钉钉...

adapter = CardAdapterFactory.get_adapter("wechat")
wechat_card = adapter.render(card)
# 发送到微信...
```

---

## 待完成事项

1. **钉钉适配器实现** - `DingTalkCardAdapter` 当前是占位实现，需要：
   - 实现完整的 ActionCard 格式
   - 处理回调按钮（钉钉不支持纯回调，需要特殊处理）

2. **微信适配器实现** - `WeChatCardAdapter` 当前是占位实现，需要：
   - 实现完整的 Markdown 格式
   - 处理企业微信的消息发送 API

3. **测试用例** - 添加单元测试验证：
   - `UniversalCardRenderer` 各卡片类型构建
   - `convert_universal_to_feishu` 转换正确性
   - 各适配器的渲染输出

---

## 文件变更清单

### 新创建
- `/backend/app/services/card_adapter_interface.py` - 多平台适配器接口

### 已更新
- `/backend/app/services/product_search.py` - ProductLink → ProductInfo
- `/backend/app/modules/inventory/skill.py` - 使用 UniversalCardRenderer
- `/backend/app/skills/shopping.py` - 使用 UniversalCardRenderer
- `/backend/app/feishu/__init__.py` - 更新导出
- `/backend/app/feishu/event_handler.py` - 支持 UniversalCard

### 向后兼容（已存在）
- `/backend/app/services/universal_card.py` - 统一卡片模型
- `/backend/app/feishu/card_adapter.py` - 飞书适配器
- `/backend/app/feishu/card_builder_v2.py` - 兼容层

### 可弃用（未来）
- `/backend/app/feishu/card_builder.py` - 旧版 CardBuilder（已通过 card_builder_v2 替代）