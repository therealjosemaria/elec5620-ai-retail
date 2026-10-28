# Proposal: Inventory Lookup result contract (M1-AR-02)

**Status:** proposal from Member 3 (Houyuchen) for Member 1 (Jose), who owns
M1-AR-02 / UC-M1-02. Nothing here is implemented; `backend/interfaces.py` and
`backend/models.py` are unchanged. The owner decides the final contract.

## Why now

`docs/stage1-alignment.md` ("Inventory interface") records that the current
`InventoryQueryService.lookup_stock(product_id) -> InventoryItem` transcribes only
the Figure 4 success signature. It lacks the requesting role, multiple product IDs,
and explicit found/not-found/stale/error outcomes, and must be updated before UC-M1-02.

Four core features consume this result: Low Stock Alert (M3-AR-01), Product
Availability Check (M4-AR-02), Reorder Suggestion (M5-AR-01) and Restocking
Decision Support (M2-AR-02). The Customer Agent's recommendation workflow also uses
it (§6.1.2 downstream relationships). Agreeing on the shape now lets every consumer
build and test against a fake implementation while the lookup itself is built.

## Report basis

| Source | What it requires |
| --- | --- |
| §6.1.2 Input | An authorised request with **one or more product IDs** and the **requesting role's context** |
| §6.1.2 Processing | Validate request and permission; preserve retrieved values exactly; flag missing or stale records using `last_updated` |
| §6.1.2 Output | Per product: product ID, stock quantity, reorder threshold, last-updated timestamp, and an explicit **found, not-found, stale or error** status |
| §6.1.2 Exceptions | Unauthorised request, invalid ID, unknown product, stale record or data-source failure → explicit status or error; never fabricate stock values |
| §6.1.2 Out of scope | No availability, low-stock or reorder decisions; no inventory changes |
| UC-M1-02 (§10.2) 1a | No product selected → request a valid selection; no lookup |
| UC-M1-02 2a | Invalid identifier → report it and continue with the valid identifiers |
| UC-M1-02 2b | Requester not authorised → deny; return no inventory data |
| UC-M1-02 3a | Inventory source unavailable → stock cannot be confirmed; no fabricated quantity |
| UC-M1-02 4a | Record missing quantity or timestamp → that product's result is unavailable; nothing inferred |
| Figure 4 | `lookupStock(id): InventoryItem` and `lookupStock(ids: String[0..*]): InventoryItem[0..*]`, realised by InventoryProcurementAgent and used by CustomerAgent and BusinessInsightsAgent |
| Figures 14–17 | M2, M3, M4 and M5 sequences all call `lookupStock(productIds)` on the interface |
| §6.4.2, UC-M4-02 step 3 | Availability relies on an "agreed freshness rule" |
| §11 (M1) | Inventory result within 2 seconds for at least 95% of prototype queries |

## Proposed contract

Follows `backend/models.py` conventions (`DomainModel`, `StrEnum`, `StrictInt`) and
reuses the shared `InventoryItem` as the payload, so no competing stock model is created.

```python
class LookupStatus(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    STALE = "stale"
    ERROR = "error"


class Requester(StrEnum):
    """Selected by code wiring, never taken from the browser (as in backend/handoff.py)."""
    CUSTOMER_AGENT = "customer_agent"
    INVENTORY_PROCUREMENT_AGENT = "inventory_procurement_agent"
    BUSINESS_INSIGHTS_AGENT = "business_insights_agent"
    FOUNDER_OPERATOR = "founder_operator"


class InventoryLookupRequest(DomainModel):
    product_ids: list[str]  # one or more
    requester: Requester


class InventoryLookupResult(DomainModel):
    product_id: str
    status: LookupStatus
    item: InventoryItem | None = None  # present only for FOUND and STALE
    reason: str | None = None          # required for NOT_FOUND, STALE and ERROR


class InventoryQueryService(Protocol):
    def lookup_stock(self, request: InventoryLookupRequest) -> list[InventoryLookupResult]: ...
```

### Rules

