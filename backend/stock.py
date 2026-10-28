"""UC-M1-02 stock evidence: report §6.1.2, §10.2 and Figure 4.

The batch contract follows Lio's proposal. The single-ID overload preserves
Cedar's existing consumer. Access is supplied by trusted server wiring.
"""
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from pathlib import Path
import re
import sqlite3
from urllib.parse import quote

from pydantic import Field, model_validator

from backend.models import DomainModel, InventoryItem


class LookupStatus(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    STALE = "stale"
    ERROR = "error"


class Requester(StrEnum):
    CUSTOMER_AGENT = "customer_agent"
    INVENTORY_PROCUREMENT_AGENT = "inventory_procurement_agent"
    BUSINESS_INSIGHTS_AGENT = "business_insights_agent"
    FOUNDER_OPERATOR = "founder_operator"


class InventoryLookupRequest(DomainModel):
    product_ids: list[str] = Field(min_length=1, max_length=100)
    requester: Requester


class InventoryLookupResult(DomainModel):
    product_id: str
    status: LookupStatus
    item: InventoryItem | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def consistent(self):
        has_evidence = self.status in (LookupStatus.FOUND, LookupStatus.STALE)
        if has_evidence != (self.item is not None):
            raise ValueError("Only found/stale results contain inventory evidence.")
        if self.item is not None and self.item.product_id != self.product_id:
            raise ValueError("Inventory evidence must match the requested product.")
        if self.status != LookupStatus.FOUND and not self.reason:
            raise ValueError("Unresolved results require a reason.")
        return self


def ensure_inventory_data(db: sqlite3.Connection, *, now: datetime | None = None):
    """Create one store; seed a labelled prototype snapshot once, never refresh it."""
    db.executescript("""
        CREATE TABLE IF NOT EXISTS inventory (
            singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
            inventory_id TEXT NOT NULL UNIQUE, name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS inventory_items (
            product_id TEXT PRIMARY KEY REFERENCES products(product_id),
            inventory_id TEXT NOT NULL REFERENCES inventory(inventory_id),
            stock_quantity INTEGER, reorder_threshold INTEGER, last_updated TEXT
        );
    """)
    if db.execute("SELECT EXISTS(SELECT 1 FROM inventory) OR EXISTS(SELECT 1 FROM inventory_items)").fetchone()[0]:
        return
    now = now or datetime.now(timezone.utc)
    db.execute("INSERT INTO inventory VALUES (1, 'inventory-001', 'Prototype store')")
    # Six existing catalogue IDs: above/at/below threshold, zero, stale, missing.
    for pid, qty, threshold, age in [
        ("product-001", 24, 10, 0), ("product-002", 10, 10, 0),
        ("product-003", 3, 10, 0), ("product-004", 0, 8, 0),
        ("product-005", 12, 5, 72),
    ]:
        if db.execute("SELECT 1 FROM products WHERE product_id=?", (pid,)).fetchone():
            db.execute("INSERT INTO inventory_items VALUES (?, 'inventory-001', ?, ?, ?)",
                       (pid, qty, threshold, (now - timedelta(hours=age)).isoformat()))


class InventoryProcurementAgent:
    """InventoryQueryService provider. Lookup itself opens SQLite read-only."""

    def __init__(self, path: Path, *, requester: Requester,
                 authorise: Callable[[Requester], bool],
                 max_age: timedelta = timedelta(hours=24),
                 clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        if not isinstance(requester, Requester) or max_age <= timedelta(0):
            raise ValueError("Use a trusted requester and positive freshness duration.")
        self.path, self.requester, self.authorise = Path(path), requester, authorise
        self.max_age, self.clock = max_age, clock

    def lookup_stock(self, request: InventoryLookupRequest | str):
        """Single-ID compatibility raises on unresolved evidence; batch returns statuses."""
        single = isinstance(request, str)
        if single:
            request = InventoryLookupRequest(product_ids=[request], requester=self.requester)
        if not isinstance(request, InventoryLookupRequest):
            raise ValueError("Expected an inventory lookup request.")
        try:
            allowed = request.requester == self.requester and self.authorise(self.requester) is True
        except Exception:
            allowed = False
        if not allowed:
            raise PermissionError("Inventory access denied.")
        now = self.clock()
        if now.tzinfo is None:
            raise ValueError("Use a timezone-aware lookup clock.")
        ids = list(dict.fromkeys(request.product_ids))
        results = {}
        valid = []
        for pid in ids:
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", pid):
                results[pid] = InventoryLookupResult(product_id=pid, status=LookupStatus.ERROR,
                                                     reason="Invalid product identifier.")
            else:
                valid.append(pid)
        if valid:
            try:
                uri = "file:" + quote(str(self.path.resolve())) + "?mode=ro"
                db = sqlite3.connect(uri, uri=True, timeout=1)
                try:
                    db.row_factory = sqlite3.Row
                    stores = db.execute("SELECT inventory_id FROM inventory").fetchall()
                    if len(stores) != 1:
                        raise sqlite3.DatabaseError("Expected one store-level inventory.")
                    for pid in valid:
                        row = db.execute("SELECT * FROM inventory_items WHERE product_id=?", (pid,)).fetchone()
                        results[pid] = self._record(pid, row, stores[0][0], now)
                finally:
                    db.close()
            except sqlite3.Error:
                for pid in valid:
                    results[pid] = InventoryLookupResult(product_id=pid, status=LookupStatus.ERROR,
                                                         reason="Inventory source unavailable.")
        ordered = [results[pid] for pid in ids]
        if single:
            if ordered[0].status != LookupStatus.FOUND:
                raise LookupError(ordered[0].reason)
            return ordered[0].item
        return ordered

    def _record(self, pid, row, inventory_id, now):
        if row is None:
            return InventoryLookupResult(product_id=pid, status=LookupStatus.NOT_FOUND,
                                         reason="No inventory record for this product.")
        try:
            item = InventoryItem.model_validate(dict(row))
            if (item.inventory_id != inventory_id or item.stock_quantity < 0
                    or item.reorder_threshold < 0 or item.last_updated.tzinfo is None
                    or item.last_updated > now):
                raise ValueError("Incomplete or conflicting record.")
        except (ValueError, TypeError):
            return InventoryLookupResult(product_id=pid, status=LookupStatus.ERROR,
                                         reason="Inventory record is incomplete or invalid.")
        stale = now - item.last_updated > self.max_age
        return InventoryLookupResult(product_id=pid, item=item,
                                     status=LookupStatus.STALE if stale else LookupStatus.FOUND,
                                     reason="Inventory record is stale; not confirmed current." if stale else None)
