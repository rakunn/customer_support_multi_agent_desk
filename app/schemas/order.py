from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

OrderStatus = Literal["processing", "shipped", "delivered", "cancelled"]


class OrderItem(BaseModel):
    sku: str
    name: str
    quantity: int = Field(ge=1)
    price: float = Field(ge=0)


class Order(BaseModel):
    id: str
    customer_id: str
    status: OrderStatus
    amount: float = Field(ge=0)
    items: list[OrderItem]
    shipping_status: str
    delivered_at: datetime | None = None
    is_final_sale: bool = False


class CreateOrderRequest(BaseModel):
    id: str
    customer_email: str
    status: OrderStatus
    amount: float = Field(ge=0)
    item_name: str
    shipping_status: str
    delivered_at: datetime | None = None
    is_final_sale: bool = False


class OrderAdminRecord(BaseModel):
    order: Order
    is_seed: bool

