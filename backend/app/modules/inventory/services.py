"""Inventory module services.

Merged from 2 service files:
- inventory.py (库存计算逻辑)
- alert_scheduler.py (补货提醒生成)
"""

from datetime import date, timedelta
from typing import Optional
import logging

from sqlalchemy.orm import Session

from app.modules.inventory.models import Item, PurchaseRecord, ConsumptionRecord, RestockAlert
from app.schemas.schemas import InventoryItemOut
from app.shared.config import ALERT_THRESHOLD_DAYS, DEFAULT_DAILY_RATE_FOR_NEW_ITEM

logger = logging.getLogger(__name__)

# Unit conversion mappings (to kg or L)
UNIT_CONVERSIONS = {
    # Weight conversions (to kg)
    "斤": 0.5,
    "市斤": 0.5,
    "两": 0.05,
    "克": 0.001,
    "g": 0.001,
    "kg": 1.0,
    "公斤": 1.0,
    "千克": 1.0,
    # Volume conversions (to L)
    "毫升": 0.001,
    "ml": 0.001,
    "L": 1.0,
    "升": 1.0,
    "公升": 1.0,
}

# Standard units for normalization
STANDARD_UNITS = {
    "斤": "kg",
    "市斤": "kg",
    "两": "kg",
    "克": "kg",
    "g": "kg",
    "kg": "kg",
    "公斤": "kg",
    "千克": "kg",
    "毫升": "L",
    "ml": "L",
    "L": "L",
    "升": "L",
    "公升": "L",
}


def convert_unit(quantity: float, from_unit: str) -> tuple[float, str]:
    """Convert quantity from one unit to standard unit.

    Args:
        quantity: Original quantity
        from_unit: Original unit

    Returns:
        Tuple of (converted_quantity, standard_unit)
    """
    from_unit_lower = from_unit.lower() if from_unit else ""

    # Check if conversion is needed
    if from_unit_lower not in UNIT_CONVERSIONS:
        logger.debug(f"Unit '{from_unit}' not in conversion table, keeping as-is")
        return quantity, from_unit

    # Convert to standard unit
    conversion_factor = UNIT_CONVERSIONS[from_unit_lower]
    standard_unit = STANDARD_UNITS.get(from_unit_lower, from_unit)
    converted_quantity = quantity * conversion_factor

    logger.debug(f"Converted {quantity}{from_unit} to {converted_quantity:.3f}{standard_unit}")

    return converted_quantity, standard_unit


def get_remaining_for_item(db: Session, item_id: int) -> float:
    """Calculate remaining quantity by: total purchased - total consumed.

    Returns:
        Remaining quantity (negative values logged as warning)
    """
    total_purchased = (
        db.query(PurchaseRecord)
        .filter(PurchaseRecord.item_id == item_id)
        .with_entities(PurchaseRecord.quantity)
    )
    purchased_sum = sum(r.quantity for r in total_purchased.all()) if total_purchased.count() > 0 else 0.0

    total_consumed = (
        db.query(ConsumptionRecord)
        .filter(ConsumptionRecord.item_id == item_id)
        .with_entities(ConsumptionRecord.quantity)
    )
    consumed_sum = sum(r.quantity for r in total_consumed.all()) if total_consumed.count() > 0 else 0.0

    remaining = purchased_sum - consumed_sum

    # Check for negative inventory
    if remaining < 0:
        item = db.query(Item).filter(Item.id == item_id).first()
        item_name = item.name if item else f"Item#{item_id}"
        logger.warning(f"⚠️ Negative inventory detected: {item_name} has {remaining:.2f} units")
        logger.warning(f"   Purchased: {purchased_sum:.2f}, Consumed: {consumed_sum:.2f}")
        logger.warning(f"   This may indicate missing purchase records")

    return remaining


