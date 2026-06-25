from sqlalchemy import Integer, String, Float, Column, ForeignKey, Date

from app.database import Base


class ConsumptionRecord(Base):
    __tablename__ = "consumption_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    record_date = Column(Date, nullable=False)
    note = Column(String(200), nullable=True)
    source = Column(String(20), default="manual")  # manual / chat_import
