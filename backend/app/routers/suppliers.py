import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_current_user
from app.models.supplier import Supplier

router = APIRouter()
_DATA = Path(__file__).parent.parent / "data" / "suppliers.json"


def _load() -> list[dict]:
    with open(_DATA, encoding="utf-8") as f:
        return json.load(f)


@router.get("/", response_model=list[Supplier])
async def list_suppliers(current_user: dict = Depends(get_current_user)):
    return _load()


@router.get("/{supplier_id}", response_model=Supplier)
async def get_supplier(supplier_id: str, current_user: dict = Depends(get_current_user)):
    for s in _load():
        if s["id"] == supplier_id:
            return s
    raise HTTPException(status_code=404, detail="Tedarikçi bulunamadı")
