from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.models.consumption import ConsumptionRecord
from app.schemas.schemas import ConsumptionCreate, ConsumptionOut

router = APIRouter(prefix="/consumption", tags=["consumption"])


@router.get("/", response_model=List[ConsumptionOut])
def list_consumption(item_id: int = None, db: Session = Depends(get_db)):
    q = db.query(ConsumptionRecord)
    if item_id:
        q = q.filter(ConsumptionRecord.item_id == item_id)
    return q.order_by(ConsumptionRecord.record_date.desc()).all()


@router.post("/", response_model=ConsumptionOut)
def create_consumption(data: ConsumptionCreate, db: Session = Depends(get_db)):
    record = ConsumptionRecord(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
