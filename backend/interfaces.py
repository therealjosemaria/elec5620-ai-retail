"""InventoryQueryService: Figure 4 success overload plus §6.1.2 batch outcomes.

InventoryProcurementAgent realizes this protocol. Callers use a trusted,
server-bound requester; a single-ID call raises on any non-current result.
"""
from typing import Protocol, overload

from backend.models import InventoryItem
from backend.stock import InventoryLookupRequest, InventoryLookupResult


class InventoryQueryService(Protocol):
    @overload
    def lookup_stock(self, request: InventoryLookupRequest) -> list[InventoryLookupResult]: ...

    @overload
    def lookup_stock(self, product_id: str) -> InventoryItem: ...
