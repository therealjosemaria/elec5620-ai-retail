"""Adapters joining teammate modules; decisions remain in their owned modules."""
from datetime import date, datetime, timedelta, timezone
import re

from backend.availability import (InventoryLookupResult as AvailabilityEvidence,
    InventoryLookupStatus, check_product_availability)
from backend.budget_filter import BudgetFilterError
from backend.restocking import CompletedSale, SalesSnapshot
from backend.retail_data import load_sales
from backend.stock import LookupStatus


def validate_aud_budget(text: str):
    """28 Oct team decision: catalogue and unqualified dollars are AUD; no FX."""
    unsupported = (r"\b(?:USD|EUR|GBP|CAD|NZD|JPY|CNY|RMB|CHF|HKD|SGD|INR|KRW|"
                   r"BRL|ZAR|AED|THB|IDR|MYR|PHP|VND|MXN|SEK|NOK|DKK|PLN|TRY|"
                   r"euros?|pounds?|yen|yuan|rupees?|pesos?)\b|[€£¥₹₩₽]|"
                   r"\b(?:US|Canadian|New Zealand|Singapore|Hong Kong)\s*(?:\$|dollars?)")
    if re.search(unsupported, text, flags=re.IGNORECASE):
        raise BudgetFilterError("Only AUD budgets are supported; no currency conversion is performed.")


def classify_lookup(result, *, now=None):
    """Map the shared lookup contract to Avan's existing availability contract."""
    item = result.item
    status = {
        LookupStatus.FOUND: InventoryLookupStatus.FOUND,
        LookupStatus.NOT_FOUND: InventoryLookupStatus.NOT_FOUND,
    }.get(result.status, InventoryLookupStatus.ERROR)
    evidence = AvailabilityEvidence(product_id=result.product_id, status=status,
        stock_quantity=item.stock_quantity if item else None,
        last_updated=item.last_updated if item else None, limitation=result.reason)
    return check_product_availability(evidence, now=now)


def completed_sales(db, *, today: date):
    """Exclude known unfinished periods; preserve malformed rows for module checks."""
    rows = []
    for row in load_sales(db):
        try:
            if date.fromisoformat(row["sale_date"]) >= today:
                continue
        except (ValueError, TypeError):
            pass
        rows.append(row)
    return rows


def sqlite_sales_snapshot(db, *, now: datetime):
    records = [CompletedSale(product_id=r["product_id"], sale_date=r["sale_date"], quantity=r["quantity"])
               for r in completed_sales(db, today=now.date())]
    end = now.date() - timedelta(days=1)
    return SalesSnapshot(start_date=min((r.sale_date for r in records), default=end),
                         end_date=end, updated_at=now, complete=True, records=records)
