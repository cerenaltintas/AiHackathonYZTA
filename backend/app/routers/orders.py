import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import get_current_user
from app.models.order import Order

router = APIRouter()
_DATA = Path(__file__).parent.parent / "data" / "orders.json"


def _load() -> list[dict]:
    with open(_DATA, encoding="utf-8") as f:
        return json.load(f)


@router.get("/", response_model=list[Order])
async def list_orders(
    status: Optional[str] = Query(None, max_length=50),
    current_user: dict = Depends(get_current_user),
):
    orders = _load()
    if status:
        orders = [o for o in orders if o["status"] == status]
    return orders


@router.get("/{order_id}", response_model=Order)
async def get_order(order_id: str, current_user: dict = Depends(get_current_user)):
    for o in _load():
        if o["order_id"] == order_id:
            return o
    raise HTTPException(status_code=404, detail="Sipariş bulunamadı")
