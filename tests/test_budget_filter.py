from decimal import Decimal

import pytest

from backend.budget_filter import (
    BudgetFilterError,
    BudgetFilterStatus,
    apply_budget_filter,
)
from backend.models import CustomerRequest, Product


def product(
    product_id: str,
    name: str,
    price: str,
) -> Product:
    return Product(
        product_id=product_id,
        name=name,
        category="Wine",
        price=Decimal(price),
        abv=Decimal("13.5"),
        sweetness="Dry",
        flavour_tags=["fruit"],
    )


def test_retains_products_within_budget():
    request = CustomerRequest(budget=Decimal("30.00"))
    candidates = [
        product("WINE-001", "Shiraz", "25.00"),
        product("WINE-002", "Pinot Noir", "36.00"),
    ]

    result = apply_budget_filter(request, candidates)

    assert [item.product_id for item in result.products] == [
        "WINE-001"
    ]
    assert result.excluded_product_ids == ["WINE-002"]
    assert result.status == BudgetFilterStatus.MATCHED
    assert result.budget == Decimal("30.00")


def test_product_equal_to_budget_is_retained():
    request = CustomerRequest(budget=Decimal("30.00"))
    candidates = [
        product("WINE-001", "Shiraz", "30.00"),
    ]

    result = apply_budget_filter(request, candidates)

    assert [item.product_id for item in result.products] == [
        "WINE-001"
    ]


def test_preserves_candidate_order():
    request = CustomerRequest(budget=Decimal("30.00"))
    candidates = [
        product("WINE-003", "Wine C", "29.00"),
        product("WINE-001", "Wine A", "20.00"),
        product("WINE-002", "Wine B", "25.00"),
    ]

    result = apply_budget_filter(request, candidates)

    assert [item.product_id for item in result.products] == [
        "WINE-003",
        "WINE-001",
        "WINE-002",
    ]


def test_returns_no_match_when_every_product_exceeds_budget():
    request = CustomerRequest(budget=Decimal("10.00"))
    candidates = [
        product("WINE-001", "Shiraz", "25.00"),
        product("WINE-002", "Pinot Noir", "36.00"),
    ]

    result = apply_budget_filter(request, candidates)

    assert result.products == []
    assert result.status == BudgetFilterStatus.NO_MATCH


def test_rejects_missing_budget():
    request = CustomerRequest(budget=None)

    with pytest.raises(
        BudgetFilterError,
        match="budget is missing",
    ):
        apply_budget_filter(
            request,
            [product("WINE-001", "Shiraz", "25.00")],
        )


def test_rejects_negative_budget():
    request = CustomerRequest(budget=Decimal("-1.00"))

    with pytest.raises(
        BudgetFilterError,
        match="cannot be negative",
    ):
        apply_budget_filter(
            request,
            [product("WINE-001", "Shiraz", "25.00")],
        )


def test_rejects_invalid_catalogue_price():
    request = CustomerRequest(budget=Decimal("30.00"))

    with pytest.raises(
        BudgetFilterError,
        match="invalid catalogue price",
    ):
        apply_budget_filter(
            request,
            [product("WINE-001", "Shiraz", "-5.00")],
        )