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
    from app.models.family import FamilyMember
    from app.models.item import ItemCategory, Item
    from app.models.consumption import ConsumptionRecord
    from app.models.purchase import PurchaseRecord
    from app.models.alert import RestockAlert
    from app.models.product_comparison import ProductComparison

    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