def get_avg_daily_rate(db: Session, item_id: int, buyer_open_id: str = None, family_id: str = None) -> Optional[float]:
    """Calculate average daily consumption rate for an item (with family isolation)."""
    from app.modules.inventory.models import Item

    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        return None

    # Query consumptions with family isolation
    query = db.query(ConsumptionRecord).filter(ConsumptionRecord.item_id == item_id)
    if family_id:
        query = query.filter(ConsumptionRecord.family_id == family_id)

    records = query.order_by(ConsumptionRecord.record_date).all()

    if not records:
        return None

    total_consumed = sum(r.quantity for r in records)
    first_date = records[0].record_date
    last_date = records[-1].record_date
    days_span = (last_date - first_date).days

    if days_span <= 0:
        # Only one day of data — use total consumed as daily rate estimate
        return total_consumed if total_consumed > 0 else DEFAULT_DAILY_RATE_FOR_NEW_ITEM

    return total_consumed / days_span


def get_inventory_overview(db: Session, family_id: str = None) -> list[InventoryItemOut]:
    """Get inventory overview for all items with remaining amounts (with family isolation)."""
    # Query items with family isolation
    query = db.query(Item)
    if family_id:
        query = query.filter(Item.family_id == family_id)

    items = query.all()
    result = []

    logger.info(f"📊 Calculating inventory overview for {len(items)} items")

    for item in items:
        remaining = get_remaining_for_item(db, item.id)
        avg_rate = get_avg_daily_rate(db, item.id)

        # Determine inventory status
        status = "unknown"
        if remaining <= 0:
            status = "empty"
        elif avg_rate and avg_rate > 0:
            days_until_empty = int(remaining / avg_rate)
            if days_until_empty <= ALERT_THRESHOLD_DAYS:
                status = "critical"
            elif days_until_empty <= 7:
                status = "low"
            else:
                status = "good"
            estimated_empty = date.today() + timedelta(days=days_until_empty)
        else:
            days_until_empty = None
            estimated_empty = None
            if remaining > 0:
                status = "no_rate"

        result.append(
            InventoryItemOut(
                item_id=item.id,
                item_name=item.name,
                unit=item.unit,
                remaining=remaining,
                avg_daily_rate=avg_rate,
                estimated_empty_date=estimated_empty,
                days_until_empty=days_until_empty,
            )
        )

        logger.debug(f"  {item.name}: {remaining:.1f}{item.unit} - status={status}")

    # Count items by status
    critical_count = sum(1 for i in result if i.days_until_empty is not None and i.days_until_empty <= ALERT_THRESHOLD_DAYS)
    if critical_count > 0:
        logger.warning(f"⚠️ {critical_count} items need urgent restocking")

    return result


def get_items_needing_restock(db: Session) -> list[InventoryItemOut]:
    """Return items where days_until_empty is below the threshold."""
    overview = get_inventory_overview(db)
    return [i for i in overview if i.days_until_empty is not None and i.days_until_empty <= ALERT_THRESHOLD_DAYS]


def generate_restock_alerts(db: Session):
    """Check all items and generate alerts for those nearing depletion."""
    items_needing_restock = get_items_needing_restock(db)

    for inv_item in items_needing_restock:
        item = db.query(Item).filter(Item.id == inv_item.item_id).first()

        # Skip if an active alert already exists for this item
        existing = (
            db.query(RestockAlert)
            .filter(RestockAlert.item_id == inv_item.item_id, RestockAlert.status.in_(["pending", "notified"]))
            .first()
        )
        if existing:
            continue

        avg_rate = inv_item.avg_daily_rate or 0.1
        # Suggest buying enough for 14 days
        suggested_qty = avg_rate * 14

        message = (
            f"{inv_item.item_name}还剩{inv_item.remaining:.1f}{inv_item.unit}，"
            f"按每天消耗{avg_rate:.2f}{inv_item.unit}的速度，"
            f"预计{inv_item.days_until_empty}天后用完，建议尽快补货！"
        )

        alert = RestockAlert(
            item_id=inv_item.item_id,
            alert_date=date.today(),
            estimated_empty_date=inv_item.estimated_empty_date,
            suggested_quantity=suggested_qty,
            status="pending",
            message=message,
        )
        db.add(alert)

    db.commit()