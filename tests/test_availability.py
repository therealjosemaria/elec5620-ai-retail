from datetime import datetime, timezone

from backend.availability import (
    AvailabilityStatus,
    InventoryLookupResult,
    InventoryLookupStatus,
    check_product_availability,
)


NOW = datetime(2026, 10, 28, 10, 0, tzinfo=timezone.utc)


def test_positive_current_stock_is_available():
    lookup = InventoryLookupResult(
        product_id="WINE-001",
        stock_quantity=6,
        last_updated=NOW,
        status=InventoryLookupStatus.FOUND,
    )

    result = check_product_availability(lookup)

    assert result.status == AvailabilityStatus.AVAILABLE
    assert result.stock_quantity == 6


def test_zero_current_stock_is_unavailable():
    lookup = InventoryLookupResult(
        product_id="WINE-001",
        stock_quantity=0,
        last_updated=NOW,
        status=InventoryLookupStatus.FOUND,
    )

    result = check_product_availability(lookup)

    assert result.status == AvailabilityStatus.UNAVAILABLE
    assert result.stock_quantity == 0


def test_not_found_inventory_is_unknown():
    lookup = InventoryLookupResult(
        product_id="WINE-404",
        status=InventoryLookupStatus.NOT_FOUND,
        limitation="Product was not found.",
    )

    result = check_product_availability(lookup)

    assert result.status == AvailabilityStatus.UNKNOWN
    assert result.reason == "Product was not found."


def test_stale_inventory_is_unknown():
    lookup = InventoryLookupResult(
        product_id="WINE-001",
        stock_quantity=5,
        last_updated=NOW,
        status=InventoryLookupStatus.STALE,
        limitation="Inventory record is stale.",
    )

    result = check_product_availability(lookup)

    assert result.status == AvailabilityStatus.UNKNOWN
    assert result.stock_quantity == 5
    assert result.reason == "Inventory record is stale."


def test_missing_quantity_is_unknown():
    lookup = InventoryLookupResult(
        product_id="WINE-001",
        stock_quantity=None,
        last_updated=NOW,
        status=InventoryLookupStatus.FOUND,
    )

    result = check_product_availability(lookup)

    assert result.status == AvailabilityStatus.UNKNOWN
    assert result.reason == "Inventory quantity is missing."


def test_missing_timestamp_is_unknown():
    lookup = InventoryLookupResult(
        product_id="WINE-001",
        stock_quantity=5,
        last_updated=None,
        status=InventoryLookupStatus.FOUND,
    )

    result = check_product_availability(lookup)

    assert result.status == AvailabilityStatus.UNKNOWN
    assert result.reason == "Inventory timestamp is missing."


def test_inventory_error_is_unknown():
    lookup = InventoryLookupResult(
        product_id="WINE-001",
        status=InventoryLookupStatus.ERROR,
        limitation="Inventory service is unavailable.",
    )

    result = check_product_availability(lookup)

    assert result.status == AvailabilityStatus.UNKNOWN
    assert result.reason == "Inventory service is unavailable."