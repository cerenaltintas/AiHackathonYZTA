import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import get_current_user
from app.models.inventory import Product, ProductResponse, ProductUpdate, get_stock_status

router = APIRouter()
_DATA = Path(__file__).parent.parent / "data" / "products.json"


def _load() -> list[dict]:
    with open(_DATA, encoding="utf-8") as f:
        return json.load(f)


def _save(products: list[dict]) -> None:
    with open(_DATA, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)


def _to_response(p: dict) -> ProductResponse:
    product = Product(**p)
    return ProductResponse(**p, stock_status=get_stock_status(product))


# Statik rotalar önce tanımlanmalı (/{product_id} ile çakışmaması için)
@router.get("/summary/stats", tags=["Envanter"])
async def inventory_stats(current_user: dict = Depends(get_current_user)):
    products = [_to_response(p) for p in _load()]
    return {
        "total_products": len(products),
        "kritik": sum(1 for p in products if p.stock_status == "kritik"),
        "dusuk": sum(1 for p in products if p.stock_status == "dusuk"),
        "normal": sum(1 for p in products if p.stock_status == "normal"),
        "yuksek": sum(1 for p in products if p.stock_status == "yuksek"),
        "total_value": round(sum(p.quantity * p.price for p in products), 2),
    }


@router.get("/critical", response_model=list[ProductResponse])
async def critical_stock(current_user: dict = Depends(get_current_user)):
    products = [_to_response(p) for p in _load()]
    return [p for p in products if p.stock_status in ("kritik", "dusuk")]


@router.get("/", response_model=list[ProductResponse])
async def list_products(
    category: Optional[str] = Query(None, max_length=100),
    status_filter: Optional[str] = Query(None, max_length=20),
    current_user: dict = Depends(get_current_user),
):
    products = [_to_response(p) for p in _load()]
    if category:
        products = [p for p in products if p.category == category]
    if status_filter:
        products = [p for p in products if p.stock_status == status_filter]
    return products


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str, current_user: dict = Depends(get_current_user)):
    for p in _load():
        if p["id"] == product_id:
            return _to_response(p)
    raise HTTPException(status_code=404, detail="Ürün bulunamadı")


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    update: ProductUpdate,
    current_user: dict = Depends(get_current_user),
):
    products = _load()
    for i, p in enumerate(products):
        if p["id"] == product_id:
            if update.quantity is not None:
                products[i]["quantity"] = update.quantity
            if update.price is not None:
                products[i]["price"] = update.price
            if update.min_threshold is not None:
                products[i]["min_threshold"] = update.min_threshold
            _save(products)
            return _to_response(products[i])
    raise HTTPException(status_code=404, detail="Ürün bulunamadı")
