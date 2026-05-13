from typing import Optional

from pydantic import BaseModel, Field


class Supplier(BaseModel):
    id: str
    name: str
    company: str
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: str
    product_categories: list[str]
    notes: Optional[str] = None
