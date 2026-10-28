# UC-M3-01 low-stock alert reference

Authority: submitted report §6.3.1 (M3-AR-01), §10.5 (UC-M3-01), §11 (M3 Low Stock
Alert NFR), Figure 10 (activity), Figure 15 (sequence) and Figure 20 (state machine).
Owner: Member 3 (Lio / Houyuchen). The first connected version was added during
integration by Jose's coding assistant (PR #8); this reference covers the owner's
follow-up described below.

## Implemented boundary

`POST /api/low-stock-alerts` (operator token required) runs the Inventory Agent
LangGraph in `backend/agent_workflows.py`: lookup through `InventoryQueryService`
(`backend/stock.py`), then the alert decision, then a persisted trace (Figure 15).

The decision lives in `backend/low_stock.py` (`evaluate_low_stock`).
`InventoryProcurementAgent.evaluate_replenishment` calls it when `reorder=False`.
Reorder suggestions (UC-M5-01) still use `evaluate_inventory` in
`backend/replenishment.py`, unchanged. The response keeps the shared
`InventoryDecisionResult` shape, so the React form and saved traces are unchanged.

Read-only and deterministic: no inventory or sales writes, no reorder quantities,
no supplier action and no model call (§6.3.1 out of scope).

## Item states (Figure 20)

| Status | Figure 20 state | Meaning |
| --- | --- | --- |
| `low_stock` | AlertGenerated | Current, valid record with `stock_quantity ≤ reorder_threshold` |
| `not_required` | NoAlert | Current, valid record above its threshold |
| `stale` | StaleRecord | Lookup marked the record stale; values shown, alert withheld (2b) |
| `excluded` | RecordExcluded | Not found, lookup error, invalid ID, or invalid values (2a); lookup reason kept |

Overall `outcome`: `presented` (alerts and no gaps), `partial` (some records stale or
excluded), `not_required` (4a: no current record at or below threshold) and
`data_error` (StatusUndetermined, 3a: no current, valid record at all). These names
are unchanged from the first version.

## Decisions (Member 3)

| Topic | Decision | Basis |
| --- | --- | --- |
| Alert rule | `stock_quantity ≤ reorder_threshold`, including equality and 0/0 | §6.3.1 "at or below the threshold" |
| Stale records (2b) | Withheld: status `stale`, evidence shown, never alerted as current | §10.5 2b allows "report as stale-based or withhold"; withholding avoids presenting old stock as current |
| Freshness | Taken from the lookup status (24-hour rule in `backend/stock.py`); not recomputed | One shared rule for M1/M3/M4/M5 (inventory contract proposal) |
| Invalid values | Negative quantity/threshold, naive or future timestamps are excluded even if marked found | Defensive repeat of the lookup's checks; no decision on such values |
| Distinct states | Stale and excluded are separate statuses with separate limitations | Figure 20 separates StaleRecord, RecordExcluded and StatusUndetermined |
| Module | Separate `backend/low_stock.py`; reorder path untouched | Keeps the M3 alert rule and the M5 reorder rule independently explainable |

## Acceptance matrix

| Report path | Implemented outcome | Evidence (`tests/test_low_stock.py`) |
| --- | --- | --- |
| Main 1–5 | Alert for every current record at/below threshold, none above; evidence and timestamp included | `test_main_flow_alerts_at_or_below_threshold_only`, `test_alert_carries_evidence_and_traceable_timestamp` |
| Main 6 | Available via API, React form and saved trace; inventory unchanged | `test_api_reports_figure_20_states_over_prototype_inventory` |
| 2a missing/invalid record | `excluded` with the lookup reason; partial result | `test_2a_missing_or_invalid_records_excluded` |
| 2b stale record | `stale`, withheld, evidence shown | `test_2b_stale_record_withheld_with_its_evidence` |
| 3a lookup unavailable | `data_error`; no alert; limitation stated | `test_3a_status_undetermined_without_current_evidence` |
| 4a nothing at/below threshold | `not_required` | `test_4a_no_product_meets_threshold` |
| No reorder calculation / no writes | `suggested_quantity` always null; inputs and inventory unchanged | Main-flow, `test_decision_is_read_only`, API test |
| Operator access | 403 without the token, no trace saved | `tests/test_remaining_core.py::test_operator_access_required` |
| §6.3.1 5-second target | Decision over 10,000 records: median 0.051 s, max 0.055 s; full API request over all prototype products: median 0.018 s (5 runs each, Windows 11, Python 3.13.17). Both asserted < 5 s | `test_performance_10000_records_within_5_seconds`, API test |
| Reorder unaffected | Reorder statuses and formula unchanged | `test_reorder_path_is_unchanged`, existing `tests/test_remaining_core.py` |

With the prototype inventory, "all products" returns `partial`: Pinot Noir,
Sauvignon Blanc and Moscato alert; Shiraz needs none; Pale Ale is `stale`; Premium
Vodka has no inventory record and is `excluded`.

## Limitations

- `evaluate_inventory(reorder=False)` in `backend/replenishment.py` still contains
  the earlier combined alert logic, used only by existing unit tests. It is left
  unchanged to keep the reorder module untouched.
- Authorisation is the shared operator token; there is no per-user identity.
