# Submitted Stage 1 → implementation alignment

Source: submitted `AI_Multi_Agent_Alcohol_Retail_Project_M5_Sequence_Fixed.docx.pdf`,
not the Critical Fixes revision. Checked §4, §6.1.1, §10.1, Figure 4 (p35),
Figure 5 (p36), Figure 7 (p38), and Figure 18 (p49).

## Corrections to the first slice

| Submitted model | Python contract | Correction |
| --- | --- | --- |
| CustomerRequest.budget: Decimal [0..1] | `Decimal \| None` | Was just quoted text; now normalized numeric value |
| partySize: Integer [0..1] | `party_size: int \| None` | Was quoted text; now an integer without rounding |
| occasion: String [0..1] | `occasion: str \| None` | Retained |
| tastePreferences: String [0..*] | `taste_preferences: list[str]` | Was one nullable string |
| constraints: String [0..*] | `constraints: list[str]` | Was one nullable string |
| status: RequestStatus | `RequestStatus` enum | Added; labels taken from Figure 18 |

`backend/models.py` contains the shared domain schemas. Python snake_case maps
directly to the diagram's camelCase. Decimal fields serialize as strings in JSON;
e.g. budget `"30.25"` is a decimal value, not the original phrase `"under $30.25"`.
No currency, budget basis or comparison semantics are invented. Original wording
is preserved in `evidence`; downstream budget filtering still owns its decisions.

The extraction step supplies exact source quotes. `backend/capture.py` validates
them, normalizes a single explicit numeric budget/party size, and creates a
`CustomerRequest`. Multi-value preferences/constraints are supported. Missing
scalars are null; missing lists are empty; `missing_fields` lists either kind.
Unresolved numeric formats remain unknown. The normalizer now supports English
number words, correctly grouped thousands, decimals and `k` shorthand. See the
UC-M1-01 acceptance matrix for supported cases and remaining semantic limitations.

New valid requests are preserved as `RequestAvailable`, then become
`RequestConfirmed` after durable inbox handoff or `DownstreamUnavailable` if the
configured publisher fails. Unusable all-unknown results are explicit incomplete
records and are not published. Legacy records remain `RequestAvailable`.
Downstream business features themselves remain for later work.

## Persistence and API

POST `/api/requests` and GET `/api/requests/{id}` return a typed `SavedRequest`:
metadata + `needs: CustomerRequest` + original `evidence` + `missing_fields`.
FastAPI's OpenAPI schema now exposes that contract.

Existing SQLite `needs` JSON stores evidence. Reads normalize it using the same
function as new records; the old evidence and original live result are not
overwritten or deleted. The old persisted `missing_fields` column is retained for
compatibility; API missing fields are derived afresh from the normalized request.
No model calls are made when reading or upgrading the representation.

## Other shared entities (schemas only)

- Product: catalogue attributes only; no stock quantity.
- Inventory: inventory ID and name. The eventual repository must enforce the
  single store-level inventory; a schema alone does not enforce global cardinality.
- InventoryItem: inventory/product references, quantity, threshold, timestamp.
- SalesRecord: product reference, date, quantity, selling price and cost.

IDs represent the associations shown in Figure 4 and §4. These schemas do not
create tables, foreign keys, agent implementations, or the other members' features.
Product and SalesRecord now have shared SQLite tables in `backend/retail_data.py`
(see `docs/uc-m3-02-profit-margin.md`); Inventory and InventoryItem still have none.

## Inventory interface: agreed interpretation, implementation pending

Figure 4 specifies `lookupStock(productId: String): InventoryItem`.
`backend/interfaces.py` preserves that successful-return signature as a Python
Protocol (`lookup_stock`). Figure 7 makes InventoryProcurementAgent its provider,
with the other agents consuming the service instead of reading inventory SQL.

However, §6.1.2 and UC-M1-02 additionally require authorization context,
one-or-more product IDs, and explicit found/not-found/stale/error results.
The diagram does not specify those result/error types. The user confirmed that
the detailed written requirement governs behaviour; the diagram describes the
simpler successful case. Before implementing UC-M1-02, update the protocol with
the detailed request context and explicit result outcomes.
The protocol is a faithful transcription of the success signature, **not a
complete integration contract or an implemented stock lookup**.

No recommendation, budget filtering, clarification or inventory behaviour was
added to UC-M1-01. No additional live model calls were needed for this alignment.

## Member 2 prototype

See [Member 2 implementation](member2-implementation.md) for submitted report
sections, diagrams, implementation choices and integration limitations.
