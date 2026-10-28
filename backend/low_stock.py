"""UC-M3-01 / M3-AR-01 Low-Stock Alert (report §6.3.1, §10.5, Figures 10, 15, 20).

InventoryProcurementAgent decision over Inventory Lookup results (backend/stock.py).
Read-only and deterministic: no inventory writes, reorder quantities or model calls.
Item statuses follow the Figure 20 states; the result keeps the shared
InventoryDecisionResult shape so the API, UI and saved traces are unchanged.
Decisions are recorded in docs/uc-m3-01-low-stock-alert.md.
"""
from datetime import datetime, timezone
from enum import StrEnum

from backend.replenishment import InventoryDecisionItem, InventoryDecisionResult
from backend.stock import InventoryLookupResult, LookupStatus

ALERT_RULE = "Alert when current stock quantity ≤ reorder threshold."


class AlertStatus(StrEnum):
    LOW_STOCK = "low_stock"  # Figure 20 AlertGenerated
    NOT_REQUIRED = "not_required"  # NoAlert
    STALE = "stale"  # StaleRecord (2b): withheld, never presented as current
    EXCLUDED = "excluded"  # RecordExcluded (2a): missing, unknown or invalid evidence


class AlertOutcome(StrEnum):
    PRESENTED = "presented"  # At least one alert, every record current and valid
    PARTIAL = "partial"  # Some records stale or excluded
    NOT_REQUIRED = "not_required"  # 4a
    DATA_ERROR = "data_error"  # StatusUndetermined (3a): no current, valid record


def _invalid(item, now):
    # Defensive repeat of the lookup's checks: a decision is never made on such values.
    return (item.stock_quantity < 0 or item.reorder_threshold < 0
            or item.last_updated.tzinfo is None or item.last_updated > now)


def evaluate_low_stock(records: list[InventoryLookupResult], *, now: datetime | None = None
                       ) -> InventoryDecisionResult:
    """Alert for every current record at or below its threshold; withhold the rest."""
    now = now or datetime.now(timezone.utc)
    items = []
    for record in records:
        item = record.item
        evidence = dict(product_id=record.product_id,
                        stock_quantity=item.stock_quantity if item else None,
                        reorder_threshold=item.reorder_threshold if item else None,
                        last_updated=item.last_updated if item else None)
        if record.status == LookupStatus.STALE:
            status, explanation = AlertStatus.STALE, (
                (record.reason or "Inventory record is stale.") + " No alert is presented as current.")
        elif record.status != LookupStatus.FOUND or item is None or _invalid(item, now):
            status = AlertStatus.EXCLUDED
            explanation = record.reason if record.status != LookupStatus.FOUND and record.reason else (
                "Inventory record is incomplete or invalid; no alert decision made.")
        elif item.stock_quantity <= item.reorder_threshold:
            status, explanation = AlertStatus.LOW_STOCK, (
                f"Stock {item.stock_quantity} ≤ threshold {item.reorder_threshold}. "
                "Low-stock alert available for operator review.")
        else:
            status, explanation = AlertStatus.NOT_REQUIRED, (
                f"Stock {item.stock_quantity} > threshold {item.reorder_threshold}. No alert.")
        items.append(InventoryDecisionItem(**evidence, status=status, explanation=explanation))

    counts = {status: sum(i.status == status for i in items) for status in AlertStatus}
    limitations = []
    if counts[AlertStatus.STALE]:
        limitations.append(f"{counts[AlertStatus.STALE]} stale record(s) withheld; "
                           "their low-stock status is not presented as current.")
    if counts[AlertStatus.EXCLUDED]:
        limitations.append(f"{counts[AlertStatus.EXCLUDED]} record(s) excluded: "
                           "missing, unknown or invalid inventory evidence.")
    current = counts[AlertStatus.LOW_STOCK] + counts[AlertStatus.NOT_REQUIRED]
    if not current:
        outcome = AlertOutcome.DATA_ERROR
        limitations.append("Low-stock status cannot be determined from the available inventory evidence.")
    elif limitations:
        outcome = AlertOutcome.PARTIAL
    elif counts[AlertStatus.LOW_STOCK]:
        outcome = AlertOutcome.PRESENTED
    else:
        outcome = AlertOutcome.NOT_REQUIRED
    return InventoryDecisionResult(outcome=outcome, items=items, rule=ALERT_RULE, limitations=limitations)
