# Team implementation and integration status — 28 October 2026

Based on the submitted Stage 1 report §6 and §10 (all ten core use cases), source
on GitHub and the combined test results. This records observable implementation;
it does not assess work performed outside the fetched repository.

## Use cases

| Owner | UC | Submitted name | Current state |
| --- | --- | --- | --- |
| M1 / Jose | UC-M1-01 | Submit Product Assistance Request | Connected: React, campus-qwen extraction, validation, saved request and downstream inbox. Historical live verification; current combined tests use fixtures. |
| M1 / Jose | UC-M1-02 | Check Current Stock | Connected: operator token, batch lookup, exact source values, found/not-found/stale/error statuses, read-only storage. Merged through PR #3. |
| M2 / Cedar | UC-M2-01 | Receive Drink Recommendations | Connected: Qwen ranks catalogue IDs with validated need/fact references; saved results are reused. Fixtures retain Cedar's matcher. Occasion/party-size suitability remains unresolved without catalogue metadata. |
| M2 / Cedar | UC-M2-02 | Review Restocking Priorities | Connected: authenticated shared inventory and completed sales, explainable ranks, no-priority and stale/missing-data errors. Original fixed demonstration retained separately in fixture mode. |
| M3 / Lio (Houyuchen / liou87) | UC-M3-01 | Receive Low-Stock Alert | Missing implementation; visible placeholder only. |
| M3 / Lio (Houyuchen / liou87) | UC-M3-02 | Review Profit Margins | Connected: authenticated product/category/completed-period analysis, exact decimal calculations, missing-cost exclusions and coverage, no-data and source-error outcomes. |
| M4 / Avan | UC-M4-01 | Apply Budget Filter | Connected: saved request and recommendation candidates, authorized catalogue prices, preserved order, explicit missing/invalid/foreign-currency budget and no-match results. |
| M4 / Avan | UC-M4-02 | Check Product Availability | Connected: shared stock adapter, customer recommended/filtered candidates and operator selections; available/unavailable/unknown with source timestamps and limitations. |
| M5 / Lira | UC-M5-01 | Review Reorder Suggestions | Missing implementation; visible placeholder only. |
| M5 / Lira | UC-M5-02 | Detect Demand Trends | Missing implementation; visible placeholder only. |

Seven use cases have connected implementations. Three implementations have not
been found. Representative model checks are recorded separately; this does not claim
all Stage 2 assessment requirements or unrestricted model accuracy are complete.

## Contributions evidenced in Git

- **Jose / therealjosemaria:** shared React/FastAPI/LangGraph/SQLite foundation,
  UC-M1-01, live-model adapter and quota protections, shared domain contracts,
  onboarding/verification documentation, UC-M1-02 and its operator UI, integration
  branches and pull requests. Current work adds the cross-feature API/UI adapters.
- **Cedar / cedar:** recommendation and restocking modules, fixtures and tests,
  catalogue API and unified three-agent interface, responsive catalogue/product
  views, navigation and workspace placeholders, documentation and browser tests.
- **Lio / Houyuchen / liou87:** profit-margin module and tests, shared products
  and sales tables with sample data, performance verification, inventory-contract
  proposal and implementation notes.
- **Avan / Avan105:** budget-filter and product-availability modules with their
  unit tests. This integration retains those modules and connects their results.
- **Lira / Member 5:** no implementation commits/branches found in the fetched repository
  at this review. Local, unpushed or differently attributed work may exist; this
  statement does not infer that no work has been done.

PR #2 integrated all earlier contributor branches while retaining authors and
history. PR #3 merged UC-M1-02. Main remains pull-request-only with no bypass list.
PR #4 merged the cross-feature connections. PR #5 merged Qwen recommendations,
caching, actual agent handoffs and optional local fallback. The university remains
primary with no application daily cap; local Qwen handles service unavailability.

## Shared decisions and boundaries

- **Currency (user agreed 28 Oct):** catalogue and unqualified dollars are AUD.
  Explicit recognized foreign currencies are rejected; no FX conversion. The
  shared Stage 1 CustomerRequest/Product models remain unchanged.
- Customer budget/availability endpoints read the saved published request;
  candidates and prices are reconstructed server-side, never supplied by the
  browser. The local random request UUID identifies the customer workflow; there
  is no public multi-user session/authentication system.
- Operator stock, availability, profit and connected restocking require the same
  private server token. Navigation/role labels grant no authority. The token is
  kept in page memory and clears on reload, not stored in browser persistence.
- Restocking uses the InventoryQueryService interface. Avan's availability
  evidence is supplied through an explicit adapter from that interface's statuses.
  Inventory remains the sole source of quantity and source timestamps.
- SQLite data is a labelled prototype snapshot. Inventory timestamps are preserved
  and age naturally. Restocking's sales snapshot timestamp is the time completed
  rows were read; it is not a fabricated source-modification timestamp.
- Lookup, budget, availability, restocking and profit operations do not invoke
  the LLM or alter stock/sales. Live capture and new recommendation generation use
  models; saved recommendation reuse, arithmetic and inventory reads do not.

## Joint test walkthrough

Start with fixture mode, so the test makes no university model calls.

1. **Customer assistant:** Use sample → Capture and save → Recommend drinks.
   Shiraz and Pinot Noir match the preferences; recommendations do not budget-filter.
2. **Apply budget filter:** AUD 30 retains Shiraz at 25 and excludes Pinot Noir at 32.
3. **Check filtered availability:** uses the saved filtered candidates and actual
   prototype inventory. Availability can also check unfiltered recommendations
   before budget filtering, including when the budget is missing.
4. **Inventory & procurement:** enter the private operator token from `.env`.
   Stock lookup shows exact stored evidence. Availability shows Moscato (zero)
   unavailable, Pale Ale (stale) unknown, and missing vodka stock unknown.
5. **Business insights → Restocking priorities:** enter that same token, choose
   Sauvignon Blanc and Review connected priorities. It has below-threshold stock
   and completed sales evidence. Choosing all products reports an evidence error
   because the prototype deliberately contains stale/missing records.
6. **Profit margins:** choose Pinot Noir to demonstrate partial coverage because
   one sale lacks cost; choose Shiraz for a complete summary. Dates are optional
   for product/category scope; a date-only scope requires both completed dates.
7. Alerts, reorder and demand-trend tabs remain placeholders; they do not generate
   fabricated outputs. Start a new request explicitly to clear a failed capture
   attempt instead of needing an incognito browser window.

Use the README for installation and `VERIFICATION.md` for exact results. The
university VPN plus reverse model tunnel is needed for university capture and
new university recommendations; local fallback uses the server's own runtime. The
browser preview uses its separate SSH forward to port 8004.

The [agent workflow guide](agent-workflows.md) describes Customer → Inventory and
Business Insights → Inventory handoffs and persisted traces. The [Agile guide](agile/README.md)
links the owner's existing KAN board. KAN-4 through KAN-20 now track the ten use
cases and shared contributions with evidence: 10 Done, 2 In Review, 4 To Do and
1 In Progress. Sprints are disabled and require the space-admin UI toggle. Only
Jose is currently listed as an assignable human; other authors are credited in
descriptions/labels. No historical meetings or burndown data have been fabricated.
