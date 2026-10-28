# Remaining core acceptance — 28 October 2026

Authority: submitted report §6.3.1/10.5 and Figures 10/15/20 (alerts),
§6.5.1/10.9 and Figures 12/17/22 (reorder), §6.5.2/10.10 (demand),
§6.4/10.7–10.8 and Figure 16 (Member 4), §6.2.1/10.3 (recommendations).
The source and relevant activity/sequence diagrams were inspected.

## Owner-approved rules

The report names agreed reorder/trend rules without providing their formulas.
The owner explicitly approved these rules in this session:

- At/below threshold, target stock = twice threshold; suggest max(0, target − stock).
  Stock 10/threshold 10 suggests 10; stock 0/threshold 0 honestly suggests 0.
- Compare completed inclusive dates against the immediately preceding equal number
  of days. September 1–30 compares with August 2–31, not all of August.
- Positive/negative/zero units difference means increasing/decreasing/stable.
  No rows mean insufficient evidence, not assumed zero sales. Explicit valid zero
  quantities can support zero totals. Zero baseline leaves percentage undefined.

## Acceptance and boundaries

| UC | Implemented behaviour | Verification |
| --- | --- | --- |
| M3-01 alerts | Inventory Agent consumes typed lookup evidence, alerts every current product at/below threshold, reports no alert above, withholds stale/missing/invalid records. Owner follow-up: Figure 20 states in `backend/low_stock.py`, see `docs/uc-m3-01-low-stock-alert.md` | Equality/zero/invalid/future/naive cases, source gaps, access denial, persisted trace, unchanged inventory/sales |
| M5-01 reorder | Uses current evidence and approved formula; shows stock, threshold, timestamp, quantity, rule and explanation. Missing rule produces no unsupported quantity | Formula boundaries, missing/stale withholding, missing rule, real SQLite API and React |
| M5-02 demand | Business Insights reads completed quantities; shows both periods, units/change/rule/classification and supporting rows. Missing cost does not invalidate quantities | Increasing/decreasing/stable, zero baseline, missing comparison/rule, invalid scope/date/rows, source error, read-only storage, API/React |
| M4-01/02 | Avan's Decimal/Stale contracts merged; InventoryQueryService owns freshness. API consumes saved requests and current inventory, not browser-supplied prices/stock/roles | Existing and new contract, authentication, spoof rejection, source/availability and OpenAPI tests |
| M2-01 review | Existing Qwen ranking/cache and no-match/error paths retained. No invented event suitability or servings where catalogue metadata is absent | Existing grounding/cache/source tests plus occasion-only no-match and invalid occasion-evidence rejection |

No orders, supplier contact, payments, stock writes, price changes or forecasts
are added. Unknown catalogue suitability remains an explicit data limitation.

## Connected workflows and APIs

Inventory workspace replaces alert/reorder placeholders with authenticated forms.
POST `/api/low-stock-alerts` and `/api/reorder-suggestions` accept `product_ids`;
empty/omitted IDs review all authorised catalogue IDs, including missing-stock gaps.
Inventory Agent performs lookup through InventoryQueryService then its own decision
in LangGraph; reports/traces are persisted for protected readback.

Business Insights demand form calls POST `/api/demand-trends` with product or
category, `start_date`, `end_date`; the agent reads sales directly. Existing
Customer–Inventory and Business Insights–Inventory handoffs remain. No all-to-all
link is invented. Deterministic features make zero model calls.

Member 4 compatibility routes: POST `/api/member4/budget-filter` accepts a saved
`request_id`; POST `/api/member4/availability-check` accepts `product_ids` and
requires the operator token. Avan's standalone raw-evidence/role endpoints were
adapted during integration to enforce the report's trusted source boundary.

## Contribution and verification limits

Avan's branch history is preserved by a merge. Report ownership remains with
Cedar/Lio/Avan/Lira. Gap completion/integration here was performed by Jose's
authorized coding assistant; do not attribute this new code to the other members.
Earlier representative university checks remain in VERIFICATION.md; fixture tests
are not general AI-quality evidence. Final submission/demo and genuine Agile
meeting evidence still require team participation.
