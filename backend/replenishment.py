"""Read-only Inventory Agent decisions: §10.5/10.9, Figures 15 and 17.

28 Oct owner decision: target stock = 2 * threshold; order the shortfall only.
"""
from datetime import datetime, timezone
from pydantic import Field
from backend.models import DomainModel
from backend.stock import InventoryLookupResult, LookupStatus

REORDER_RULE = "target = 2 × reorder threshold; suggested quantity = max(0, target − current stock)"


class InventoryDecisionItem(DomainModel):
    product_id: str
    status: str
    stock_quantity: int | None = None
    reorder_threshold: int | None = None
    last_updated: datetime | None = None
    suggested_quantity: int | None = None
    explanation: str


class InventoryDecisionResult(DomainModel):
    outcome: str
    items: list[InventoryDecisionItem] = Field(default_factory=list)
    rule: str
    limitations: list[str] = Field(default_factory=list)


def evaluate_inventory(records: list[InventoryLookupResult], *, reorder=False, rule_available=True, now=None):
    """Consume lookup statuses; stale/invalid evidence never produces a quantity."""
    rule = REORDER_RULE if reorder else "Alert when current stock quantity ≤ reorder threshold."
    items, valid, actionable = [], 0, 0
    now = now or datetime.now(timezone.utc)
    for record in records:
        item = record.item
        evidence = dict(product_id=record.product_id, stock_quantity=item.stock_quantity if item else None,
            reorder_threshold=item.reorder_threshold if item else None, last_updated=item.last_updated if item else None)
        invalid = item is not None and (item.stock_quantity < 0 or item.reorder_threshold < 0 or
            item.last_updated.tzinfo is None or item.last_updated > now)
        if record.status != LookupStatus.FOUND or invalid:
            items.append(InventoryDecisionItem(**evidence, status="unknown",
                explanation=record.reason or "Current inventory evidence is unavailable or invalid; no decision made."))
            continue
        valid += 1
        low = item.stock_quantity <= item.reorder_threshold
        if not low:
            items.append(InventoryDecisionItem(**evidence, status="not_required", explanation="Current stock exceeds its reorder threshold."))
        elif reorder and not rule_available:
            items.append(InventoryDecisionItem(**evidence, status="rule_unavailable", explanation="Confirm a valid reorder rule before calculating a quantity."))
        else:
            actionable += 1
            quantity = max(0, 2 * item.reorder_threshold - item.stock_quantity) if reorder else None
            items.append(InventoryDecisionItem(**evidence, status="suggested" if reorder else "low_stock",
                suggested_quantity=quantity,
                explanation=(f"Stock {item.stock_quantity} ≤ threshold {item.reorder_threshold}. "
                    + (f"Target {2 * item.reorder_threshold}; shortfall {quantity}." if reorder else "Low-stock alert available for operator review."))))
    limitations = []
    if any(i.status == "unknown" for i in items):
        limitations.append("Missing, stale or invalid records were withheld from current decisions.")
    if any(i.status == "rule_unavailable" for i in items):
        limitations.append("Reorder rule unavailable; unsupported quantities were not calculated.")
    if not valid:
        outcome = "data_error"
    elif limitations:
        outcome = "partial"
    elif actionable:
        outcome = "presented"
    else:
        outcome = "not_required"
    return InventoryDecisionResult(outcome=outcome, items=items, rule=rule, limitations=limitations)
