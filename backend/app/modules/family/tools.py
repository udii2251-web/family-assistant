"""家庭组织管理 - Agent Tools

提供家庭管理的Agent Tools：
1. create_family - 创建家庭组织
2. join_family - 加入家庭（通过邀请链接）
3. add_family_member - 添加家庭成员（小孩/宠物）
4. list_family_members - 查看家庭成员列表
5. get_family_info - 查看家庭信息
6. generate_invite_link - 生成邀请链接
"""

import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.models.family import Family, FamilyMember

logger = logging.getLogger(__name__)


def get_family_tools() -> List[Dict[str, Any]]:
    """Return family management Agent Tools."""
    return [
        {
            "type": "function",
            "function": {
                "name": "create_family",
                "description": "创建一个新的家庭组织。用户首次使用时需要创建家庭才能管理库存。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "family_name": {
                            "type": "string",
                            "description": "家庭名称，例如'幸福之家'"
                        },
                        "initial_members": {
                            "type": "string",
                            "description": "初始家庭成员描述，例如'4个大人、1个小孩、2只狗'"
                        }
                    },
                    "required": ["family_name"]
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "join_family",
                "description": "通过邀请码加入一个家庭组织。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "invite_code": {
                            "type": "string",
                            "description": "邀请码"
                        }
                    },
                    "required": ["invite_code"]
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "add_family_member",
                "description": "添加家庭成员（小孩或宠物）。大人通过邀请链接加入。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "member_type": {
                            "type": "string",
                            "description": "成员类型: child(小孩)/dog(狗)/cat(猫)"
                        },
                        "name": {
                            "type": "string",
                            "description": "成员姓名/昵称"
                        },
                        "age": {
                            "type": "number",
                            "description": "年龄（小孩）"
                        },
                        "weight": {
                            "type": "number",
                            "description": "体重（宠物，单位kg）"
                        },
                        "breed": {
                            "type": "string",
                            "description": "品种（宠物）"
                        }
                    },
                    "required": ["member_type", "name"]
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_family_members",
                "description": "查看家庭成员列表。",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_family_info",
                "description": "查看家庭信息，包括家庭成员构成。",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "generate_invite_link",
                "description": "生成邀请链接，邀请其他飞书用户加入家庭。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expires_days": {
                            "type": "number",
                            "description": "邀请链接有效期（天数），默认7天"
                        }
                    },
                    "required": []
                },
            },
        },
    ]


def execute_family_tool(db: Session, tool_name: str, tool_args: Dict[str, Any], user_open_id: str) -> str:
    """Execute a family management tool.

    Args:
        db: Database session
        tool_name: Name of tool to execute
        tool_args: Tool arguments
        user_open_id: Current user's Feishu open_id

    Returns:
        str: Result message
    """
    try:
        if tool_name == "create_family":
            return _create_family(db, tool_args, user_open_id)
        elif tool_name == "join_family":
            return _join_family(db, tool_args, user_open_id)
        elif tool_name == "add_family_member":
            return _add_family_member(db, tool_args, user_open_id)
        elif tool_name == "list_family_members":
            return _list_family_members(db, user_open_id)
        elif tool_name == "get_family_info":
            return _get_family_info(db, user_open_id)
        elif tool_name == "generate_invite_link":
            return _generate_invite_link(db, tool_args, user_open_id)
        else:
            return f"未知的家庭管理工具: {tool_name}"

    except Exception as e:
        logger.error(f"Error executing family tool {tool_name}: {e}")
        return f"执行工具失败: {str(e)}"


def _create_family(db: Session, args: Dict[str, Any], user_open_id: str) -> str:
    """Create a new family."""
    import uuid
    import random

    family_name = args["family_name"]
    initial_members = args.get("initial_members", "")

    # Check if user already has a family
    existing_member = db.query(FamilyMember).filter(
        FamilyMember.feishu_open_id == user_open_id
    ).first()

    if existing_member:
        return f"⚠️ 你已经加入了家庭'{existing_member.family_id}'，不能创建新家庭。"

    # Generate unique family_id and invite_code
    family_id = str(uuid.uuid4())[:8]  # Short ID for easier sharing
    invite_code = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=6))  # 6-char code

    # Create family
    family = Family(
        family_id=family_id,
        family_name=family_name,
        creator_open_id=user_open_id,
        invite_code=invite_code,
        adult_count=1,  # Creator is first adult
    )
    db.add(family)

    # Add creator as first family member
    creator_member = FamilyMember(
        family_id=family_id,
        member_type="adult",
        name="创建者",  # Can update later
        feishu_open_id=user_open_id,
        is_feishu_user=True,
    )
    db.add(creator_member)

    db.commit()

    logger.info(f"✅ Family created: {family_id} by {user_open_id}")

    # Parse initial members if provided
    member_info = ""
    if initial_members:
        # TODO: Parse "4个大人、1个小孩、2只狗" format
        member_info = f"\n初始成员：{initial_members}"

    return (
        f"✅ 家庭'{family_name}'创建成功！\n\n"
        f"家庭ID：{family_id}\n"
        f"邀请码：{invite_code}\n"
        f"{member_info}\n\n"
        f"💡 你可以：\n"
        f"1. 发送邀请码给家人，让他们输入'加入家庭 {invite_code}'\n"
        f"2. 添加家庭成员：'添加家庭成员' → 选择小孩或宠物\n"
    )


