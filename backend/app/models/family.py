"""家庭组织架构 - 多家庭隔离设计

实现家庭组织管理功能：
1. Family表：家庭组织（支持多家庭隔离）
2. FamilyMember表：家庭成员（关联到家庭）
3. 邀请机制：生成邀请链接，邀请其他飞书用户加入
4. 数据隔离：所有物品、库存、订单都关联到family_id

使用方式：
- 用户通过飞书机器人创建家庭
- 发送邀请链接给家人
- 家人点击链接加入家庭
- 家庭内共享库存数据，家庭间隔离
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from datetime import datetime

from app.shared.database import Base


class Family(Base):
    """家庭组织表 - 支持多家庭隔离"""

    __tablename__ = "families"

    id = Column(Integer, primary_key=True, autoincrement=True)
    family_id = Column(String(64), unique=True, index=True, nullable=False, comment="家庭唯一标识（用于邀请链接）")
    family_name = Column(String(100), nullable=False, comment="家庭名称")
    creator_open_id = Column(String(100), nullable=False, comment="创建者的飞书open_id")

    # 邀请机制
    invite_code = Column(String(32), nullable=False, comment="邀请码（用于验证加入）")
    invite_link = Column(String(200), nullable=True, comment="邀请链接")
    invite_expires_at = Column(DateTime, nullable=True, comment="邀请链接过期时间")

    # 家庭统计
    adult_count = Column(Integer, default=0, comment="大人数量")
    child_count = Column(Integer, default=0, comment="小孩数量")
    pet_count = Column(Integer, default=0, comment="宠物数量")

    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<Family(family_id={self.family_id}, name={self.family_name}, members={self.adult_count}大人{self.child_count}小孩{self.pet_count}宠物)>"


class FamilyMember(Base):
    """家庭成员表 - 关联到家庭组织"""

    __tablename__ = "family_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    family_id = Column(String(64), ForeignKey("families.family_id"), nullable=False, index=True, comment="关联家庭")

    # 成员基本信息
    member_type = Column(String(20), nullable=False, comment="成员类型: adult/child/dog/cat")
    name = Column(String(50), nullable=False, comment="成员姓名/昵称")
    age = Column(Integer, nullable=True, comment="年龄（大人/小孩）")
    weight = Column(Float, nullable=True, comment="体重（宠物）")
    breed = Column(String(50), nullable=True, comment="品种（宠物）")

    # 飞书关联（只有大人会有）
    feishu_open_id = Column(String(100), nullable=True, unique=True, comment="飞书用户open_id（大人）")
    is_feishu_user = Column(Boolean, default=False, comment="是否是飞书用户（大人）")

    # 加入信息
    joined_at = Column(DateTime, default=datetime.utcnow, comment="加入时间")
    invited_by = Column(String(100), nullable=True, comment="邀请者open_id")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<FamilyMember(family={self.family_id}, type={self.member_type}, name={self.name})>"