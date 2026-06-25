from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.purchase import PurchaseRecord
from app.schemas.schemas import PurchaseCreate, PurchaseOut

router = APIRouter(prefix="/purchases", tags=["purchases"])


@router.get("/", response_model=List[PurchaseOut])
def list_purchases(item_id: int = None, db: Session = Depends(get_db)):
    q = db.query(PurchaseRecord)
    if item_id:
        q = q.filter(PurchaseRecord.item_id == item_id)
    return q.order_by(PurchaseRecord.purchase_date.desc()).all()


@router.post("/", response_model=PurchaseOut)
def create_purchase(data: PurchaseCreate, db: Session = Depends(get_db)):
    purchase = PurchaseRecord(**data.model_dump())
    db.add(purchase)
    db.commit()
    db.refresh(purchase)
    return purchase