def _join_family(db: Session, args: Dict[str, Any], user_open_id: str) -> str:
    """Join a family using invite code."""
    invite_code = args["invite_code"]

    # Check if user already has a family
    existing_member = db.query(FamilyMember).filter(
        FamilyMember.feishu_open_id == user_open_id
    ).first()

    if existing_member:
        return f"⚠️ 你已经加入了家庭'{existing_member.family_id}'，不能加入其他家庭。"

    # Find family by invite code
    family = db.query(Family).filter(Family.invite_code == invite_code).first()

    if not family:
        return f"❌ 邀请码'{invite_code}'无效，请检查后重试。"

    # Add user as adult member
    new_member = FamilyMember(
        family_id=family.family_id,
        member_type="adult",
        name="家庭成员",
        feishu_open_id=user_open_id,
        is_feishu_user=True,
        invited_by=family.creator_open_id,
    )
    db.add(new_member)

    # Update family adult count
    family.adult_count += 1

    db.commit()

    logger.info(f"✅ User {user_open_id} joined family {family.family_id}")

    return (
        f"✅ 成功加入家庭'{family.family_name}'！\n\n"
        f"当前成员：{family.adult_count}个大人、{family.child_count}个小孩、{family.pet_count}只宠物\n\n"
        f"💡 现在你可以：\n"
        f"- 记录购买和消耗\n"
        f"- 查看库存情况\n"
        f"- 接收补货提醒\n"
    )


def _add_family_member(db: Session, args: Dict[str, Any], user_open_id: str) -> str:
    """Add a family member (child or pet)."""
    # Get user's family
    user_member = db.query(FamilyMember).filter(
        FamilyMember.feishu_open_id == user_open_id
    ).first()

    if not user_member:
        return "❌ 你还没有加入家庭，请先'创建家庭'或'加入家庭'。"

    family = db.query(Family).filter(Family.family_id == user_member.family_id).first()
    if not family:
        return "❌ 家庭不存在。"

    member_type = args["member_type"]
    name = args["name"]
    age = args.get("age")
    weight = args.get("weight")
    breed = args.get("breed")

    # Create new member
    new_member = FamilyMember(
        family_id=family.family_id,
        member_type=member_type,
        name=name,
        age=age,
        weight=weight,
        breed=breed,
        is_feishu_user=False,  # Children/pets don't use Feishu
        invited_by=user_open_id,
    )
    db.add(new_member)

    # Update family counts
    if member_type == "child":
        family.child_count += 1
    elif member_type in ["dog", "cat"]:
        family.pet_count += 1

    db.commit()

    logger.info(f"✅ Member added: {member_type} '{name}' to family {family.family_id}")

    type_name = {"child": "小孩", "dog": "狗", "cat": "猫"}
    extra_info = ""
    if age:
        extra_info += f"，年龄{age}岁"
    if weight:
        extra_info += f"，体重{weight}kg"
    if breed:
        extra_info += f"，品种{breed}"

    return (
        f"✅ 成功添加家庭成员：{type_name.get(member_type, member_type)} '{name}'{extra_info}\n\n"
        f"当前家庭：{family.adult_count}个大人、{family.child_count}个小孩、{family.pet_count}只宠物\n\n"
        f"💡 提醒：添加成员后，消耗速度预测会更准确！"
    )


