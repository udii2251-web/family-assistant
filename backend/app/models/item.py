from sqlalchemy import Integer, String, Float, Column, ForeignKey

from app.shared.database import Base


class ItemCategory(Base):
    __tablename__ = "item_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)
    icon = Column(String(50), nullable=True)


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    category_id = Column(Integer, ForeignKey("item_categories.id"), nullable=True)
    unit = Column(String(20), nullable=False)  # kg / L / 包 / 瓶 etc.
    typical_size = Column(Float, nullable=True)  # typical purchase quantity
    target_audience = Column(String(20), default="all")  # all / child / dog
