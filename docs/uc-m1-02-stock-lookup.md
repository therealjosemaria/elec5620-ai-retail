# UC-M1-02 — Check Current Stock

Authority: submitted Stage 1 report §6.1.2, §10.2 and Figure 4. The detailed
written requirement supplies authorization and explicit outcomes omitted from
the success-only diagram. Lio's proposal in `proposals/inventory-lookup-contract.md`
was inspected and used as the batch contract starting point.

## Behaviour and contracts

Operator selection → authenticated FastAPI endpoint → InventoryProcurementAgent
through InventoryQueryService → read-only SQLite connection → per-product result.
No LLM, availability decision, low-stock alert, reorder calculation or writes occur
inside a lookup. Cedar's single-ID consumer remains compatible.

- Batch: `lookup_stock(InventoryLookupRequest(product_ids=[...], requester=...))`.
  One result per distinct exact ID, preserving selection order. Invalid IDs are
  reported while valid IDs continue. Empty selection is rejected before lookup.
- Single ID: `lookup_stock(product_id)` returns a current InventoryItem or raises
  LookupError. Both overloads use the same trusted server authorization callback.
- `found`: complete current evidence; `stale`: complete old evidence, explicitly
  labelled; `not_found`: no record; `error`: invalid ID, incomplete/conflicting
  record or source failure. Only found/stale carry InventoryItem values.
- Freshness is an implementation policy: at most 24 hours old is current; older
  is stale. Configure `max_age` in trusted service wiring. Future and timezone-free
  timestamps are errors. Stale quantities are preserved but never claimed current.
- Product IDs use ASCII letters/digits followed by letters/digits/dot/underscore/
  hyphen, up to 128 characters. API batches are bounded to 100 entries.

Requester enums are selected by server code, not accepted from the browser. A
service instance has a fixed requester and an authorization callback. Requests
claiming a different requester are denied before opening SQLite. Internal caller
wiring must authenticate and authorize the actual caller before granting access.
The single-ID overload is retained to avoid breaking Cedar's restocking module.
Avan's availability module has a separate evidence shape. `team_workflows.py`
now provides an explicit adapter from shared lookup outcomes to that shape.

## Operator setup and API

Generate a local token, then paste it into the private ignored `.env`:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

```dotenv
OPERATOR_TOKEN=your-generated-value
```

Restart FastAPI and enter the token in the inventory workspace. It remains only
in React memory, not browser storage. Missing/wrong tokens yield HTTP 403 and no
inventory lookup. Hash navigation never grants access. This is minimal
localhost operator authentication, not a public account-management system.

`POST /api/inventory/lookup`, header `Authorization: Bearer <private-token>`, JSON:

```json
{"product_ids":["product-001","product-005","product-006"]}
```

Empty selection returns 400, malformed payloads 422. A valid batch returns a JSON
array of typed results, including explicit errors if the source is unavailable.
The browser cannot pass a role or authorization boolean. Keep the app bound to
localhost and use the existing SSH forwarding instructions for remote access.

## Persistence and prototype data

`inventory` enforces one store using a singleton primary key constrained to 1.
`inventory_items` references that store and the existing shared products table.
The lookup opens SQLite with `mode=ro`; missing files are not silently created.

Startup creates tables and seeds a prototype snapshot only when both inventory
tables are empty. Existing rows, timestamps, sales and requests are preserved.
The prototype snapshot contains known above/at/below threshold quantities, zero
stock, one stale record and one catalogue product without a record:

| Product | Quantity | Threshold | Source timestamp |
| --- | --- | --- | --- |
| product-001 | 24 | 10 | Initial seed time |
| product-002 | 10 | 10 | Initial seed time |
| product-003 | 3 | 10 | Initial seed time |
| product-004 | 0 | 8 | Initial seed time |
| product-005 | 12 | 5 | Three days before seed time |
| product-006 | Unknown | Unknown | No record |

These are labelled sample quantities, not a real store feed. Startup never
updates an existing timestamp to make stale evidence appear current. After 24
hours, more prototype rows correctly become stale. Tests use controlled clocks.

## Acceptance evidence

| Report path | Verified behaviour |
| --- | --- |
| Main 1–6 | Exact quantities, thresholds and source times; no writes or model calls |
| 1a empty selection | HTTP 400; no lookup |
| 2a invalid IDs | Per-product error, valid IDs continue, duplicates deduplicated |
| 2b unauthorized | Missing/wrong token or untrusted requester denied; no stock returned |
| 3a unavailable source | Per-product error; no fabricated quantities or new database |
| 4a incomplete record | Per-product error; remaining products still returned |
| §6.1.2 freshness | Boundary, stale, naive and future timestamp tests |
| §6.1.2 performance | 95th percentile of 20 local six-product lookups below 2 seconds |

`tests/test_stock.py` exercises these paths and verifies the SQL dump is unchanged
by lookups. `frontend/e2e/stock.spec.ts` checks denial, found/stale/not-found results,
mobile layout, and clearing the token/results on reload. All checks are fixture
verification; no university model calls are required.

## Team integration and remaining work

PR #2 integrated all published contributions on 28 October 2026: Lio's profit
margin (already main) and inventory proposal, Cedar's earlier M2 branch through
its latest unified-UI descendant, and Avan's budget/availability branch. Original
commits and authors are retained. No remote branches were deleted.

The subsequent team workflow integration connects budget/availability/profit
screens and shared-data restocking. See `team-status.md` for current coverage
and the three remaining missing implementations.