def _list_family_members(db: Session, user_open_id: str) -> str:
    """List family members."""
    user_member = db.query(FamilyMember).filter(
        FamilyMember.feishu_open_id == user_open_id
    ).first()

    if not user_member:
        return "❌ 你还没有加入家庭，请先'创建家庭'或'加入家庭'。"

    members = db.query(FamilyMember).filter(
        FamilyMember.family_id == user_member.family_id
    ).all()

    if not members:
        return "家庭成员列表为空。"

    type_names = {"adult": "大人", "child": "小孩", "dog": "狗", "cat": "猫"}

    lines = [f"🏠 家庭成员列表：\n"]

    # Group by type
    for member_type in ["adult", "child", "dog", "cat"]:
        type_members = [m for m in members if m.member_type == member_type]
        if type_members:
            lines.append(f"{type_names[member_type]}：")
            for m in type_members:
                info = f"  - {m.name}"
                if m.age:
                    info += f"（{m.age}岁）"
                if m.weight:
                    info += f"（{m.weight}kg）"
                if m.breed:
                    info += f"（{m.breed}）"
                if m.is_feishu_user:
                    info += " ✅飞书用户"
                lines.append(info)
            lines.append("")

    return "\n".join(lines)


def _get_family_info(db: Session, user_open_id: str) -> str:
    """Get family information."""
    user_member = db.query(FamilyMember).filter(
        FamilyMember.feishu_open_id == user_open_id
    ).first()

    if not user_member:
        return "❌ 你还没有加入家庭，请先'创建家庭'或'加入家庭'。"

    family = db.query(Family).filter(Family.family_id == user_member.family_id).first()

    if not family:
        return "❌ 家庭不存在。"

    return (
        f"🏠 家庭信息\n\n"
        f"家庭名称：{family.family_name}\n"
        f"家庭ID：{family.family_id}\n"
        f"成员构成：{family.adult_count}个大人、{family.child_count}个小孩、{family.pet_count}只宠物\n"
        f"创建时间：{family.created_at.strftime('%Y-%m-%d')}\n"
        f"\n💡 邀请码：{family.invite_code}（可分享给家人加入）"
    )


def _generate_invite_link(db: Session, args: Dict[str, Any], user_open_id: str) -> str:
    """Generate invite link."""
    from datetime import datetime, timedelta

    user_member = db.query(FamilyMember).filter(
        FamilyMember.feishu_open_id == user_open_id
    ).first()

    if not user_member:
        return "❌ 你还没有加入家庭，请先'创建家庭'或'加入家庭'。"

    family = db.query(Family).filter(Family.family_id == user_member.family_id).first()

    expires_days = args.get("expires_days", 7)

    # Generate invite link (mock URL for now)
    invite_link = f"https://feishu-bot.example.com/join?family={family.family_id}&code={family.invite_code}"
    family.invite_link = invite_link
    family.invite_expires_at = datetime.utcnow() + timedelta(days=expires_days)

    db.commit()

    return (
        f"✅ 邀请链接已生成！\n\n"
        f"邀请链接：{invite_link}\n"
        f"邀请码：{family.invite_code}\n"
        f"有效期：{expires_days}天\n\n"
        f"💡 发送此链接给家人，他们点击即可加入家庭。"
    )


class FamilySkill:
    """Family management skill for integration with orchestrator."""

    @property
    def name(self) -> str:
        return "family"

    @property
    def description(self) -> str:
        return "家庭组织管理：创建家庭、邀请家人、管理家庭成员"

    @property
    def system_prompt(self) -> str:
        return """你是家庭管家助手，帮助用户管理家庭组织。

你的职责：
1. 帮助用户创建家庭组织（首次使用必须创建）
2. 生成邀请链接邀请家人加入
3. 添加家庭成员（小孩、宠物）
4. 查看家庭信息和成员列表

使用工具时请注意：
- create_family：首次使用时创建家庭
- generate_invite_link：生成邀请链接发给家人
- join_family：用户通过邀请码加入家庭
- add_family_member：添加小孩或宠物（大人通过邀请链接加入）

重要规则：
- 每个飞书用户只能加入一个家庭
- 家庭内共享库存数据，家庭间隔离
- 大人通过邀请链接加入，小孩/宠物由管理员添加"""

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tool definitions for this skill."""
        return get_family_tools()

    def execute_tool(self, db: Session, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """Execute a tool for this skill."""
        # Family tools need user_open_id from context
        # This is called from orchestrator with context
        import asyncio

        # Placeholder: will be integrated with orchestrator
        return execute_family_tool(db, tool_name, tool_args, "placeholder_open_id")

    def format_response(self, reply: str, actions: List[Dict], context: Dict) -> Dict:
        """Format response for Feishu."""
        return {
            "type": "text",
            "content": reply
        }


__all__ = [
    'get_family_tools',
    'execute_family_tool',
    'FamilySkill'
]