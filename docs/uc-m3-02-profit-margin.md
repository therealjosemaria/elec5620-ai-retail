# UC-M3-02 profit margin reference

Authority: submitted report §6.3.2 (M3-AR-02), §10.6 (UC-M3-02), §4 (Sales fields),
§11 (M3 Profit Margin NFR), Figure 4 (`BusinessInsightsAgent.analyseProfitMargin()`,
`SalesRecord`), Figure 5 (example SalesRecord) and Figure 7 (the Business Insights
Agent analyses sales records directly). The report has no activity, interaction or
state diagram for this use case, so the written text governs.

The copy reviewed for this work has page numbers one lower than those cited in
`stage1-alignment.md` (e.g. Figure 4 on p34, not p35). Confirm it is the same
Sequence Fixed submission; section and figure numbers are used here.

## Implemented boundary

`backend/profit_margin.py` is a read-only, deterministic calculation. The caller
supplies loaders for authorised sales rows and the product catalogue; nothing is
written and no downstream action is triggered. It makes no model call.

Not yet wired: no API route, UI, or sales/product tables. Those depend on the
shared decisions listed at the end.

## Implementation decisions (Member 3)

| Topic | Decision | Basis |
| --- | --- | --- |
| Cost semantics | `selling_price` and `cost` are **per unit**; totals multiply by `quantity` | Figure 5: quantity 2 with sellingPrice 67.00 against catalogue price 65.00 only reads as per-unit; cost 52.00 read the same way. **Team to confirm** (shared field). |
| Margin formula | `profit / revenue × 100` (gross margin), rounded half-up to 2 dp | Not defined in §6.3.2; every result states it in `calculation_basis` (§11 explainability) |
| Zero revenue | Margin is null with a stated limitation | No fabricated value (§6.3.2 exceptions) |
| Arithmetic | `Decimal` throughout; money sums are not rounded | §11: figures must exactly match expected values |
| Scope | Product **or** category, and/or an inclusive date range; at least one; not product and category together | §6.3.2 input: "product, category, or completed date range"; output "time period where applicable" |
| Completed period | Range must end before today (UTC, as elsewhere in the app) | "completed sales period" |
| Category match | Case-insensitive | Usability; catalogue values are not altered |
| Unknown product/category | `invalid_scope`; sales are not read | §10.6 2a |
| Missing cost | Record excluded, counted, coverage stated, never estimated | §10.6 3a |
| Other invalid records | Missing/NaN/negative price or cost, or quantity < 1: excluded and counted | §6.3.2: "sales records are incomplete" → partial result with limitation |
| Records not matchable to scope | Missing product/date, or product absent from catalogue for a category scope: counted as `unassigned`; result is partial | Do not estimate (§6.3.2 exceptions) |
| Shared `SalesRecord` | Unchanged; missing cost is handled at the data-source row level | Figure 4 makes cost required; 3a requires handling its absence |
| Records analysed | Returned as `analysed_records` plus `record_count` | §6.3.2 acceptance: "identifies the records analysed" |
| LLM | Not used | Not required by §6.3.2; exact-match NFR; conserves the live allowance |

## Outcomes

`complete`, `partial` (3a), `insufficient_data` (3a, nothing usable),
`no_data` (4a), `invalid_scope` (2a), `source_unavailable` (3b). Only `complete`
and `partial` carry financial values.

## Acceptance matrix

| Report path | Implemented outcome | Evidence (`tests/test_profit_margin.py`) |
| --- | --- | --- |
| Main 1–6 | Exact revenue, cost, profit, margin and record count per scope | `test_main_flow_exact_figures_for_each_scope`, `test_result_states_scope_and_basis_with_decimal_strings` |
| 2a invalid scope | Rejected before sales are read | `test_2a_invalid_scope_rejected_without_reading_sales` |
| 2a unauthorised | **Not implemented** — needs the shared authorisation mechanism | — |
| 3a missing cost | Excluded and reported with coverage; no figures if nothing usable | `test_3a_missing_cost_excluded_with_coverage_reported`, `test_3a_all_costs_missing_produces_no_figures` |
| 3b source unavailable | No values; no data-source details exposed | `test_3b_unavailable_source_returns_no_values_or_details` |
| 4a no records in scope | Explicit `no_data` | `test_4a_no_sales_in_scope_is_explicit` |
| §11 accuracy | Decimal exactness and stated rounding | `test_decimal_arithmetic_has_no_float_drift`, `test_margin_rounds_half_up_to_two_places` |
| No automatic action | Inputs are only read | `test_analysis_is_read_only` |
| §6.3.2 10-second target | Not yet measured; in-memory arithmetic only | — |

## Needs team agreement

1. Confirm `SalesRecord.cost` (and `selling_price`) are per-unit values.
2. Shared `products` and `sales` tables with prototype data (§4): who creates them.
   Store money as decimal text, not SQLite REAL, and allow a null `cost` so 3a can occur.
3. Authorisation/role context for founder-only analyses, consistent with the
   pending `InventoryQueryService` update and the code-selected identity pattern in
   `backend/handoff.py`.
4. API route and UI: requires agreed changes to the shared `main.py` and `main.tsx`.
