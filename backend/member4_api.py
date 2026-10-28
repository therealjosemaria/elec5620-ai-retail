"""API routes for UC-M4-01 and UC-M4-02."""

from enum import StrEnum

from fastapi import APIRouter, HTTPException

from backend.availability import (
    InventoryLookupResult,
    ProductAvailabilityResult,
    check_product_availability,
)
from backend.budget_filter import (
    BudgetFilterError,
    BudgetFilterResult,
    apply_budget_filter,
)
from backend.models import CustomerRequest, DomainModel, Product


router = APIRouter(
    prefix="/api/member4",
    tags=["Member 4 product decisions"],
)


class RequesterRole(StrEnum):
    CUSTOMER_AGENT = "CustomerAgent"
    FOUNDER_OPERATOR = "FounderOperator"


class BudgetFilterSubmission(DomainModel):
    request: CustomerRequest
    candidates: list[Product]


class AvailabilityCheckSubmission(DomainModel):
    requester_role: RequesterRole
    lookups: list[InventoryLookupResult]


@router.post(
    "/budget-filter",
    response_model=BudgetFilterResult,
)
def budget_filter(
    submission: BudgetFilterSubmission,
) -> BudgetFilterResult:
    try:
        return apply_budget_filter(
            submission.request,
            submission.candidates,
        )
    except BudgetFilterError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error


@router.post(
    "/availability-check",
    response_model=list[ProductAvailabilityResult],
)
def availability_check(
    submission: AvailabilityCheckSubmission,
) -> list[ProductAvailabilityResult]:
    return [
        check_product_availability(lookup)
        for lookup in submission.lookups
    ]