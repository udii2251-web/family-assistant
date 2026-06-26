"""Test data seeder for inventory module.

Creates sample data for testing:
- Family members
- Item categories
- Items
- Purchase records
- Consumption records

Run: python backend/app/modules/inventory/test_data.py
"""

import sys
import os
from datetime import date, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from app.shared.database import SessionLocal, init_db
from app.modules.inventory.models import FamilyMember, ItemCategory, Item, PurchaseRecord, ConsumptionRecord


def seed_test_data():
    """Seed database with test data."""
    db = SessionLocal()

    try:
        # Clear existing data (optional)
        print("⚠️ Clearing existing data...")
        db.query(ConsumptionRecord).delete()
        db.query(PurchaseRecord).delete()
        db.query(Item).delete()
        db.query(ItemCategory).delete()
        db.query(FamilyMember).delete()
        db.commit()

        # Create family members
        print("👨‍👩‍👧‍👦 Creating family members...")
        members = [
            FamilyMember(name="爸爸", type="adult", age=45, feishu_open_id="ou_test_001", responsibilities="食品,采购"),
            FamilyMember(name="妈妈", type="adult", age=42, feishu_open_id="ou_test_002", responsibilities="洗护,清洁"),
            FamilyMember(name="爷爷", type="adult", age=70, feishu_open_id="ou_test_003"),
            FamilyMember(name="奶奶", type="adult", age=68, feishu_open_id="ou_test_004"),
            FamilyMember(name="小明", type="child", age=8, feishu_open_id=None),
            FamilyMember(name="豆豆", type="dog", age=3, breed="泰迪", weight=5),
            FamilyMember(name="花花", type="dog", age=2, breed="柯基", weight=8),
        ]
        for m in members:
            db.add(m)
        db.commit()

        # Create categories
        print("📦 Creating categories...")
        categories = [
            ItemCategory(name="食品", icon="🍎"),
            ItemCategory(name="洗护", icon="🧴"),
            ItemCategory(name="宠物用品", icon="🐕"),
            ItemCategory(name="清洁", icon="🧹"),
            ItemCategory(name="儿童用品", icon="🧸"),
        ]
        for c in categories:
            db.add(c)
        db.commit()

        # Create items
        print("🛒 Creating items...")
        items = [
            Item(name="大米", unit="kg", category_id=1, target_audience="all"),
            Item(name="牛奶", unit="L", category_id=1, target_audience="all"),
            Item(name="狗粮", unit="kg", category_id=3, target_audience="dog"),
            Item(name="洗衣液", unit="L", category_id=2, target_audience="all"),
            Item(name="卫生纸", unit="包", category_id=4, target_audience="all"),
            Item(name="儿童牛奶", unit="L", category_id=5, target_audience="child"),
            Item(name="狗零食", unit="包", category_id=3, target_audience="dog"),
            Item(name="食用油", unit="L", category_id=1, target_audience="all"),
        ]
        for i in items:
            db.add(i)
        db.commit()

        # Create purchase records (past 30 days)
        print("🛍️ Creating purchase records...")
        purchases = [
            # 大米: bought 10kg 20 days ago
            PurchaseRecord(item_id=1, quantity=10, unit="kg", purchase_date=date.today() - timedelta(days=20)),
            # 牛奶: bought 6L 15 days ago
            PurchaseRecord(item_id=2, quantity=6, unit="L", purchase_date=date.today() - timedelta(days=15)),
            # 狗粮: bought 5kg 10 days ago
            PurchaseRecord(item_id=3, quantity=5, unit="kg", purchase_date=date.today() - timedelta(days=10)),
            # 洗衣液: bought 3L 25 days ago
            PurchaseRecord(item_id=4, quantity=3, unit="L", purchase_date=date.today() - timedelta(days=25)),
            # 卫生纸: bought 2包 5 days ago
            PurchaseRecord(item_id=5, quantity=2, unit="包", purchase_date=date.today() - timedelta(days=5)),
            # 儿童牛奶: bought 4L 12 days ago
            PurchaseRecord(item_id=6, quantity=4, unit="L", purchase_date=date.today() - timedelta(days=12)),
        ]
        for p in purchases:
            db.add(p)
        db.commit()

        # Create consumption records (past 20 days)
        print("📉 Creating consumption records...")
        consumptions = [
            # 大米: consumed 0.3kg/day for 20 days = 6kg
            PurchaseRecord(item_id=1, quantity=6, unit="kg", purchase_date=date.today() - timedelta(days=20)),
        ]

        # More realistic consumption
        for i in range(20):
            day = date.today() - timedelta(days=i)
            # 大米: 0.3kg/day
            db.add(ConsumptionRecord(item_id=1, quantity=0.3, unit="kg", record_date=day, source="manual"))
            # 牛奶: 0.2L/day
            db.add(ConsumptionRecord(item_id=2, quantity=0.2, unit="L", record_date=day, source="manual"))
            # 狗粮: 0.2kg/day (for 2 dogs)
            db.add(ConsumptionRecord(item_id=3, quantity=0.2, unit="kg", record_date=day, source="manual"))
            # 洗衣液: 0.05L/day (average)
            if i % 3 == 0:  # Not every day
                db.add(ConsumptionRecord(item_id=4, quantity=0.1, unit="L", record_date=day, source="manual"))
            # 卫生纸: 0.1包/day
            if i % 2 == 0:
                db.add(ConsumptionRecord(item_id=5, quantity=0.1, unit="包", record_date=day, source="manual"))
            # 儿童牛奶: 0.3L/day
            db.add(ConsumptionRecord(item_id=6, quantity=0.3, unit="L", record_date=day, source="manual"))

        db.commit()

        print("✅ Test data seeded successfully!")
        print("\n📊 Summary:")
        print(f"  Family members: {len(members)}")
        print(f"  Categories: {len(categories)}")
        print(f"  Items: {len(items)}")
        print(f"  Purchase records: {len(purchases)}")
        print(f"  Consumption records: ~{20 * 5}")

        # Verify inventory status
        print("\n📦 Inventory status:")
        from app.modules.inventory.services import get_inventory_overview
        overview = get_inventory_overview(db)
        for item in overview:
            status = ""
            if item.days_until_empty is not None:
                if item.days_until_empty <= 3:
                    status = "⚠️ CRITICAL"
                elif item.days_until_empty <= 7:
                    status = "🔴 LOW"
                else:
                    status = "✅ GOOD"
            print(f"  {item.item_name}: {item.remaining:.1f}{item.unit} - {item.days_until_empty or 'N/A'} days left {status}")

    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    seed_test_data()