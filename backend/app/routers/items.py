from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.models.item import Item, ItemCategory
from app.schemas.schemas import ItemCreate, ItemUpdate, ItemOut, ItemCategoryCreate, ItemCategoryOut

router = APIRouter(prefix="/items", tags=["items"])


# --- Categories ---
@router.get("/categories", response_model=List[ItemCategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(ItemCategory).all()


@router.post("/categories", response_model=ItemCategoryOut)
def create_category(data: ItemCategoryCreate, db: Session = Depends(get_db)):
    cat = ItemCategory(**data.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


# --- Items ---
@router.get("/", response_model=List[ItemOut])
def list_items(category_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Item)
    if category_id:
        q = q.filter(Item.category_id == category_id)
    return q.all()


@router.get("/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise ValueError("Item not found")
    return item


@router.post("/", response_model=ItemOut)
def create_item(data: ItemCreate, db: Session = Depends(get_db)):
    item = Item(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=ItemOut)
def update_item(item_id: int, data: ItemUpdate, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise ValueError("Item not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise ValueError("Item not found")
    db.delete(item)
    db.commit()
    return {"ok": True}
