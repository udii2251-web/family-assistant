"""Taobao order data models.

Defines:
- TaobaoOrder model (for order sync data)
- TaobaoOrderItem model (for order items)
- TaobaoAuthStatus model (for login status tracking)
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.sql import func
from datetime import datetime
from app.shared.database import Base


class TaobaoOrder(Base):
    """淘宝订单主表"""

    __tablename__ = "taobao_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    family_id = Column(String(64), ForeignKey("families.family_id"), nullable=True, index=True, comment="关联家庭（数据隔离）")
    order_id = Column(String(64), unique=True, index=True, nullable=False, comment="淘宝订单号")
    product_name = Column(String(500), comment="商品名称（简短）")
    shop_name = Column(String(200), comment="店铺名称")
    total_price = Column(Float, comment="订单总金额")
    order_time = Column(DateTime, comment="下单时间")
    status = Column(String(50), comment="订单状态（已付款、已发货、已完成等）")
    synced_at = Column(DateTime, default=datetime.utcnow, comment="同步时间")

    # 订单详情
    buyer_nick = Column(String(100), comment="买家昵称")
    pay_time = Column(DateTime, comment="付款时间")
    ship_time = Column(DateTime, comment="发货时间")
    complete_time = Column(DateTime, comment="完成时间")

    # 订单地址
    receiver_name = Column(String(100), comment="收货人姓名")
    receiver_mobile = Column(String(20), comment="收货人手机号")
    receiver_address = Column(String(500), comment="收货地址")

    # 备注
    remark = Column(Text, comment="订单备注")

    # 是否已同步到库存
    synced_to_inventory = Column(Boolean, default=False, comment="是否已同步到库存")

    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<TaobaoOrder(order_id={self.order_id}, product_name={self.product_name}, price={self.total_price})>"


class TaobaoOrderItem(Base):
    """淘宝订单商品明细表"""

    __tablename__ = "taobao_order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(64), index=True, nullable=False, comment="关联订单号")
    item_id = Column(String(64), comment="商品ID")
    product_name = Column(String(500), comment="商品名称")
    sku_name = Column(String(200), comment="SKU名称（规格）")
    quantity = Column(Integer, comment="购买数量")
    unit_price = Column(Float, comment="单价")
    total_price = Column(Float, comment="小计金额")
    product_image = Column(String(500), comment="商品图片URL")

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<TaobaoOrderItem(order_id={self.order_id}, product={self.product_name}, qty={self.quantity})>"


class TaobaoAuthStatus(Base):
    """淘宝登录授权状态表"""

    __tablename__ = "taobao_auth_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    is_logged_in = Column(Boolean, default=False, comment="是否已登录")
    last_login_time = Column(DateTime, comment="最后登录时间")
    last_check_time = Column(DateTime, comment="最后检查时间")
    login_expiry_time = Column(DateTime, comment="登录过期时间")
    cookie_file = Column(String(500), comment="Cookie文件路径")
    user_nick = Column(String(100), comment="淘宝账号昵称")
    user_id = Column(String(100), comment="淘宝用户ID")

    # 状态
    status_message = Column(Text, comment="状态消息")
    needs_reauth = Column(Boolean, default=False, comment="是否需要重新授权")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<TaobaoAuthStatus(logged_in={self.is_logged_in}, nick={self.user_nick})>"