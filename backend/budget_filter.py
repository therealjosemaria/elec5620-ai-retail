"""UC-M4-01: Filter candidate products using the customer's budget."""

from decimal import Decimal

from enum import StrEnum

from backend.models import CustomerRequest, DomainModel, Product


class BudgetFilterStatus(StrEnum):
    MATCHED = "Matched"
    NO_MATCH = "NoMatch"


class BudgetFilterResult(DomainModel):
    budget: Decimal
    products: list[Product]
    excluded_product_ids: list[str]
    status: BudgetFilterStatus


class BudgetFilterError(ValueError):
    """The budget filter could not produce a reliable result."""


def apply_budget_filter(
    request: CustomerRequest,
    candidates: list[Product],
) -> BudgetFilterResult:
    """Retain candidates whose authorised price does not exceed the budget."""

    if request.budget is None:
        raise BudgetFilterError("Customer budget is missing.")

    if request.budget < 0:
        raise BudgetFilterError("Customer budget cannot be negative.")

    invalid_prices = [
        product.product_id
        for product in candidates
        if product.price < 0
    ]

    if invalid_prices:
        raise BudgetFilterError(
            "Candidate products contain an invalid catalogue price."
        )

    retained = [
        product
        for product in candidates
        if product.price <= request.budget
    ]

    excluded = [
        product.product_id
        for product in candidates
        if product.price > request.budget
    ]

    return BudgetFilterResult(
        budget=request.budget,
        products=retained,
        excluded_product_ids=excluded,
        status=(
            BudgetFilterStatus.MATCHED
            if retained
            else BudgetFilterStatus.NO_MATCH
        ),
    )