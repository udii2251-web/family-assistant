from sqlalchemy import Integer, String, Float, Column

from app.database import Base


class FamilyMember(Base):
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
