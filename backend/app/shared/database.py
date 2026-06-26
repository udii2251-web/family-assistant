import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.shared.config import DB_PATH, DATA_DIR

os.makedirs(DATA_DIR, exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def init_db():
    from app.modules.inventory.models import FamilyMember, ItemCategory, Item
    from app.modules.inventory.models import ConsumptionRecord, PurchaseRecord, RestockAlert
    # Taobao module models
    from app.modules.taobao.models import TaobaoOrder, TaobaoOrderItem, TaobaoAuthStatus
    # ProductComparison model is standalone, keep in shared location or move later
    try:
        from app.models.product_comparison import ProductComparison
    except ImportError:
        pass

    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()