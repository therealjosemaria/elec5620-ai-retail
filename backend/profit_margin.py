"""UC-M3-02 / M3-AR-02 Profit Margin Analysis (report §6.3.2, §10.6).

BusinessInsightsAgent arithmetic over authorised completed sales. No figure covers
this use case, so the written text governs; decisions are recorded in
docs/uc-m3-02-profit-margin.md. Read-only and deterministic: no model call, no
forecasting, and no pricing, procurement or inventory action.
"""
from collections.abc import Callable, Iterable, Mapping
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
import logging

from pydantic import BaseModel, Field, ValidationError

from backend.models import DomainModel, Product, SalesRecord

CALCULATION_BASIS = (
    "selling_price and cost are per-unit values; revenue = sum(quantity * selling_price); "
    "total_cost = sum(quantity * cost); profit = revenue - total_cost; "
    "profit_margin_percent = profit / revenue * 100, rounded half-up to 2 decimal places."
)


class ProfitMarginScope(DomainModel):
    """A product or a category and/or a completed date range (inclusive)."""
    product_id: str | None = None
    category: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class AnalysisOutcome(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"  # 3a: some in-scope records could not be analysed.
    INSUFFICIENT_DATA = "insufficient_data"  # 3a: no in-scope record could be analysed.
    NO_DATA = "no_data"  # 4a
    INVALID_SCOPE = "invalid_scope"  # 2a
    SOURCE_UNAVAILABLE = "source_unavailable"  # 3b


class ProfitMarginResult(DomainModel):
    outcome: AnalysisOutcome
    scope: ProfitMarginScope
    revenue: Decimal | None = None
    total_cost: Decimal | None = None
    profit: Decimal | None = None
    profit_margin_percent: Decimal | None = None
    record_count: int = 0
    analysed_records: list[SalesRecord] = Field(default_factory=list)
    excluded_missing_cost: int = 0
    excluded_invalid: int = 0
    unassigned: int = 0
    calculation_basis: str = CALCULATION_BASIS
    limitations: list[str] = Field(default_factory=list)


class _ScopeKey(BaseModel):
    product_id: str
    sale_date: date


def scope_problem(scope: ProfitMarginScope, today: date) -> str | None:
    """Structural 2a checks; they need no data access."""
    if all(value is None for value in scope.model_dump().values()):
        return "Select a product, category or completed date range."
    if scope.product_id is not None and scope.category is not None:
        return "Select either a product or a category, not both."
    if (scope.start_date is None) != (scope.end_date is None):
        return "A date range needs both a start and an end date."
    if scope.start_date is not None and scope.start_date > scope.end_date:
        return "The start date is after the end date."
    if scope.end_date is not None and scope.end_date >= today:
        return "Only completed periods can be analysed: the range must end before today."
    return None


def analyse_profit_margin(scope: ProfitMarginScope,
                          load_sales: Callable[[], Iterable[Mapping]],
                          load_catalogue: Callable[[], Iterable[Product]],
                          today: date | None = None) -> ProfitMarginResult:
    """Loaders supply authorised data source rows; this function only reads them."""
    def refused(outcome, reason):
        return ProfitMarginResult(outcome=outcome, scope=scope, limitations=[reason])

    if problem := scope_problem(scope, today or datetime.now(timezone.utc).date()):
        return refused(AnalysisOutcome.INVALID_SCOPE, problem)
    category = scope.category.casefold() if scope.category is not None else None
    try:
        # A date-only scope does not depend on the catalogue being available.
        catalogue = ({product.product_id: product for product in load_catalogue()}
                     if scope.product_id is not None or category is not None else {})
        if scope.product_id is not None and scope.product_id not in catalogue:
            return refused(AnalysisOutcome.INVALID_SCOPE, f"Unknown product: {scope.product_id}.")
        if category is not None and category not in {p.category.casefold() for p in catalogue.values()}:
            return refused(AnalysisOutcome.INVALID_SCOPE, f"Unknown category: {scope.category}.")
        rows = list(load_sales())
    except Exception as exc:
        # Class name only: never expose data-source details.
        logging.getLogger(__name__).warning("Profit margin data unavailable (%s)", type(exc).__name__)
        return refused(AnalysisOutcome.SOURCE_UNAVAILABLE,
                       "Sales or catalogue data is unavailable; no financial values were produced.")

    def in_scope(key):
        if scope.start_date is not None and not scope.start_date <= key.sale_date <= scope.end_date:
            return False
        if scope.product_id is not None:
            return key.product_id == scope.product_id
        if category is not None:
            product = catalogue.get(key.product_id)
            return None if product is None else product.category.casefold() == category
        return True

    analysed, missing_cost, invalid, unassigned = [], 0, 0, 0
    for row in rows:
        try:
            matched = in_scope(_ScopeKey.model_validate(row))
        except ValidationError:
            matched = None
        if matched is None:
            unassigned += 1
            continue
        if not matched:
            continue
        # Missing cost is excluded and counted (3a), never estimated.
        if row.get("cost") is None:
            missing_cost += 1
            continue
        try:
            record = SalesRecord.model_validate({name: row.get(name) for name in SalesRecord.model_fields})
        except ValidationError:
            invalid += 1
            continue
        if record.quantity < 1 or record.selling_price < 0 or record.cost < 0:
            invalid += 1
            continue
        analysed.append(record)

    in_scope_count = len(analysed) + missing_cost + invalid
    limitations = []
    if missing_cost:
        limitations.append(f"{missing_cost} of {in_scope_count} in-scope records excluded: cost is missing.")
    if invalid:
        limitations.append(f"{invalid} of {in_scope_count} in-scope records excluded: incomplete or invalid values.")
    if unassigned:
        limitations.append(f"{unassigned} records could not be matched to the scope "
                           "(missing product, date or catalogue entry) and were not analysed.")
    counts = dict(excluded_missing_cost=missing_cost, excluded_invalid=invalid, unassigned=unassigned)
    if not analysed:
        if in_scope_count or unassigned:
            outcome, reason = AnalysisOutcome.INSUFFICIENT_DATA, "No financial values were produced."
        else:
            outcome, reason = AnalysisOutcome.NO_DATA, "No completed sales records fall within the selected scope."
        return ProfitMarginResult(outcome=outcome, scope=scope, limitations=[*limitations, reason], **counts)
    if missing_cost or invalid:
        limitations.append(f"Figures cover {len(analysed)} of {in_scope_count} in-scope records.")

    revenue = sum((r.quantity * r.selling_price for r in analysed), Decimal(0))
    total_cost = sum((r.quantity * r.cost for r in analysed), Decimal(0))
    profit = revenue - total_cost
    margin = None
    if revenue:
        margin = (profit / revenue * 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
    else:
        limitations.append("Profit margin is undefined because revenue is zero.")
    outcome = AnalysisOutcome.PARTIAL if missing_cost or invalid or unassigned else AnalysisOutcome.COMPLETE
    return ProfitMarginResult(
        outcome=outcome, scope=scope, revenue=revenue, total_cost=total_cost, profit=profit,
        profit_margin_percent=margin, record_count=len(analysed), analysed_records=analysed,
        limitations=limitations, **counts)
