from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.models.alert import RestockAlert
from app.schemas.schemas import AlertOut, AlertUpdate

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/", response_model=List[AlertOut])
def list_alerts(status: str = None, db: Session = Depends(get_db)):
    q = db.query(RestockAlert)
    if status:
        q = q.filter(RestockAlert.status == status)
    return q.order_by(RestockAlert.alert_date.desc()).all()


@router.put("/{alert_id}", response_model=AlertOut)
def update_alert(alert_id: int, data: AlertUpdate, db: Session = Depends(get_db)):
    alert = db.query(RestockAlert).filter(RestockAlert.id == alert_id).first()
    if not alert:
        raise ValueError("Alert not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(alert, key, value)
    db.commit()
    db.refresh(alert)
    return alert
