from typing import List, Optional
from pydantic import BaseModel


class OrderItem(BaseModel):
    product_id: str
    name: str
    quantity: int


class Order(BaseModel):
    order_id: str
    customer_name: str
    items: List[OrderItem]
    status: str
    delivery_address: str
    order_date: str
