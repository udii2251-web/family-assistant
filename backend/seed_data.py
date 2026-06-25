"""Seed initial data: family members, item categories, items, and sample consumption records.

Updated to include feishu_open_id and responsibilities for each family member.
"""
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.database import SessionLocal, init_db
from app.models.family import FamilyMember
from app.models.item import ItemCategory, Item
from app.models.purchase import PurchaseRecord
from app.models.consumption import ConsumptionRecord


def seed():
    init_db()
    db = SessionLocal()

    # --- Family members (with feishu identity and responsibilities) ---
    members = [
        FamilyMember(name="大人1", type="adult", weight=65,
                     feishu_open_id="ou_placeholder_1",
                     responsibilities="食品,洗护,购物",
                     notification_prefs="all"),
        FamilyMember(name="大人2", type="adult", weight=60,
                     feishu_open_id="ou_placeholder_2",
                     responsibilities="清洁,纸品",
                     notification_prefs="all"),
        FamilyMember(name="大人3", type="adult", weight=70,
                     feishu_open_id="ou_placeholder_3",
                     responsibilities="宠物用品",
                     notification_prefs="urgent_only"),
        FamilyMember(name="大人4", type="adult", weight=55,
                     feishu_open_id="ou_placeholder_4",
                     responsibilities="食品",
                     notification_prefs="all"),
        FamilyMember(name="小朋友", type="child", age=6, weight=20,
                     notification_prefs="none"),
        FamilyMember(name="小狗1", type="dog", weight=8),
        FamilyMember(name="小狗2", type="dog", weight=5),
    ]
    for m in members:
        existing = db.query(FamilyMember).filter(FamilyMember.name == m.name).first()
        if not existing:
            db.add(m)

    # --- Categories ---
    categories = [
        ItemCategory(name="食品", icon="🍚"),
        ItemCategory(name="洗护", icon="🧴"),
        ItemCategory(name="宠物用品", icon="🐶"),
        ItemCategory(name="清洁", icon="🧹"),
        ItemCategory(name="纸品", icon="📄"),
        ItemCategory(name="其他", icon="📦"),
    ]
    for c in categories:
        existing = db.query(ItemCategory).filter(ItemCategory.name == c.name).first()
        if not existing:
            db.add(c)
    db.commit()

    # --- Items ---
    cat_food = db.query(ItemCategory).filter(ItemCategory.name == "食品").first()
    cat_care = db.query(ItemCategory).filter(ItemCategory.name == "洗护").first()
    cat_pet = db.query(ItemCategory).filter(ItemCategory.name == "宠物用品").first()
    cat_clean = db.query(ItemCategory).filter(ItemCategory.name == "清洁").first()
    cat_paper = db.query(ItemCategory).filter(ItemCategory.name == "纸品").first()

    items_data = [
        Item(name="大米", category_id=cat_food.id, unit="kg", typical_size=5, target_audience="all"),
        Item(name="食用油", category_id=cat_food.id, unit="L", typical_size=1, target_audience="all"),
        Item(name="牛奶", category_id=cat_food.id, unit="L", typical_size=1, target_audience="all"),
        Item(name="洗衣液", category_id=cat_care.id, unit="L", typical_size=2, target_audience="all"),
        Item(name="洗发水", category_id=cat_care.id, unit="瓶", typical_size=1, target_audience="all"),
        Item(name="牙膏", category_id=cat_care.id, unit="支", typical_size=1, target_audience="all"),
        Item(name="狗粮", category_id=cat_pet.id, unit="kg", typical_size=5, target_audience="dog"),
        Item(name="狗零食", category_id=cat_pet.id, unit="包", typical_size=10, target_audience="dog"),
        Item(name="洗洁精", category_id=cat_clean.id, unit="L", typical_size=1, target_audience="all"),
        Item(name="卫生纸", category_id=cat_paper.id, unit="卷", typical_size=10, target_audience="all"),
    ]
    for i in items_data:
        existing = db.query(Item).filter(Item.name == i.name).first()
        if not existing:
            db.add(i)
    db.commit()

    # --- Sample purchases (7 days ago) ---
    today = date.today()
    week_ago = today - timedelta(days=7)

    purchases = [
        PurchaseRecord(item_id=1, quantity=5, unit="kg", purchase_date=week_ago, remaining=5),
        PurchaseRecord(item_id=2, quantity=1, unit="L", purchase_date=week_ago, remaining=1),
        PurchaseRecord(item_id=3, quantity=2, unit="L", purchase_date=week_ago, remaining=2),
        PurchaseRecord(item_id=4, quantity=2, unit="L", purchase_date=week_ago, remaining=2),
        PurchaseRecord(item_id=7, quantity=5, unit="kg", purchase_date=week_ago, remaining=5),
        PurchaseRecord(item_id=9, quantity=1, unit="L", purchase_date=week_ago, remaining=1),
        PurchaseRecord(item_id=10, quantity=10, unit="卷", purchase_date=week_ago, remaining=10),
    ]
    for p in purchases:
        db.add(p)
    db.commit()

    # --- Sample consumption over the past 7 days ---
    daily_consumption = {
        1: [("kg", 0.5)],   # 大米 0.5kg/day
        2: [("L", 0.03)],   # 食用油
        3: [("L", 0.3)],    # 牛奶
        4: [("L", 0.05)],   # 洗衣液
        7: [("kg", 0.4)],   # 狗粮
        9: [("L", 0.02)],   # 洗洁精
        10: [("卷", 1)],    # 卫生纸
    }

    for day_offset in range(7):
        d = today - timedelta(days=6 - day_offset)
        for item_id, consumptions in daily_consumption.items():
            for unit, qty in consumptions:
                record = ConsumptionRecord(
                    item_id=item_id, quantity=qty, unit=unit,
                    record_date=d, note="", source="manual",
                )
                db.add(record)

    db.commit()
    db.close()
    print("Seed data loaded successfully!")


if __name__ == "__main__":
    seed()
