from sqlalchemy import Integer, String, Float, Column, ForeignKey, Date

from app.shared.database import Base


class PurchaseRecord(Base):
    __tablename__ = "purchase_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    purchase_date = Column(Date, nullable=False)
    remaining = Column(Float, nullable=True)  # remaining amount after purchase
