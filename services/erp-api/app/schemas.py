from pydantic import BaseModel, Field
from typing import List
import uuid
from datetime import datetime

class OrderItemCreate(BaseModel):
    product_sku: str = Field(..., min_length=1, description="The SKU of the product")
    requested_qty: int = Field(..., gt=0, description="Quantity must be greater than 0")

class OrderCreate(BaseModel):
    order_number: str = Field(..., min_length=1)
    customer: str = Field(..., min_length=1)
    destination_dock: str = Field(..., description="e.g., Dock-3")
    items: List[OrderItemCreate]

class OrderResponse(BaseModel):
    id: uuid.UUID
    order_number: str
    correlation_id: str
    customer: str
    destination_dock: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True