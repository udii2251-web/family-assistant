"""Inventory module services.

Merged from 2 service files:
- inventory.py (库存计算逻辑)
- alert_scheduler.py (补货提醒生成)
"""

from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.modules.inventory.models import Item, PurchaseRecord, ConsumptionRecord, RestockAlert
from app.schemas.schemas import InventoryItemOut
from app.shared.config import ALERT_THRESHOLD_DAYS, DEFAULT_DAILY_RATE_FOR_NEW_ITEM


def get_remaining_for_item(db: Session, item_id: int) -> float:
    """Calculate remaining quantity by: total purchased - total consumed."""
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

    return purchased_sum - consumed_sum


def get_avg_daily_rate(db: Session, item_id: int) -> Optional[float]:
    """Calculate average daily consumption rate for an item."""
    records = (
        db.query(ConsumptionRecord)
        .filter(ConsumptionRecord.item_id == item_id)
        .order_by(ConsumptionRecord.record_date)
        .all()
    )
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


def get_inventory_overview(db: Session) -> list[InventoryItemOut]:
    """Get inventory overview for all items with remaining amounts."""
    items = db.query(Item).all()
    result = []

    for item in items:
        remaining = get_remaining_for_item(db, item.id)
        avg_rate = get_avg_daily_rate(db, item.id)

        if avg_rate and avg_rate > 0 and remaining > 0:
            days_until_empty = int(remaining / avg_rate)
            estimated_empty = date.today() + timedelta(days=days_until_empty)
        else:
            days_until_empty = None
            estimated_empty = None

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