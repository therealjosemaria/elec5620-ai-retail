"""Avan's HTTP adapters integrated with trusted saved requests/stock services."""

from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import Field

from backend.availability import ProductAvailabilityResult
from backend.budget_filter import BudgetFilterResult
from backend.models import DomainModel


class BudgetFilterSubmission(DomainModel):
    request_id: UUID


class AvailabilityCheckSubmission(DomainModel):
    product_ids: list[str] = Field(min_length=1, max_length=100)


def build_router(*, filter_request, check_inventory, require_operator):
    # The browser cannot supply authoritative prices, stock, or a trusted role.
    router = APIRouter(prefix="/api/member4", tags=["Member 4 product decisions"])

    @router.post("/budget-filter", response_model=BudgetFilterResult)
    def budget_filter(submission: BudgetFilterSubmission):
        return filter_request(submission.request_id)

    @router.post("/availability-check", response_model=list[ProductAvailabilityResult])
    def availability_check(submission: AvailabilityCheckSubmission, request: Request):
        require_operator(request)
        return check_inventory(submission.product_ids)

    return router
