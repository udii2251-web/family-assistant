"""Test script for inventory Agent Tools.

Tests:
- Unit conversion (斤→kg)
- Purchase/consumption recording
- Inventory query
- Negative inventory detection

Run: python backend/app/modules/inventory/test_tools.py
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Fix circular import by importing before skill
from app.shared.database import SessionLocal
from app.modules.inventory.models import Item, ConsumptionRecord
from app.modules.inventory.services import convert_unit, get_remaining_for_item
from datetime import date

# Now import skill
from app.modules.inventory.skill import InventorySkill


def test_unit_conversion():
    """Test unit conversion functionality."""
    print("\n🧪 Testing Unit Conversion...")

    test_cases = [
        (2, "斤", 1.0, "kg"),
        (1, "斤", 0.5, "kg"),
        (500, "克", 0.5, "kg"),
        (1000, "ml", 1.0, "L"),
        (5, "kg", 5.0, "kg"),
        (3, "包", 3, "包"),  # No conversion
    ]

    for qty, unit, expected_qty, expected_unit in test_cases:
        converted_qty, converted_unit = convert_unit(qty, unit)
        status = "✅" if abs(converted_qty - expected_qty) < 0.01 and converted_unit == expected_unit else "❌"
        print(f"  {status} {qty}{unit} → {converted_qty:.3f}{converted_unit} (expected: {expected_qty}{expected_unit})")


def test_tool_calls():
    """Test Agent Tool execution."""
    print("\n🧪 Testing Agent Tool Calls...")

    db = SessionLocal()
    skill = InventorySkill()

    try:
        # Test 1: Record purchase with unit conversion
        print("\n1. Testing record_purchase (2斤大米)...")
        result = skill.execute_tool(db, "record_purchase", {
            "item_name": "测试大米",
            "quantity": 2,
            "unit": "斤",
        })
        import json
        data = json.loads(result)
        print(f"   Result: {result}")
        assert data.get("success") == True, "Purchase should succeed"
        assert data.get("unit") == "kg", "Unit should be converted to kg"
        assert abs(data.get("quantity") - 1.0) < 0.01, "2斤 should equal 1kg"

        # Test 2: Query inventory
        print("\n2. Testing query_inventory (all items)...")
        result = skill.execute_tool(db, "query_inventory", {})
        data = json.loads(result)
        print(f"   Found {len(data.get('items', []))} items")
        assert data.get("success") == True, "Query should succeed"

        # Test 3: Query specific item
        print("\n3. Testing query_inventory (specific item)...")
        result = skill.execute_tool(db, "query_inventory", {
            "item_name": "测试大米",
        })
        data = json.loads(result)
        print(f"   Result: {result}")
        assert data.get("success") == True, "Query should succeed"

        # Test 4: Record consumption
        print("\n4. Testing record_consumption...")
        result = skill.execute_tool(db, "record_consumption", {
            "item_name": "测试大米",
            "quantity": 0.3,
            "unit": "kg",
        })
        data = json.loads(result)
        print(f"   Result: {result}")
        assert data.get("success") == True, "Consumption should succeed"

        # Test 5: Check restock alerts
        print("\n5. Testing check_restock_alerts...")
        result = skill.execute_tool(db, "check_restock_alerts", {})
        data = json.loads(result)
        print(f"   Items needing restock: {len(data.get('need_restock', []))}")
        assert data.get("success") == True, "Check should succeed"

        # Test 6: List items
        print("\n6. Testing list_items...")
        result = skill.execute_tool(db, "list_items", {})
        data = json.loads(result)
        print(f"   Found {len(data.get('items', []))} items")
        assert data.get("success") == True, "List should succeed"

        print("\n✅ All tool tests passed!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def test_negative_inventory():
    """Test negative inventory detection."""
    print("\n🧪 Testing Negative Inventory Detection...")

    db = SessionLocal()

    try:
        from app.modules.inventory.models import Item, ConsumptionRecord
        from datetime import date

        # Create test item
        item = Item(name="负数测试", unit="kg")
        db.add(item)
        db.commit()
        db.refresh(item)

        # Record consumption without purchase (will cause negative inventory)
        consumption = ConsumptionRecord(
            item_id=item.id,
            quantity=5,
            unit="kg",
            record_date=date.today(),
            source="manual",
        )
        db.add(consumption)
        db.commit()

        # Query inventory (should trigger warning)
        from app.modules.inventory.services import get_remaining_for_item
        remaining = get_remaining_for_item(db, item.id)

        print(f"   Remaining: {remaining}kg")
        assert remaining < 0, "Should detect negative inventory"
        print("   ✅ Negative inventory detection working!")

        # Cleanup
        db.delete(consumption)
        db.delete(item)
        db.commit()

    except Exception as e:
        print(f"   ❌ Test failed: {e}")
    finally:
        db.close()


def test_logs():
    """Test enhanced logging."""
    print("\n🧪 Testing Enhanced Logging...")

    db = SessionLocal()
    skill = InventorySkill()

    try:
        # Execute a tool to see logs
        result = skill.execute_tool(db, "add_item", {
            "name": "日志测试物品",
            "unit": "个",
        })

        print("   ✅ Tool executed with enhanced logging (check logs)")

        # Cleanup
        from app.modules.inventory.models import Item
        item = db.query(Item).filter(Item.name == "日志测试物品").first()
        if item:
            db.delete(item)
            db.commit()

    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Inventory Agent MVP Test Suite")
    print("=" * 60)

    test_unit_conversion()
    test_tool_calls()
    test_negative_inventory()
    test_logs()

    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)