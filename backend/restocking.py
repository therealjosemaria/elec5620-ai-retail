"""Member 2 / UC-M2-02 (§6.2.2, §10.4, Figures 9, 14, 19).

BusinessInsightsAgent consumes InventoryQueryService; never reads inventory SQL.
Authorisation is supplied by trusted server wiring, not by a browser role flag.
"""
from collections.abc import Callable, Iterable
from datetime import date, datetime, timedelta, timezone
from enum import StrEnum
from fractions import Fraction
import logging

from pydantic import Field, StrictInt

from backend.interfaces import InventoryQueryService
from backend.models import DomainModel, InventoryItem, Product


class RestockingScope(DomainModel):
    product_id: str | None = None
    category: str | None = None


class CompletedSale(DomainModel):
    product_id: str
    sale_date: date
    quantity: StrictInt = Field(gt=0)


class SalesSnapshot(DomainModel):
    start_date: date
    end_date: date
    updated_at: datetime
    complete: bool
    records: list[CompletedSale]


class RestockingOutcome(StrEnum):
    PRESENTED = "presented"
    DENIED = "denied"
    INVALID_SCOPE = "invalid_scope"
    DATA_ERROR = "data_error"
    NO_PRIORITY = "no_priority"


class RestockingPriority(DomainModel):
    product_id: str
    product_name: str
    rank: int
    stock_quantity: int
    reorder_threshold: int
    last_updated: datetime
    sold_quantity: int
    explanation: str


RANKING_BASIS = (
    "Consider stock at or below its threshold. Lower stock/threshold ratio takes priority "
    "(denominator 1 when threshold is zero); then higher completed sales quantity in the same period. "
    "Equal evidence shares a rank. This prototype rule does not forecast demand or calculate order quantities."
)


class RestockingResult(DomainModel):
    outcome: RestockingOutcome
    scope: RestockingScope
    generated_at: datetime
    priorities: list[RestockingPriority] = Field(default_factory=list)
    sales_start_date: date | None = None
    sales_end_date: date | None = None
    sales_updated_at: datetime | None = None
    ranking_basis: str = RANKING_BASIS
    limitations: list[str] = Field(default_factory=list)
    data_mode: str = "connected"


def analyse_restocking(scope: RestockingScope, *,
                       authorise: Callable[[RestockingScope], bool],
                       load_catalogue: Callable[[], Iterable[Product]],
                       inventory: InventoryQueryService,
                       load_sales: Callable[[], SalesSnapshot],
                       now: datetime | None = None,
                       max_age: timedelta = timedelta(hours=24)) -> RestockingResult:
    """Fail closed on incomplete/stale evidence; injected freshness is an implementation choice.

    The success-only InventoryQueryService is retained for compatibility. Missing,
    denied or unavailable records must raise at the adapter boundary. Detailed stock
    status integration remains with the inventory owner.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or max_age <= timedelta(0):
        raise ValueError("Use an aware clock and positive freshness duration.")

    def result(outcome, limitation):
        return RestockingResult(outcome=outcome, scope=scope, generated_at=now,
                                limitations=[limitation])

    try:
        allowed = authorise(scope.model_copy(deep=True)) is True
    except Exception:
        allowed = False
    if not allowed:
        return result(RestockingOutcome.DENIED, "Not authorised; no catalogue, inventory or sales data was read.")
    if (scope.product_id is not None and scope.category is not None) or any(
            value is not None and not value.strip() for value in (scope.product_id, scope.category)):
        return result(RestockingOutcome.INVALID_SCOPE, "Choose a product or category, or leave both empty for all authorised products.")

    def fresh(timestamp):
        return timestamp.tzinfo is not None and timedelta(0) <= now - timestamp <= max_age

    try:
        catalogue = [Product.model_validate(p) for p in load_catalogue()]
        if len({p.product_id for p in catalogue}) != len(catalogue):
            raise ValueError("Duplicate catalogue IDs")
        products = [p for p in catalogue
                    if (scope.product_id is None or p.product_id == scope.product_id)
                    and (scope.category is None or p.category.casefold() == scope.category.casefold())]
        if not products and (scope.product_id is not None or scope.category is not None):
            return result(RestockingOutcome.INVALID_SCOPE, "Product or category is not in the authorised catalogue.")
        if not products:
            return result(RestockingOutcome.DATA_ERROR, "Authorised catalogue is empty; no priority can be established.")
        stocks = []
        for product in products:
            item = InventoryItem.model_validate(inventory.lookup_stock(product.product_id))
            if (item.product_id != product.product_id or item.stock_quantity < 0 or item.reorder_threshold < 0
                    or not fresh(item.last_updated)):
                raise ValueError("Invalid or stale inventory evidence")
            stocks.append(item)
        if len({s.inventory_id for s in stocks}) != 1 or not stocks[0].inventory_id.strip():
            raise ValueError("Expected one store-level inventory")
        sales = SalesSnapshot.model_validate(load_sales())
        if (not sales.complete or not fresh(sales.updated_at)
                or not sales.start_date <= sales.end_date < now.date()):
            raise ValueError("Invalid or incomplete sales snapshot")
        catalogue_ids = {p.product_id for p in catalogue}
        if any(s.product_id not in catalogue_ids or not sales.start_date <= s.sale_date <= sales.end_date
               for s in sales.records):
            raise ValueError("Sales outside the declared scope or period")
    except Exception as exc:
        logging.getLogger(__name__).warning("Restocking evidence unavailable (%s)", type(exc).__name__)
        return result(RestockingOutcome.DATA_ERROR,
                      "Required inventory or sales evidence is missing, stale, invalid or unavailable; no priorities produced.")

    quantities = {p.product_id: 0 for p in products}
    for sale in sales.records:
        if sale.product_id in quantities:
            quantities[sale.product_id] += sale.quantity
    candidates = [(Fraction(s.stock_quantity, max(s.reorder_threshold, 1)), -quantities[p.product_id], p, s)
                  for p, s in zip(products, stocks) if s.stock_quantity <= s.reorder_threshold]
    candidates.sort(key=lambda row: (row[0], row[1], row[2].product_id))
    priorities, previous, rank = [], None, 0
    for index, (ratio, negative_sales, product, stock) in enumerate(candidates, 1):
        key = (ratio, negative_sales)
        if key != previous:
            rank = index
        previous = key
        priorities.append(RestockingPriority(
            product_id=product.product_id, product_name=product.name, rank=rank,
            stock_quantity=stock.stock_quantity, reorder_threshold=stock.reorder_threshold,
            last_updated=stock.last_updated, sold_quantity=-negative_sales,
            explanation=(f"Stock {stock.stock_quantity} is at or below threshold {stock.reorder_threshold}; "
                         f"{-negative_sales} units sold from {sales.start_date} to {sales.end_date}. "
                         "Priority follows the displayed stock ratio and sales rule.")))
    return RestockingResult(
        outcome=RestockingOutcome.PRESENTED if priorities else RestockingOutcome.NO_PRIORITY,
        scope=scope, generated_at=now, priorities=priorities,
        sales_start_date=sales.start_date, sales_end_date=sales.end_date, sales_updated_at=sales.updated_at,
        limitations=[] if priorities else ["No product in scope is at or below its reorder threshold."])
