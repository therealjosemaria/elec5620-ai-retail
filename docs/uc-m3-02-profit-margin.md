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

Data comes from the shared `products` and `sales` SQLite tables in
`backend/retail_data.py` via `load_sales(db)` and `load_products(db)`. The tables
are created at startup and seeded with prototype data only when both are empty.
The seed includes one September sale without cost, so a Wine/September analysis
demonstrates the 3a partial result.

**28 October integration update:** authenticated `/api/profit-margins` and the
Business insights page now call this module with shared completed SQLite sales.
Missing-cost coverage and errors are rendered explicitly. The decisions below
describe the original module; see `team-status.md` for current wiring.

## Implementation decisions (Member 3)

| Topic | Decision | Basis |
| --- | --- | --- |
| Cost semantics | `selling_price` and `cost` are **per unit**; totals multiply by `quantity`. Adopted for the prototype tables and seed data; the team may revisit. | Figure 5: quantity 2 with sellingPrice 67.00 against catalogue price 65.00 only reads as per-unit; cost 52.00 read the same way. |
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
| 2a unauthorised | Operator token required before loaders run | `test_operator_endpoints_deny_before_returning_any_data` |
| 3a missing cost | Excluded and reported with coverage; no figures if nothing usable | `test_3a_missing_cost_excluded_with_coverage_reported`, `test_3a_all_costs_missing_produces_no_figures` |
| 3b source unavailable | No values; no data-source details exposed | `test_3b_unavailable_source_returns_no_values_or_details` |
| 4a no records in scope | Explicit `no_data` | `test_4a_no_sales_in_scope_is_explicit` |
| §11 accuracy | Decimal exactness and stated rounding | `test_decimal_arithmetic_has_no_float_drift`, `test_margin_rounds_half_up_to_two_places` |
| No automatic action | Inputs are only read | `test_analysis_is_read_only` |
| §6.3.2 10-second target | SQLite load plus analysis of 10,016 sales rows (Wine, Jan–Oct): median 0.082 s, max 0.089 s over 5 runs on Windows 11, Python 3.13.17, AMD64 CPU (family 23, model 96). The test asserts < 10 s. | `tests/test_retail_data.py::test_standard_analysis_within_ten_seconds` |

## Shared data tables

`backend/retail_data.py` now provides the shared `products` and `sales` tables (§4)
for every feature that reads the catalogue or completed sales, e.g. Drink
Recommendation, Budget Filtering, Restocking Decision Support and Demand Trend
Detection. Reuse them rather than creating parallel tables.

- Columns follow `Product` and `SalesRecord` in `backend/models.py`, plus a
  `sale_id` key. `flavour_tags` is a JSON list.
- Money is decimal text, never REAL; `selling_price` and `cost` are per unit.
- `sales.cost` is nullable so missing cost data (3a) can be represented.
- Prototype data: 6 products (Wine, Beer, Spirits) and 16 sales from August to
  October 2026, including the Figure 5 example sale.
- Inventory tables are not included; they belong with Inventory Lookup (M1-AR-02).

## Needs team agreement

1. Per-unit `selling_price`/`cost` is adopted for now; raise it if a feature needs
   a different meaning before others build on it.
2. Authorisation/role context for founder-only analyses, consistent with the
   pending `InventoryQueryService` update and the code-selected identity pattern in
   `backend/handoff.py`.
3. API route and UI: requires agreed changes to the shared `main.py` and `main.tsx`.
