from sqlalchemy import Integer, String, Float, Column, ForeignKey, Date

from app.shared.database import Base


class RestockAlert(Base):
    __tablename__ = "restock_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    alert_date = Column(Date, nullable=False)
    estimated_empty_date = Column(Date, nullable=True)
    suggested_quantity = Column(Float, nullable=True)
    status = Column(String(20), default="pending")  # pending / notified / done
    message = Column(String(500), nullable=True)
