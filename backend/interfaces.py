"""Successful stock-query signature from Stage 1 Figure 4.

No inventory access is implemented here. InventoryProcurementAgent will realize
this protocol. CustomerAgent/BusinessInsightsAgent consume it, not inventory SQL.
The not-found/stale/error result contract still needs reconciliation with §6.1.2;
do not treat this successful-return signature as a complete stock feature.
"""
from typing import Protocol

from backend.models import InventoryItem


class InventoryQueryService(Protocol):
    def lookup_stock(self, product_id: str) -> InventoryItem: ...
