# 家庭管家系统 - 架构重构进度报告

**报告时间**: 2026-06-25 19:15  
**执行者**: Claude Fable 5  
**状态**: 阶段1进行中，已完成核心架构框架

---

## 一、背景与目标

### 原始方案来源
- 文件: `AI Agent 项目并行开发方案.rtf`
- 位置: `/Users/cocawinnie/family-assistant/AI Agent 项目并行开发方案.rtf`
- 核心目标: 淘宝账号授权 + 淘宝订单同步 + 消费分析能力
- 架构选择: 业务模块化架构（用户已同意模块化优于功能分层）

### 计划文件
- 完整计划: `/Users/cocawinnie/.claude/plans/dapper-mixing-sonnet.md`
- 计划状态: 已获用户批准
- 计划版本: v1.0

---

## 二、已完成工作

### ✅ 1. 目录结构创建（100%完成）

创建的目录：
```
backend/app/
├── modules/              # 新增
│   ├── inventory/        # 库存模块（Session A负责）
│   │   └── __init__.py
│   └── taobao/           # 淘宝模块（Session B负责）
│   │   └── __init__.py
└── shared/               # 共享代码（新增）
    └── __init__.py
```

**验证命令**:
```bash
ls -la backend/app/modules/
ls -la backend/app/shared/
```

---

### ✅ 2. 共享代码迁移（100%完成）

已迁移文件：
| 原路径 | 新路径 | 状态 | 备注 |
|--------|--------|------|------|
| `backend/app/database.py` | `backend/app/shared/database.py` | ✅ 已迁移 | 导入路径已修改为 `from app.shared.config` |
| `backend/app/config.py` | `backend/app/shared/config.py` | ✅ 已迁移 | BASE_DIR路径已调整 |
| `backend/app/services/session.py` | `backend/app/shared/session.py` | ✅ 已迁移 | 导入路径已修改 |
| `backend/app/services/orchestrator.py` | `backend/app/shared/orchestrator.py` | ✅ 已迁移 | 导入路径已修改 |

**关键修改**:
- `shared/database.py`: 修改导入 `from app.shared.config import DB_PATH, DATA_DIR`
- `shared/database.py`: init_db() 函数修改导入路径为 `from app.modules.inventory.models import ...`
- `shared/config.py`: BASE_DIR调整为 `os.path.dirname(os.path.dirname(os.path.dirname(...)))`

---

### ✅ 3. 淘宝模块占位文件创建（100%完成）

创建的文件（6个）：
```
backend/app/modules/taobao/
├── __init__.py           ✅ 模块入口，定义 __all__
├── auth.py               ✅ 登录授权占位（含注释）
├── sync.py               ✅ 订单同步占位（含注释）
├── models.py             ✅ 订单模型占位（含示例结构）
├── tools.py              ✅ Agent Tools占位，含 get_taobao_tools() 函数
└── playwright_manager.py ✅ Playwright管理占位
```

**关键代码**:
- `tools.py`: 包含 `get_taobao_tools()` 函数，返回空列表（占位）
- `__init__.py`: 定义 `__all__ = ['get_taobao_tools', 'TaobaoSkill']`
- 所有文件包含详细注释，说明 Session B 需实现的内容

---

### ✅ 4. 库存模块部分合并（20%完成）

已完成：
- ✅ `modules/inventory/models.py`: 合并5个模型（FamilyMember, ItemCategory, Item, PurchaseRecord, ConsumptionRecord, RestockAlert）
- ✅ 导入路径修改为 `from app.shared.database import Base`

待完成：
- ⏳ `modules/inventory/routers.py`: 合并6个路由文件
- ⏳ `modules/inventory/services.py`: 合并2个服务文件
- ⏳ `modules/inventory/tools.py`: 提取8个Agent Tools
- ⏳ `modules/inventory/skill.py`: 迁移ShoppingSkill
- ⏳ `modules/inventory/triggers.py`: 迁移TriggerEngine

---

### ✅ 5. 依赖更新（100%完成）

**文件**: `backend/requirements.txt`

