# UC-M1-01 acceptance reference

Authority: submitted report §6.1.1 (M1-AR-01), §10.1 (UC-M1-01),
Figure 4 (types), Figures 8/13/18 (activity, interaction and states).

## Implemented boundary

React submission → Customer Agent LangGraph extraction → evidence validation →
typed normalization → SQLite preservation → downstream request inbox → confirmation.
No products are recommended, budget-filtered or checked for stock by this use case.

The default downstream boundary is a **durable SQLite inbox**. It accepts validated
requests for later authorized feature consumption; it does not execute another
member's behaviour. `read_published_request` requires a code-selected
`RequestConsumer` enum and returns the typed payload. Do not derive that enum from
an unauthenticated user-supplied role. The whole application remains localhost-only;
this internal allowlist is not a public-user authentication system.

`create_app(publisher=...)` allows a future in-process service adapter to accept the
request or raise on unavailability. It receives a defensive copy. Saved values
are committed before handoff; a failure results in `DownstreamUnavailable` and a
visible message without deleting those values or calling the model again.
Duplicate submissions return the same saved result without republishing.

## Acceptance matrix

| Report path | Implemented outcome | Evidence |
| --- | --- | --- |
| Main 1–4 | Capture stated fields, normalize and validate | `test_main_flow_and_authorized_consumer`, numeric/evidence tests |
| Main 5–6 | Durable handoff followed by `RequestConfirmed` | Main-flow test and fixture browser test |
| 1a empty input | HTTP 422, no model call | `test_invalid_input_never_calls_model` |
| 1a unusable content | Explicit incomplete result, all unknown, no downstream publish | `test_1a_unusable_input_not_published` |
| 2a ambiguous/conflicting fields | Unknown affected field; retain clear fields | `test_2a_conflict_preserves_other_clear_fields`, range/ambiguity cases |
| 4a invalid structure or invented evidence | HTTP 502, no CustomerRequest publish | Bad-output tests, `test_4a_invalid_result_never_reaches_publisher` |
| 5a downstream unavailable | Saved values retained, visible unavailable outcome | `test_5a_downstream_failure_preserves_request_and_deduplicates` |
| Model/tool failure | Explicit error, no automatic retry | Provider-error and retry tests |
| Existing data | Non-destructive status-column migration | `test_original_six_column_database_upgrades_without_losing_data` |

Successful captures persist `RequestConfirmed`; legacy records remain
`RequestAvailable` because no handoff was recorded for them. Unusable results
persist `RequestUnusable` as explicit incomplete records but are not placed in
the downstream inbox. Validation failures do not create a CustomerRequest.
Request/attempt statuses are sufficient for this use case; a full event-history
UI is not an additional requirement.

## Number handling and AI limits

Explicit digit amounts, correctly grouped thousands, `k` shorthand, English
cardinal numbers through hundreds/thousands, and word decimals are normalized.
Ranges, alternatives, approximate amounts and unsupported expressions remain
unknown. Party size is never rounded. Original wording is retained.
Currency, budget basis and purchasing decisions belong to downstream features.

The model determines which words belong to which fields. Evidence matching
prevents invented quotation text, not every possible semantic mistake. Mocked
tests prove the application's response to model outputs; live evaluation adds
representative evidence but is not a guarantee for arbitrary language.

The live adapter explicitly requests JSON-object output with temperature zero.
Local evidence/schema checks still run; JSON mode is not a semantic guarantee.
Truncated or filtered responses are rejected without retry. This implements
§10.1 extension 4a and Figure 13's validation boundary without inventing values.
Both complete-request and conflicting-budget browser cases passed on 20 October
2026; see the chronological results in `VERIFICATION.md`.

## Running checks

Normal zero-call checks: `python -m pytest -q`, then frontend
`npm run build && npm run test:e2e`.

Manual live browser verification is deliberately separate:

1. Keep the configured university endpoint reachable.
2. Start a live backend on localhost 8002, using the normal database/call counter.
3. From `frontend`, run
   `CONFIRM_LIVE_CALLS=2 node scripts/verify-live.mjs`.

This makes at most two submissions: a full request with number words, and a
conflicting budget with other clear preferences. It stops on first failure and
does not retry. Readback/reload checks spend no model calls. Do not run this as
part of automated CI.

To run only the unresolved conflict case, with one available local attempt:
`LIVE_CASE=conflict CONFIRM_LIVE_CALLS=1 node scripts/verify-live.mjs`.
Do not increase the local cap merely to repeat a failing test.

See `VERIFICATION.md` for actual results, not merely the expected checks.
