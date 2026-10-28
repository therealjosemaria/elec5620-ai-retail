"""UC-M4-02: Classify product availability from inventory lookup evidence."""

from datetime import datetime, timedelta, timezone
from enum import StrEnum

from pydantic import Field, StrictInt

from backend.models import DomainModel


class InventoryLookupStatus(StrEnum):
    FOUND = "Found"
    NOT_FOUND = "NotFound"
    ERROR = "Error"


class InventoryLookupResult(DomainModel):
    product_id: str
    stock_quantity: StrictInt | None = Field(default=None, ge=0)
    last_updated: datetime | None = None
    status: InventoryLookupStatus
    limitation: str | None = None


class AvailabilityStatus(StrEnum):
    AVAILABLE = "Available"
    UNAVAILABLE = "Unavailable"
    UNKNOWN = "Unknown"


class ProductAvailabilityResult(DomainModel):
    product_id: str
    status: AvailabilityStatus
    stock_quantity: StrictInt | None = None
    last_updated: datetime | None = None
    reason: str


def check_product_availability(
    lookup: InventoryLookupResult,
    *,
    now: datetime | None = None,
    max_age: timedelta = timedelta(hours=24),
) -> ProductAvailabilityResult:
    """Classify availability without modifying or reserving inventory."""

    current_time = now or datetime.now(timezone.utc)

    if lookup.status != InventoryLookupStatus.FOUND:
        return ProductAvailabilityResult(
            product_id=lookup.product_id,
            status=AvailabilityStatus.UNKNOWN,
            last_updated=lookup.last_updated,
            reason=lookup.limitation or (
                f"Inventory lookup status is {lookup.status.value}."
            ),
        )

    if lookup.stock_quantity is None:
        return ProductAvailabilityResult(
            product_id=lookup.product_id,
            status=AvailabilityStatus.UNKNOWN,
            last_updated=lookup.last_updated,
            reason="Inventory quantity is missing.",
        )

    if lookup.last_updated is None:
        return ProductAvailabilityResult(
            product_id=lookup.product_id,
            status=AvailabilityStatus.UNKNOWN,
            stock_quantity=lookup.stock_quantity,
            reason="Inventory timestamp is missing.",
        )

    if lookup.last_updated.tzinfo is None:
        return ProductAvailabilityResult(
            product_id=lookup.product_id,
            status=AvailabilityStatus.UNKNOWN,
            stock_quantity=lookup.stock_quantity,
            last_updated=lookup.last_updated,
            reason="Inventory timestamp has no timezone.",
        )

    record_age = current_time - lookup.last_updated

    if record_age < timedelta(0):
        return ProductAvailabilityResult(
            product_id=lookup.product_id,
            status=AvailabilityStatus.UNKNOWN,
            stock_quantity=lookup.stock_quantity,
            last_updated=lookup.last_updated,
            reason="Inventory timestamp is in the future.",
        )

    if record_age > max_age:
        return ProductAvailabilityResult(
            product_id=lookup.product_id,
            status=AvailabilityStatus.UNKNOWN,
            stock_quantity=lookup.stock_quantity,
            last_updated=lookup.last_updated,
            reason="Inventory record is stale.",
        )

    if lookup.stock_quantity == 0:
        return ProductAvailabilityResult(
            product_id=lookup.product_id,
            status=AvailabilityStatus.UNAVAILABLE,
            stock_quantity=0,
            last_updated=lookup.last_updated,
            reason="Current stock quantity is zero.",
        )

    return ProductAvailabilityResult(
        product_id=lookup.product_id,
        status=AvailabilityStatus.AVAILABLE,
        stock_quantity=lookup.stock_quantity,
        last_updated=lookup.last_updated,
        reason="Current stock quantity is greater than zero.",
    )