"""Inventory module data models.

Merged from:
- family.py (FamilyMember)
- item.py (ItemCategory, Item)
- purchase.py (PurchaseRecord)
- consumption.py (ConsumptionRecord)
- alert.py (RestockAlert)
"""

from sqlalchemy import Integer, String, Float, Column, ForeignKey, Date

from app.shared.database import Base


class FamilyMember(Base):
    """Family member (adult, child, or pet)."""
    __tablename__ = "family_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    type = Column(String(20), nullable=False)  # adult / child / dog
    age = Column(Integer, nullable=True)
    weight = Column(Float, nullable=True)
    breed = Column(String(50), nullable=True)  # pet breed
    # Feishu integration fields
    feishu_open_id = Column(String(100), nullable=True, unique=True)  # Feishu user identity
    responsibilities = Column(String(200), nullable=True)  # comma-separated: "食品,洗护,宠物用品"
    notification_prefs = Column(String(100), nullable=True, default="all")  # "all" / "urgent_only" / "none"


class ItemCategory(Base):
    """Item category (食品, 洗护, etc.)."""
    __tablename__ = "item_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)
    icon = Column(String(50), nullable=True)


class Item(Base):
    """Item type (大米, 牛奶, etc.)."""
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    category_id = Column(Integer, ForeignKey("item_categories.id"), nullable=True)
    unit = Column(String(20), nullable=False)  # kg / L / 包 / 瓶 etc.
    typical_size = Column(Float, nullable=True)  # typical purchase quantity
    target_audience = Column(String(20), default="all")  # all / child / dog


class PurchaseRecord(Base):
    """Purchase record (增加库存)."""
    __tablename__ = "purchase_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    purchase_date = Column(Date, nullable=False)
    remaining = Column(Float, nullable=True)  # remaining amount after purchase


class ConsumptionRecord(Base):
    """Consumption record (减少库存)."""
    __tablename__ = "consumption_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    record_date = Column(Date, nullable=False)
    note = Column(String(200), nullable=True)
    source = Column(String(20), default="manual")  # manual / chat_import


class RestockAlert(Base):
    """Restock alert (补货提醒)."""
    __tablename__ = "restock_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    alert_date = Column(Date, nullable=False)
    estimated_empty_date = Column(Date, nullable=True)
    suggested_quantity = Column(Float, nullable=True)
    status = Column(String(20), default="pending")  # pending / notified / done
    message = Column(String(500), nullable=True)