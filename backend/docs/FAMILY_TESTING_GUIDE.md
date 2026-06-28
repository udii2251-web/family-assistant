# 家庭组织管理功能测试指南

## 📋 已完成的功能

### 1. 数据隔离架构 ✅
- **Family表**：家庭组织（支持多家庭隔离）
- **FamilyMember表**：家庭成员（大人/小孩/宠物）
- **所有数据表添加family_id**：Item、PurchaseRecord、ConsumptionRecord、RestockAlert、TaobaoOrder

### 2. Agent Tools ✅
- `create_family` - 创建家庭
- `join_family` - 加入家庭（邀请码）
- `add_family_member` - 添加成员（小孩/宠物）
- `list_family_members` - 查看成员列表
- `get_family_info` - 查看家庭信息
- `generate_invite_link` - 生成邀请链接

### 3. 飞书卡片交互 ✅
- 创建家庭卡片（输入框+按钮）
- 添加成员卡片（选择器+输入框）
- 家庭信息展示卡片
- 邀请链接分享卡片

---

## 🧪 测试步骤

### 前置准备

1. **启动后端服务**：
```bash
cd backend
python3 -m uvicorn app.main:app --reload --port 8000
```

2. **确保飞书WebSocket连接正常**：
```bash
# 查看后端日志，应该看到：
# ✅ Feishu WebSocket connected
```

---

### 测试场景1：创建家庭（用户A）

**步骤**：
1. 在飞书机器人对话框中发送：`创建家庭`
2. 观察机器人回复：
   - ✅ 应返回"创建家庭的交互卡片"或提示引导创建
   - ✅ 或者直接文本回复："请输入家庭名称"

3. 发送：`创建家庭 幸福之家`
4. 观察回复：
   - ✅ 应返回：
     ```
     ✅ 家庭'幸福之家'创建成功！

     家庭ID：xxxxx
     邀请码：ABC123

     💡 你可以：
     1. 发送邀请码给家人...
     2. 添加家庭成员...
     ```

**验证数据库**：
```bash
sqlite3 backend/data/family_assistant.db "SELECT * FROM families;"
# 应看到新创建的家庭记录

sqlite3 backend/data/family_assistant.db "SELECT * FROM family_members WHERE member_type='adult';"
# 应看到创建者作为第一个大人成员
```

---

### 测试场景2：邀请家人（用户B）

**步骤**：
1. 用户B在飞书机器人对话框中发送：`加入家庭 ABC123`（使用步骤1的邀请码）
2. 观察回复：
   - ✅ 应返回：
     ```
     ✅ 成功加入家庭'幸福之家'！

     当前成员：2个大人...

     💡 现在你可以：
     - 记录购买和消耗
     - 查看库存情况
     - 接收补货提醒
     ```

**验证数据库**：
```bash
sqlite3 backend/data/family_assistant.db "SELECT adult_count FROM families WHERE family_id='xxx';"
# adult_count应从1变为2

sqlite3 backend/data/family_assistant.db "SELECT * FROM family_members WHERE member_type='adult';"
# 应看到2个大人成员
```

---

### 测试场景3：添加家庭成员（小孩/宠物）

**步骤**：
1. 用户A或B发送：`添加家庭成员`
2. 观察机器人回复：
   - ✅ 应返回"添加家庭成员卡片"或引导添加
   - ✅ 或提示："请选择成员类型"

3. 发送：`添加小孩 小宝 3岁`
4. 观察回复：
   - ✅ 应返回：
     ```
     ✅ 成功添加家庭成员：小孩 '小宝'，年龄3岁

     当前家庭：2个大人、1个小孩、0只宠物
     ```

**验证数据库**：
```bash
sqlite3 backend/data/family_assistant.db "SELECT child_count FROM families;"
# child_count应为1

sqlite3 backend/data/family_assistant.db "SELECT * FROM family_members WHERE member_type='child';"
# 应看到小孩记录
```

---

### 测试场景4：查看家庭信息

**步骤**：
1. 发送：`查看家庭信息` 或 `家庭信息`
2. 观察回复：
   - ✅ 应返回家庭详细信息：
     ```
     🏠 家庭信息

     家庭名称：幸福之家
     家庭ID：xxxxx
     成员构成：2个大人、1个小孩、0只宠物
     创建时间：2026-06-28

     💡 邀请码：ABC123（可分享给家人加入）
     ```

