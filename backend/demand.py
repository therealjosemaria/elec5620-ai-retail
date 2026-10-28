"""UC-M5-02: completed sales quantities, not forecasts (§6.5.2/10.10).

Owner agreed 28 Oct: compare the adjacent preceding equal-length period;
increasing/decreasing/stable means positive/negative/zero units difference.
"""
from datetime import date, timedelta
from decimal import Decimal
from pydantic import Field, StrictInt
from backend.models import DomainModel

TREND_RULE = "Compare total units with the immediately preceding equal-length period: positive change = increasing, negative = decreasing, zero = stable."


class DemandScope(DomainModel):
    product_id: str | None = None
    category: str | None = None
    start_date: date
    end_date: date


class QuantitySale(DomainModel):
    product_id: str = Field(min_length=1)
    sale_date: date
    quantity: StrictInt = Field(ge=0)


class DemandResult(DomainModel):
    outcome: str
    scope: DemandScope
    comparison_start: date | None = None
    comparison_end: date | None = None
    units_sold: int | None = None
    comparison_units: int | None = None
    change: int | None = None
    percent_change: Decimal | None = None
    trend: str | None = None
    rule: str = TREND_RULE
    records: list[QuantitySale] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


def analyse_demand(scope, *, load_sales, load_catalogue, today, rule_available=True):
    result = DemandResult(scope=scope, outcome="invalid_scope")
    if (bool(scope.product_id) == bool(scope.category) or
        any(v is not None and not v.strip() for v in (scope.product_id, scope.category)) or
        scope.start_date > scope.end_date or scope.end_date >= today):
        result.limitations = ["Select one product or category and a completed historical period ending before today."]
        return result
    try:
        span = (scope.end_date - scope.start_date).days + 1
        result.comparison_end = scope.start_date - timedelta(days=1)
        result.comparison_start = scope.start_date - timedelta(days=span)
    except OverflowError:
        result.outcome = "no_comparison"
        result.limitations = ["No valid preceding equal-length comparison period exists."]
        return result
    try:
        catalogue = list(load_catalogue())
        if len({p.product_id for p in catalogue}) != len(catalogue):
            raise ValueError("Conflicting catalogue IDs.")
        ids = {p.product_id for p in catalogue if p.product_id == scope.product_id or
            (scope.category is not None and p.category.casefold() == scope.category.casefold())}
        if not ids:
            result.limitations = ["The selected product/category is not in the authorised catalogue."]
            return result
        rows = list(load_sales())
    except Exception:
        result.outcome = "source_unavailable"
        result.limitations = ["Authorised sales or catalogue source unavailable; no trend inferred."]
        return result
    invalid = 0
    for row in rows:
        # Unassignable rows make completeness uncertain; never infer missing dates/IDs.
        try:
            pid, day = row['product_id'], date.fromisoformat(str(row['sale_date']))
            if not isinstance(pid, str) or not pid.strip():
                raise ValueError("Unassignable sales product.")
        except (KeyError, TypeError, ValueError):
            invalid += 1
            continue
        if pid not in ids or not result.comparison_start <= day <= scope.end_date:
            continue
        try:
            result.records.append(QuantitySale(product_id=pid, sale_date=day, quantity=row.get('quantity')))
        except (ValueError, TypeError):
            invalid += 1
    current = [r for r in result.records if scope.start_date <= r.sale_date <= scope.end_date]
    previous = [r for r in result.records if result.comparison_start <= r.sale_date <= result.comparison_end]
    result.units_sold = sum(r.quantity for r in current) if current else None
    result.comparison_units = sum(r.quantity for r in previous) if previous else None
    if invalid:
        result.outcome = "partial"
        result.limitations = [f"{invalid} incomplete/unassignable sales records; totals describe valid records only. No reliable trend classification."]
        return result
    if not current or not previous:
        result.outcome = "no_comparison" if current else "insufficient_data"
        result.limitations = ["No sales rows exist for one or both periods; absent evidence is not assumed to mean zero sales."]
        return result
    result.change = result.units_sold - result.comparison_units
    if result.comparison_units:
        result.percent_change = (Decimal(result.change) / result.comparison_units * 100).quantize(Decimal("0.01"))
    else:
        result.limitations.append("Percentage change is undefined for a zero baseline; absolute units determine the trend.")
    if not rule_available:
        result.outcome = "rule_unavailable"
        result.limitations = ["Descriptive quantities only; confirm a valid trend rule before classification."]
        return result
    result.trend = "increasing" if result.change > 0 else "decreasing" if result.change < 0 else "stable"
    result.outcome = "complete"
    return result
