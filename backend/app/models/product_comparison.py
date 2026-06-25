"""Product comparison model — caches search results to avoid repeated API calls."""

from sqlalchemy import Integer, String, Float, Column, ForeignKey, DateTime, Text
from datetime import datetime

from app.database import Base


class ProductComparison(Base):
    __tablename__ = "product_comparisons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    search_query = Column(String(200), nullable=False)  # the search query used
    platform = Column(String(20), nullable=False)  # "taobao", "jd", "pdd"
    product_name = Column(String(200), nullable=False)
    price = Column(Float, nullable=False)
    product_url = Column(Text, nullable=True)  # web URL
    deep_link = Column(Text, nullable=True)  # app deep link URL
    search_date = Column(DateTime, default=datetime.utcnow)
    is_available = Column(Integer, default=1)  # 1=available, 0=unavailable