新增依赖：
```txt
# Taobao module dependencies (for Session B)
playwright>=1.40.0
supabase>=2.0.0  # Optional, can also use SQLite
```

---

## 三、待完成工作清单

### 🔄 阶段1剩余任务（优先级：高）

#### 1. 合并库存模块文件（工作量：大）

**文件合并任务**:

**A. routers.py 合并**（预计30分钟）
- 需合并6个路由文件：
  - `backend/app/routers/family.py`
  - `backend/app/routers/items.py`
  - `backend/app/routers/purchases.py`
  - `backend/app/routers/consumption.py`
  - `backend/app/routers/inventory.py`
  - `backend/app/routers/alerts.py`
- 合并方式：每个路由保持独立的 router 对象
- 导入修改：`from app.modules.inventory.models import ...`

**B. services.py 合并**（预计20分钟）
- 需合并2个服务文件：
  - `backend/app/services/inventory.py`
  - `backend/app/services/alert_scheduler.py`
- 合并方式：将所有服务函数合并到一个文件
- 导入修改：`from app.modules.inventory.models import ...`

**C. tools.py 提取**（预计15分钟）
- 从 `backend/app/skills/shopping.py` 提取：
  - `get_tools()` 方法返回的8个工具定义
  - 创建独立的 `get_inventory_tools()` 函数
- 工具列表：
  1. record_purchase
  2. record_consumption
  3. query_inventory
  4. check_restock_alerts
  5. add_item
  6. list_items
  7. search_products
  8. compare_products

**D. skill.py 迁移**（预计20分钟）
- 迁移 `backend/app/skills/shopping.py`：
  - ShoppingSkill 类改名为 InventorySkill
  - 保持所有业务逻辑不变
  - 导入修改：相对导入
- 关键方法：
  - `get_tools()`
  - `execute_tool()`
  - `get_triggers()`
  - `check_restock_and_notify()`
  - `format_response()`

**E. triggers.py 迁移**（预计15分钟）
- 迁移 `backend/app/services/trigger_engine.py`：
  - TriggerEngine 类
  - 保持逻辑不变
  - 导入修改：相对导入

---

#### 2. 更新导入路径（工作量：中）

**需要修改的文件**:

**A. main.py**（关键，预计30分钟）
- 修改导入路径：
  ```python
  # 原导入
  from app.routers import family, items, consumption, purchases, inventory, alerts
  from app.services.orchestrator import Orchestrator
  from app.services.session import SessionManager
  from app.services.trigger_engine import TriggerEngine
  
  # 新导入
  from app.modules.inventory.routers import (
      family_router, items_router, consumption_router,
      purchases_router, inventory_router, alerts_router
  )
  from app.shared.orchestrator import Orchestrator
  from app.shared.session import SessionManager
  from app.modules.inventory.triggers import TriggerEngine
  from app.modules.inventory.skill import InventorySkill
  ```
- 注册路由：修改 router 名称
- 初始化：修改 skill 注册

**B. 其他文件**（预计20分钟）
- `backend/app/feishu/client.py`: 导入路径修改
- `backend/app/feishu/dispatcher.py`: 导入路径修改
- `backend/app/feishu/event_handler.py`: 导入路径修改
- `backend/app/routers/chat.py`: 导入路径修改

**批量修改命令**（待执行）:
```bash
# 更新所有 app.database → app.shared.database
find backend/app -name "*.py" -exec sed -i '' 's/from app\.database/from app.shared.database/g' {} \;

# 更新所有 app.config → app.shared.config  
find backend/app -name "*.py" -exec sed -i '' 's/from app\.config/from app.shared.config/g' {} \;

# 更新所有 app.services.orchestrator → app.shared.orchestrator
find backend/app -name "*.py" -exec sed -i '' 's/from app\.services\.orchestrator/from app.shared.orchestrator/g' {} \;

# 更新所有 app.services.session → app.shared.session
find backend/app -name "*.py" -exec sed -i '' 's/from app\.services\.session/from app.shared.session/g' {} \;
```

---

#### 3. 功能验证（工作量：中）

**验证步骤**（预计30分钟）:
1. 后端启动测试：
   ```bash
   cd backend
   python3 -m uvicorn app.main:app --reload --port 8000
   ```
