"""Inventory module routers.

Merged from 6 router files:
- family.py (FamilyMember CRUD)
- items.py (Item CRUD)
- purchases.py (PurchaseRecord CRUD)
- consumption.py (ConsumptionRecord CRUD)
- inventory.py (Inventory overview)
- alerts.py (RestockAlert CRUD)
"""

from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.modules.inventory.models import (
    FamilyMember, Item, ItemCategory,
    PurchaseRecord, ConsumptionRecord, RestockAlert
)
from app.schemas.schemas import (
    FamilyMemberCreate, FamilyMemberUpdate, FamilyMemberOut,
    ItemCreate, ItemUpdate, ItemOut, ItemCategoryCreate, ItemCategoryOut,
    PurchaseCreate, PurchaseOut,
    ConsumptionCreate, ConsumptionOut,
    AlertOut, AlertUpdate,
    InventoryItemOut
)
from app.modules.inventory.services import get_inventory_overview


# Family router
family_router = APIRouter(prefix="/family", tags=["family"])

@family_router.get("/", response_model=List[FamilyMemberOut])
def list_members(db: Session = Depends(get_db)):
    return db.query(FamilyMember).all()

@family_router.post("/", response_model=FamilyMemberOut)
def create_member(data: FamilyMemberCreate, db: Session = Depends(get_db)):
    member = FamilyMember(**data.model_dump())
    db.add(member)
    db.commit()
    db.refresh(member)
    return member

@family_router.put("/{member_id}", response_model=FamilyMemberOut)
def update_member(member_id: int, data: FamilyMemberUpdate, db: Session = Depends(get_db)):
    member = db.query(FamilyMember).filter(FamilyMember.id == member_id).first()
    if not member:
        raise ValueError("Member not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(member, key, value)
    db.commit()
    db.refresh(member)
    return member

@family_router.delete("/{member_id}")
def delete_member(member_id: int, db: Session = Depends(get_db)):
    member = db.query(FamilyMember).filter(FamilyMember.id == member_id).first()
    if not member:
        raise ValueError("Member not found")
    db.delete(member)
    db.commit()
    return {"ok": True}


# Items router
items_router = APIRouter(prefix="/items", tags=["items"])

@items_router.get("/categories", response_model=List[ItemCategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(ItemCategory).all()

@items_router.post("/categories", response_model=ItemCategoryOut)
def create_category(data: ItemCategoryCreate, db: Session = Depends(get_db)):
    cat = ItemCategory(**data.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat

@items_router.get("/", response_model=List[ItemOut])
def list_items(category_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Item)
    if category_id:
        q = q.filter(Item.category_id == category_id)
    return q.all()

@items_router.get("/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise ValueError("Item not found")
    return item

@items_router.post("/", response_model=ItemOut)
def create_item(data: ItemCreate, db: Session = Depends(get_db)):
    item = Item(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@items_router.put("/{item_id}", response_model=ItemOut)
def update_item(item_id: int, data: ItemUpdate, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise ValueError("Item not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item

@items_router.delete("/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise ValueError("Item not found")
    db.delete(item)
    db.commit()
    return {"ok": True}


# Purchases router
purchases_router = APIRouter(prefix="/purchases", tags=["purchases"])

@purchases_router.get("/", response_model=List[PurchaseOut])
def list_purchases(item_id: int = None, db: Session = Depends(get_db)):
    q = db.query(PurchaseRecord)
    if item_id:
        q = q.filter(PurchaseRecord.item_id == item_id)
    return q.order_by(PurchaseRecord.purchase_date.desc()).all()

@purchases_router.post("/", response_model=PurchaseOut)
def create_purchase(data: PurchaseCreate, db: Session = Depends(get_db)):
    purchase = PurchaseRecord(**data.model_dump())
    db.add(purchase)
    db.commit()
    db.refresh(purchase)
    return purchase


# Consumption router
consumption_router = APIRouter(prefix="/consumption", tags=["consumption"])

@consumption_router.get("/", response_model=List[ConsumptionOut])
def list_consumption(item_id: int = None, db: Session = Depends(get_db)):
    q = db.query(ConsumptionRecord)
    if item_id:
        q = q.filter(ConsumptionRecord.item_id == item_id)
    return q.order_by(ConsumptionRecord.record_date.desc()).all()

@consumption_router.post("/", response_model=ConsumptionOut)
def create_consumption(data: ConsumptionCreate, db: Session = Depends(get_db)):
    record = ConsumptionRecord(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# Inventory router
inventory_router = APIRouter(prefix="/inventory", tags=["inventory"])

@inventory_router.get("/", response_model=List[InventoryItemOut])
def list_inventory(db: Session = Depends(get_db)):
    return get_inventory_overview(db)


# Alerts router
alerts_router = APIRouter(prefix="/alerts", tags=["alerts"])

@alerts_router.get("/", response_model=List[AlertOut])
def list_alerts(status: str = None, db: Session = Depends(get_db)):
    q = db.query(RestockAlert)
    if status:
        q = q.filter(RestockAlert.status == status)
    return q.order_by(RestockAlert.alert_date.desc()).all()

@alerts_router.put("/{alert_id}", response_model=AlertOut)
def update_alert(alert_id: int, data: AlertUpdate, db: Session = Depends(get_db)):
    alert = db.query(RestockAlert).filter(RestockAlert.id == alert_id).first()
    if not alert:
        raise ValueError("Alert not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(alert, key, value)
    db.commit()
    db.refresh(alert)
    return alert