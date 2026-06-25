from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.alert import RestockAlert
from app.models.item import Item
from app.services.inventory import get_items_needing_restock, get_avg_daily_rate
from app.config import ALERT_THRESHOLD_DAYS


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