---

### 测试场景5：验证数据隔离

**关键测试**：确保不同家庭的库存数据隔离

**步骤**：
1. **用户A（已加入家庭1）**：
   - 发送：`记录购买 大米 5公斤`
   - 观察回复：✅ 成功记录

2. **用户C（未加入家庭）**：
   - 发送：`创建家庭 另一个家庭`
   - 发送：`记录购买 大米 3公斤`
   - 观察回复：✅ 成功记录

3. **用户A查看库存**：
   - 发送：`查看库存`
   - 应看到：大米 5公斤（家庭1的数据）

4. **用户C查看库存**：
   - 发送：`查看库存`
   - 应看到：大米 3公斤（家庭2的数据）

**验证数据库**：
```bash
sqlite3 backend/data/family_assistant.db "
SELECT 
  f.family_name,
  i.name,
  p.quantity
FROM purchase_records p
JOIN items i ON p.item_id = i.id
JOIN families f ON p.family_id = f.family_id;
"
# 应看到两条记录，分别属于不同的家庭
```

---

### 测试场景6：飞书卡片交互（可选）

如果飞书卡片渲染成功，测试交互按钮：

1. **创建家庭卡片**：
   - 输入家庭名："幸福之家"
   - 输入初始成员："4个大人、1个小孩、2只狗"
   - 点击"创建家庭"按钮
   - ✅ 应触发创建动作

2. **添加成员卡片**：
   - 选择成员类型："小孩"
   - 输入姓名："小宝"
   - 输入年龄："3"
   - 点击"添加成员"按钮
   - ✅ 应触发添加动作

**注意**：飞书卡片回调需要配置飞书应用的卡片回调URL，参见飞书文档。

---

## 🐛 常见问题

### 1. 提示"你还没有加入家庭"

**原因**：用户未创建或加入家庭

**解决**：
- 发送：`创建家庭 家庭名`
- 或：`加入家庭 邀请码`

---

### 2. 数据库找不到family_id字段

**原因**：数据库未更新

**解决**：
```bash
# 重新创建数据库表
cd backend
python3 -c "
from app.shared.database import init_db
init_db()
print('✅ Database initialized')
"
```

---

### 3. 飞书WebSocket未连接

**检查**：
```bash
# 查看后端日志
ps aux | grep uvicorn
# 确认进程运行中

# 检查飞书配置
grep FEISHU_APP_ID backend/app/shared/config.py
# 确认飞书APP_ID和SECRET已配置
```

---

## 📊 数据验证SQL

```bash
# 查看所有家庭
sqlite3 backend/data/family_assistant.db "
SELECT family_id, family_name, adult_count, child_count, pet_count, invite_code
FROM families;
"

# 查看所有家庭成员
sqlite3 backend/data/family_assistant.db "
SELECT f.family_name, fm.member_type, fm.name, fm.feishu_open_id
FROM family_members fm
JOIN families f ON fm.family_id = f.family_id
ORDER BY f.family_name, fm.member_type;
"

# 查看库存数据隔离
sqlite3 backend/data/family_assistant.db "
SELECT
  f.family_name,
  i.name as item_name,
  SUM(p.quantity) as total_purchased,
  p.family_id
FROM purchase_records p
JOIN items i ON p.item_id = i.id
JOIN families f ON p.family_id = f.family_id
GROUP BY p.family_id, i.name;
"
```

---

## ✅ 测试成功标准

1. ✅ 用户能创建家庭并获取邀请码
2. ✅ 其他用户能通过邀请码加入家庭
3. ✅ 能添加小孩和宠物成员
4. ✅ 查看家庭信息显示正确
5. ✅ 不同家庭的库存数据隔离（关键！）
6. ✅ 飞书卡片能正常渲染和交互（可选）

---

## 🎯 下一步功能

完成测试后，可继续开发：
1. **消耗速度预测优化**：基于家庭成员数量调整预测算法
2. **定向通知策略**：共用物品通知所有大人，个人物品只通知购买者
3. **飞书卡片回调处理**：处理卡片按钮点击事件
4. **家庭成员管理增强**：删除成员、修改成员信息

---

测试完成后请反馈结果！有问题随时联系。