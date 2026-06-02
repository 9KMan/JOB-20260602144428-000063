"""
GTN Order models - Pydantic models for order data.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class OrderLineItem(BaseModel):
    """Individual line item in an order."""
    item_id: str
    sku: str
    quantity: int
    unit_price: float
    total_price: float
    discount: float = 0.0


class Order(BaseModel):
    """GTN Order model."""
    order_id: str
    order_number: str
    customer_id: str
    order_date: datetime
    status: str
    total_amount: float
    currency: str = "USD"
    shipping_address: Optional[Dict[str, Any]] = None
    billing_address: Optional[Dict[str, Any]] = None
    line_items: List[OrderLineItem] = Field(default_factory=list)
    payment_method: Optional[str] = None
    payment_status: str = "PENDING"
    shipping_method: Optional[str] = None
    tracking_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class OrderSearchRequest(BaseModel):
    """Request model for order search API."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    customer_id: Optional[str] = None
    status: Optional[str] = None
    page: int = 1
    page_size: int = 100


class OrderSearchResponse(BaseModel):
    """Response model for order search API."""
    orders: List[Order]
    total_count: int
    page: int
    page_size: int
    has_more: bool


class WebSocketEvent(BaseModel):
    """GTN WebSocket event model."""
    event_id: str
    event_type: str
    timestamp: datetime
    payload: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SpooledEvent(BaseModel):
    """Spooled event for processing queue."""
    spool_id: str
    event: WebSocketEvent
    received_at: datetime = Field(default_factory=datetime.now)
    processed: bool = False
    processed_at: Optional[datetime] = None
    retry_count: int = 0
    error_message: Optional[str] = None