1. **Exactly four statuses** (§6.1.2), each non-found result with a human-readable `reason`:
   - `found`: a complete, current record; `item` carries the exact stored values.
   - `not_found`: a well-formed ID with no inventory record.
   - `stale`: a complete record whose `last_updated` is older than the freshness
     limit. **Values are still returned**, so consumers can follow their own rule:
     M3 reports an alert as stale-based (UC-M3-01 2b) and M4 classifies it unknown
     (UC-M4-02 3a).
   - `error`: an invalid ID, e.g. empty or blank (UC-M1-02 2a); a record missing
     quantity or timestamp (4a); or the inventory source failing (3a). `item` is absent.
2. **Freshness rule, defined once in the lookup:** a record is stale when
   `lookup_time - last_updated > 24 hours`. Exactly 24 hours is still current.
   The limit is configurable (e.g. `INVENTORY_STALE_AFTER_HOURS`, default 24).
   Timestamps are timezone-aware UTC. Consumers read `status` and never recompute
   freshness, so M1, M3, M4 and M5 cannot disagree.
3. **Whole-request rejections, with no per-product results:**
   - No product IDs → `ValueError` (1a).
   - Requester not allowed → `PermissionError`, no inventory data (2b), as in
     `read_published_request` in `backend/handoff.py`.
4. **Data-source failure** → every requested product returns `error` with
   reason "Inventory source unavailable" (3a). This matches the §6.1.2 output of an
   explicit status for each product.
5. **One result per distinct requested ID**, in request order. Invalid IDs do not
   stop valid IDs from being looked up (2a).
6. **Read-only:** no writes, no availability/low-stock/reorder decisions, no rounding
   or repair of stored values (§6.1.2 out of scope, accuracy NFR).

### How each consumer uses the result

| Status | M3 Low Stock Alert (UC-M3-01) | M4 Availability (UC-M4-02) | M5 Reorder (UC-M5-01) | M2 Restocking (UC-M2-02) |
| --- | --- | --- | --- | --- |
| `found` | Alert if `stock_quantity <= reorder_threshold`, else no alert | `> 0` available, `= 0` unavailable | Suggest a quantity if at or below threshold | Use as ranking evidence |
| `stale` | Report as stale-based or withhold; never presented as current (2b) | Unknown, with limitation (3a) | Partial result; no unsupported quantity (3a) | Partial result, limitation stated (3a) |
| `not_found` | Excluded; incomplete result for that product (2a) | Unknown, with limitation (3a) | Partial result (3a) | Limitation stated (3a) |
| `error` | Excluded (2a); if every product fails, status undetermined (3a) | Unknown, or explicit error if the source is down (3b) | Partial or error result (3a) | Partial or error result (3a) |
| `PermissionError` | No alert | Denied (2a) | Denied (2a) | Denied (2a) |

## Prototype inventory data (suggestion)

- One store-level inventory, e.g. `inventory-001` as in Figure 5.
- `last_updated` generated relative to startup time, otherwise every record is
  stale during a demo.
- Cover every consumer path:
  - one item above its threshold, one exactly at it, one below it;
  - one at zero stock;
  - one stale (e.g. 3 days old);
  - one catalogue product with no inventory record.
- Product IDs follow the shared catalogue proposed on branch
  `feat/houyuchen-profit-margin` (`product-001` to `product-006`).

## Open questions for the owner

1. **Least privilege (§1.4):** should Customer Agent results omit `reorder_threshold`,
   which only operational features need?
2. **Source failure:** per-product `error` results (proposed), or a dedicated exception
   so consumers can tell a total outage from individual record problems?
3. **Future timestamps** (clock skew or bad data): suggest `error` as a conflicting
   record (cf. UC-M4-02 step 4).
4. **Ownership:** who builds the inventory tables and seed data, and when? Low Stock
   Alert, Availability Check and Reorder Suggestion are blocked until the lookup exists.

## After agreement

The owner updates `backend/interfaces.py` (and `backend/models.py` if the result types
live there) and implements the lookup. Consumers can start immediately against a fake
`InventoryQueryService` that returns these result types.
