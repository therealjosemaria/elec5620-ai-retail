# Member 2 implementation and demonstration

## Source and ownership

On 27 October 2026 the user confirmed that the local
`AIMultiAgentAlcoholRetail_Project-1.pdf` is the submitted Stage 1 report under a
different filename. Read §4, §6.2.1–6.2.2, §10.3–10.4, §11, and inspected Figures
4, 7, 9, 14 and 19. This is not an adoption of a Critical Fixes revision.
The local PDF page numbers differ from the earlier alignment note; use section
and figure identifiers for traceability.

Member 2 owns two features across two shared agents:

| Feature | Agent | Implemented here |
| --- | --- | --- |
| UC-M2-01 / M2-AR-01 Drink Recommendation | CustomerAgent | Deterministic catalogue matching, explanation, saved-request API and UI |
| UC-M2-02 / M2-AR-02 Restocking Decision Support | BusinessInsightsAgent | Authorised evidence analysis, ranking, errors, integration API and isolated fixture demonstration |

This is a prototype implementation, not completion of unrestricted natural-language
AI recommendation or the team's authentication/inventory services. No new live
model adapter or live model calls are introduced.

## UC-M2-01

`GET /api/requests/{request_id}/recommendations` reads the existing durable inbox
using `RequestConsumer.RECOMMENDATION`, then reads shared catalogue products.
Unknown requests return 404; requests without a published handoff return 409.
The endpoint does not change request status, re-extract needs, write catalogue
data, or invoke the model (even if extraction is in live mode).

The prototype recognises exact phrases listed in `backend/recommendations.py`:
wine, red wine, white wine, beer, spirits, dry, dry wine, sweet, sweet wine,
red, white, plum, oak, cherry, light, citrus, sparkling, fruity, hoppy,
no sweet drinks, not sweet, dry drinks. Case and terminal punctuation are normalised.
All supported stated preferences/constraints must match catalogue facts.
Unsupported phrases return `unsupported_request`; negation is never silently
discarded. A general natural-language interpretation/ranking adapter remains
future work and needs its own validation and shared quota accounting before use.

Implementation choices, not additional report requirements:

- Supported needs act as conjunctive catalogue predicates. All matching products
  share rank 1 because this matcher has no evidence to prefer one exact match;
  product ID gives stable display order, not a hidden priority.
- `no sweet drinks` maps conservatively to catalogue sweetness `dry`.
- Occasion and party size remain available in CustomerRequest, but this catalogue
  provides no corresponding suitability fields. Their non-use is disclosed;
  occasion-only/party-size-only requests cannot be recommended by this matcher.
- Product facts and prices are copied from the authorised catalogue, never generated.
  Each result links its explanation to the exact structured need (§11).
- Budget filtering belongs to Member 4. The sample therefore returns both the
  25.00 Shiraz and 32.00 Pinot Noir despite the captured budget of 30.
- No inventory, availability, quantity planning, purchase or supplier action occurs.

Outcomes cover §10.3: `complete`, `unusable_request`, `unsupported_request`,
`source_unavailable`, `no_match`. No product is returned without a supported
need-linked explanation (extension 5a).

## UC-M2-02

`analyse_restocking` takes trusted authorisation, catalogue, inventory-service and
completed-sales-snapshot dependencies. It validates permission before reading data.
It calls `InventoryQueryService.lookup_stock` rather than inventory SQL, retaining
the Figure 14 interaction boundary. The current protocol only models success;
the adapter must raise for denied, missing or unavailable results. The inventory
owner still needs to implement the detailed lookup contract.

`POST /api/restocking-priorities` accepts `{}`, `{ "product_id": "..." }` or
`{ "category": "Wine" }`. Server integration must supply all of:

- `restocking_authorise(request, scope)`: authenticate the HTTP request and
  authorise the exact requested scope; default denies with 403.
- `inventory_service`: an authorised service implementing the existing protocol.
- `restocking_sales_loader()`: a complete `SalesSnapshot` with source update time,
  inclusive completed date range, and completed sale product/date/quantity records.

Allowed requests without connected services return 503. Neither a client role
nor a boolean in the JSON body can grant permission. Catalogue loading is shared
with the existing application; integration must ensure the authenticated scope
is authorised for those catalogue entries. Sales loaders must deliver only
authorised records, and inventory adapters must enforce their own access boundary.
Raw existing `sales` rows alone cannot assert snapshot completeness/freshness;
no source timestamp is fabricated for them.

Implementation choices, not report-prescribed formulas:

- Product or category scope, case-insensitive category; omitted scope means all
  authorised catalogue products. Unknown scope is rejected before stock/sales reads.
- Default freshness is 24 hours, injectable through `max_age`; future or timezone-naive
  timestamps are invalid. The team can change this policy without changing the rule.
- All inventory records must refer to the same store inventory. Any incomplete,
  stale, invalid or unavailable required evidence yields `data_error` without
  priorities. This implements the error alternative permitted by extension 3a.
- Snapshot end date must precede the analysis date. Its provider explicitly asserts
  completeness. A complete empty period means zero completed sales, not missing data.
  Cost is not needed for restocking, so a sale lacking cost can still be evidence.
- Consider products at or below threshold. Rank by ascending stock/threshold ratio
  (denominator 1 at threshold zero), then descending sold units in the same period.
  Equal evidence retains equal competition rank (e.g. 1, 1, 3); ID only stabilises display.
  This is a transparent prototype heuristic, not a demand forecast.
- Return inventory quantities/thresholds/timestamps, sales quantities/period/source
  timestamp, generation time, ranking rule, and a reason per product (§11).

Outcomes correspond to the written extensions and Figure 19:
`denied`, `invalid_scope`, `data_error`, `no_priority`, `presented`.
No final reorder quantity, supplier contact/order, inventory modification or
procurement approval is performed.

## Demo

Start using the README's fixture setup. Save **Use sample**, then click **Recommend drinks**. Below it, choose a sample category and click **Review sample priorities**. Wine produces two tied priorities; Beer produces
an explicit no-priority result.

`POST /api/demo/restocking-priorities` uses only isolated fixed fixtures from
`backend/member2_demo.py`, with a fixed 27 October 2026 clock and explicit
`data_mode: fixture`. It does not load or modify operational inventory/sales.
It is disabled outside fixture mode. This is not evidence of operator
authentication, current stock integration, or live-model quality.

## Verification

`tests/test_member2.py` covers the written success/exception paths, conservative
matching and explanation, no budget filtering, catalogue failures, authorisation
before reads, invalid scope, stale/missing/invalid data, complete empty sales,
ranking/ties, zero thresholds, source traceability, handoff failure, default API
denial, fixture separation, and database non-mutation.
`frontend/e2e/member2.spec.ts` covers the saved-request recommendation flow,
reload, tied priorities, category changes, no-priority results and mobile layout.
All these checks use fixtures/mocks and zero university calls.

Verified on 27 October 2026 on macOS with Python 3.13 and Node 24.21.0:

- `.venv/bin/python -m pytest -q`: **143 passed** (entire backend suite).
- `.venv/bin/python -m pip check`: no broken requirements.
- `npm run build`: TypeScript checking and Vite build passed.
- `npm run test:e2e`: **4 passed**, including both existing capture tests.
- Inspected desktop recommendation and mobile restocking screenshots under
  `frontend/test-results/`; no clipped content was observed.

Node 24 was already installed on this machine; the team's documented Node 22
setup was not changed. The browser test server required permission to bind its
local port outside the sandbox. Dependencies and Chromium were installed; no
university key was read or changed. Feature changes are committed separately from the unified interface.
