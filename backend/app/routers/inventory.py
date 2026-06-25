from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.schemas import InventoryItemOut
from app.services.inventory import get_inventory_overview

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/", response_model=List[InventoryItemOut])
def list_inventory(db: Session = Depends(get_db)):
    return get_inventory_overview(db)
