"""Shared Stage 1 domain contracts (report §4, Figure 4, Figure 18).

Python uses snake_case for UML camelCase attributes. Decimal values serialize
as JSON strings to avoid losing precision. These are schemas, not feature implementations.
"""
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class RequestStatus(StrEnum):
    RECEIVED = "RequestReceived"
    CAPTURING = "CapturingNeeds"
    VALIDATING = "ValidatingRequest"
    UNUSABLE = "RequestUnusable"
    VALIDATION_FAILED = "ValidationFailed"
    AVAILABLE = "RequestAvailable"
    DOWNSTREAM_UNAVAILABLE = "DownstreamUnavailable"
    CONFIRMED = "RequestConfirmed"


class CustomerRequest(DomainModel):
    budget: Decimal | None = None
    occasion: str | None = None
    party_size: StrictInt | None = None
    taste_preferences: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    status: RequestStatus = RequestStatus.AVAILABLE


class Product(DomainModel):
    product_id: str
    name: str
    category: str
    price: Decimal
    abv: Decimal
    sweetness: str
    flavour_tags: list[str] = Field(default_factory=list)


class Inventory(DomainModel):
    inventory_id: str
    name: str


class InventoryItem(DomainModel):
    inventory_id: str
    product_id: str
    stock_quantity: StrictInt
    reorder_threshold: StrictInt
    last_updated: datetime


class SalesRecord(DomainModel):
    product_id: str
    sale_date: date
    quantity: StrictInt
    selling_price: Decimal
    cost: Decimal
