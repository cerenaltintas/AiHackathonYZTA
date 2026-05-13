from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class StockStatus(str, Enum):
    CRITICAL = "kritik"
    LOW = "dusuk"
    NORMAL = "normal"
    HIGH = "yuksek"


class Product(BaseModel):
    id: str
    name: str
    category: str
    quantity: int = Field(ge=0)
    unit: str
    min_threshold: int = Field(ge=0)
    price: float = Field(gt=0)
    supplier_id: str


class ProductUpdate(BaseModel):
    quantity: Optional[int] = Field(None, ge=0)
    price: Optional[float] = Field(None, gt=0)
    min_threshold: Optional[int] = Field(None, ge=0)


class ProductResponse(Product):
    stock_status: str


def get_stock_status(p: Product) -> str:
    if p.min_threshold == 0:
        return StockStatus.HIGH.value
    if p.quantity <= p.min_threshold * 0.5:
        return StockStatus.CRITICAL.value
    if p.quantity <= p.min_threshold:
        return StockStatus.LOW.value
    if p.quantity <= p.min_threshold * 3:
        return StockStatus.NORMAL.value
    return StockStatus.HIGH.value