2. API 测试：
   ```bash
   curl http://localhost:8000/inventory/
   curl http://localhost:8000/items/
   curl http://localhost:8000/alerts/
   ```
3. 飞书机器人测试：发送消息"大米还有多少"
4. Agent Tools测试：record_purchase, query_inventory
5. 定时提醒测试：trigger_engine运行正常

---

#### 4. Git提交（工作量：小）

**提交内容**（预计10分钟）:
```bash
git add backend/app/modules/
git add backend/app/shared/
git add backend/requirements.txt
git commit -m "架构重构阶段1: 模块化架构搭建

- 创建 modules/inventory 和 modules/taobao 目录结构
- 迁移共享代码到 shared/ 目录
- 创建淘宝模块占位文件（6个文件）
- 合并库存模块模型文件（models.py）
- 更新依赖（添加 playwright 和 supabase）

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## 四、后续阶段任务（Session A/B负责）

### 阶段2: Session A - Inventory Agent MVP完善
**负责人**: Session A（独立session）  
**禁止范围**: 禁止进入 `modules/taobao/`  
**任务**:
- 完善库存查询能力
- 优化 Agent Tool调用
- 维护 Mock 数据
- 运维支持

### 阶段3: Session B - Taobao Connector实现
**负责人**: Session B（独立session）  
**禁止范围**: 禁止进入 `modules/inventory/`  
**任务**:
- 淘宝登录授权（Playwright）
- 订单同步（最近7天）
- Agent Tools实现
- 登录失效处理
- 定时任务集成

### 阶段4: 集成与测试
**任务**:
- 统一 Agent Tool注册
- 飞书机器人集成测试
- 订单数据与库存数据关联
- 文档更新

---

## 五、关键文件索引

### 已创建/修改的文件

| 文件路径 | 状态 | 内容 | 备注 |
|---------|------|------|------|
| `backend/app/modules/__init__.py` | ✅ 已创建 | 空文件 | 模块入口 |
| `backend/app/modules/inventory/__init__.py` | ✅ 已创建 | 空文件 | 库存模块入口 |
| `backend/app/modules/inventory/models.py` | ✅ 已创建 | 合并5个模型 | **关键文件** |
| `backend/app/modules/taobao/__init__.py` | ✅ 已创建 | 模块定义 | 含 __all__ |
| `backend/app/modules/taobao/auth.py` | ✅ 已创建 | 占位+注释 | Session B待实现 |
| `backend/app/modules/taobao/sync.py` | ✅ 已创建 | 占位+注释 | Session B待实现 |
| `backend/app/modules/taobao/models.py` | ✅ 已创建 | 占位+示例 | Session B待实现 |
| `backend/app/modules/taobao/tools.py` | ✅ 已创建 | 占位函数 | **关键：get_taobao_tools()** |
| `backend/app/modules/taobao/playwright_manager.py` | ✅ 已创建 | 占位 | Session B待实现 |
| `backend/app/shared/__init__.py` | ✅ 已创建 | 空文件 | 共享代码入口 |
| `backend/app/shared/database.py` | ✅ 已创建 | 数据库连接 | **关键：导入路径已修改** |
| `backend/app/shared/config.py` | ✅ 已创建 | 配置管理 | BASE_DIR已调整 |
| `backend/app/shared/session.py` | ✅ 已创建 | 会话管理 | 导入路径已修改 |
| `backend/app/shared/orchestrator.py` | ✅ 已创建 | 消息调度 | 导入路径已修改 |
| `backend/requirements.txt` | ✅ 已修改 | 新增依赖 | playwright + supabase |

### 待创建的文件

| 文件路径 | 待创建 | 内容 | 预计时间 |
|---------|--------|------|---------|
| `backend/app/modules/inventory/routers.py` | ⏳ 待创建 | 合并6个路由 | 30分钟 |
| `backend/app/modules/inventory/services.py` | ⏳ 待创建 | 合并2个服务 | 20分钟 |
| `backend/app/modules/inventory/tools.py` | ⏳ 待创建 | 提取8个Tools | 15分钟 |
| `backend/app/modules/inventory/skill.py` | ⏳ 待创建 | 迁移Skill类 | 20分钟 |
| `backend/app/modules/inventory/triggers.py` | ⏳ 待创建 | 迁移Trigger类 | 15分钟 |

---

## 六、遇到的问题与解决

### 问题1: inventory-merge-agent未能创建文件
**现象**: 启动的 agent 只返回空闲通知，未实际创建文件  
**原因**: 可能权限或执行问题  
**解决**: 改为手动逐步执行文件合并  
**影响**: 延长时间，但可控

### 问题2: __init__.py文件写入需要先Read
**现象**: Write工具要求先Read已存在的文件  
**解决**: 先Read空文件，再Write内容  
**影响**: 无影响，已解决

---

## 七、下一步行动计划

### 明天继续步骤（推荐顺序）

#### Step 1: 完成库存模块文件合并（最优先）
**预计时间**: 90分钟  
**执行方式**: 手动逐步合并  
**关键文件**: routers.py, services.py, tools.py, skill.py, triggers.py

#### Step 2: 更新导入路径
**预计时间**: 50分钟  
**关键文件**: main.py（最重要）  
**批量命令**: 使用 sed 批量修改

#### Step 3: 功能验证
**预计时间**: 30分钟  
**测试内容**: 启动后端 + API测试 + 飞书机器人测试

#### Step 4: Git提交
**预计时间**: 10分钟  
**提交信息**: 详细的架构重构描述

#### Step 5: 启动Session A/B并行开发
**执行方式**: 使用 Agent 工具启动两个独立session  
**Session A任务**: Inventory Agent MVP完善  
**Session B任务**: Taobao Connector实现

---

## 八、关键提醒

### ⚠️ 重要注意事项

1. **导入路径一致性**: 所有文件必须使用新的导入路径
   - `app.database` → `app.shared.database`
   - `app.config` → `app.shared.config`
   - `app.routers.*` → `app.modules.inventory.routers`
   - `app.models.*` → `app.modules.inventory.models`

2. **功能不中断**: 所有现有功能必须保持正常
   - API路由路径不变（/family, /items, /inventory等）
   - 飞书机器人交互不变
   - Agent Tools功能不变

3. **模块隔离原则**:
   - Session A 只修改 `modules/inventory/`
   - Session B 只修改 `modules/taobao/`
   - 禁止跨模块修改

4. **暂不删除原文件**: 
   - 原文件暂时保留，便于回滚
   - 验证成功后再删除

5. **main.py关键修改**:
   - 必须正确导入新的路由名称
   - 必须正确注册InventorySkill
   - 必须正确初始化TriggerEngine

---

## 九、参考文档

### 原始方案文件
- `/Users/cocawinnie/family-assistant/AI Agent 项目并行开发方案.rtf`

### 完整计划文件  
- `/Users/cocawinnie/.claude/plans/dapper-mixing-sonnet.md`

### 项目总结文档
- `/Users/cocawinnie/family-assistant/PROJECT_SUMMARY.md`
- `/Users/cocawinnie/family-assistant/CODE_WALKTHROUGH_SUMMARY.md`
- `/Users/cocawinnie/family-assistant/IMPLEMENTATION_STATUS.md`

---

## 十、总结

### 已完成进度
- ✅ 核心架构框架搭建（目录结构 + 共享代码 + 淘宝模块占位）
- ✅ 60%的阶段1工作
- ✅ 模块化骨架已成型

### 待完成进度
- ⏳ 库存模块文件合并（40%的阶段1工作）
- ⏳ 导入路径更新
- ⏳ 功能验证
- ⏳ Git提交

### 估计剩余时间
- **阶段1完成**: 约120分钟（明天继续）
- **Session A**: 约3-4小时（独立session）
- **Session B**: 约6-8小时（独立session）
- **集成测试**: 约3小时

---

**状态**: 架构重构进行中，已完成核心框架，明天继续完成剩余合并工作  
**下一步**: 明天继续完成库存模块文件合并，然后验证功能，最后启动Session A/B并行开发

**保存时间**: 2026-06-25 19:15  
**保存者**: Claude Fable 5