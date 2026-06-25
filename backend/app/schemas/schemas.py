from datetime import date
from typing import Optional

from pydantic import BaseModel


# --- Family ---
class FamilyMemberCreate(BaseModel):
    name: str
    type: str  # adult / child / dog
    age: Optional[int] = None
    weight: Optional[float] = None
    breed: Optional[str] = None
    feishu_open_id: Optional[str] = None
    responsibilities: Optional[str] = None
    notification_prefs: Optional[str] = "all"


class FamilyMemberUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    weight: Optional[float] = None
    breed: Optional[str] = None
    feishu_open_id: Optional[str] = None
    responsibilities: Optional[str] = None
    notification_prefs: Optional[str] = None


class FamilyMemberOut(BaseModel):
    id: int
    name: str
    type: str
    age: Optional[int] = None
    weight: Optional[float] = None
    breed: Optional[str] = None
    feishu_open_id: Optional[str] = None
    responsibilities: Optional[str] = None
    notification_prefs: Optional[str] = None

    model_config = {"from_attributes": True}


# --- Item Category ---
class ItemCategoryCreate(BaseModel):
    name: str
    icon: Optional[str] = None


class ItemCategoryOut(BaseModel):
    id: int
    name: str
    icon: Optional[str] = None

    model_config = {"from_attributes": True}


# --- Item ---
class ItemCreate(BaseModel):
    name: str
    category_id: Optional[int] = None
    unit: str
    typical_size: Optional[float] = None
    target_audience: str = "all"


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    unit: Optional[str] = None
    typical_size: Optional[float] = None
    target_audience: Optional[str] = None


class ItemOut(BaseModel):
    id: int
    name: str
    category_id: Optional[int] = None
    unit: str
    typical_size: Optional[float] = None
    target_audience: str

    model_config = {"from_attributes": True}


# --- Consumption ---
class ConsumptionCreate(BaseModel):
    item_id: int
    quantity: float
    unit: str
    record_date: date
    note: Optional[str] = None
    source: str = "manual"


class ConsumptionOut(BaseModel):
    id: int
    item_id: int
    quantity: float
    unit: str
    record_date: date
    note: Optional[str] = None
    source: str

    model_config = {"from_attributes": True}


# --- Purchase ---
class PurchaseCreate(BaseModel):
    item_id: int
    quantity: float
    unit: str
    purchase_date: date
    remaining: Optional[float] = None


class PurchaseOut(BaseModel):
    id: int
    item_id: int
    quantity: float
    unit: str
    purchase_date: date
    remaining: Optional[float] = None

    model_config = {"from_attributes": True}


# --- Alert ---
class AlertOut(BaseModel):
    id: int
    item_id: int
    alert_date: date
    estimated_empty_date: Optional[date] = None
    suggested_quantity: Optional[float] = None
    status: str
    message: Optional[str] = None

    model_config = {"from_attributes": True}


class AlertUpdate(BaseModel):
    status: Optional[str] = None


# --- Inventory ---
class InventoryItemOut(BaseModel):
    item_id: int
    item_name: str
    unit: str
    remaining: float
    avg_daily_rate: Optional[float] = None
    estimated_empty_date: Optional[date] = None
    days_until_empty: Optional[int] = None


# --- Chat ---
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    actions: list[dict] = []


# --- Product Comparison ---
class ProductComparisonOut(BaseModel):
    id: int
    item_id: int
    search_query: str
    platform: str
    product_name: str
    price: float
    product_url: Optional[str] = None
    deep_link: Optional[str] = None
    search_date: Optional[str] = None
    is_available: int

    model_config = {"from_attributes": True}
