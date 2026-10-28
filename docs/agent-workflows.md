# Qwen recommendations and agent communication

Authority: submitted Stage 1 §1.4, §6.1.1/6.1.2/6.2.1/6.2.2, §10.1–10.4,
§10.6/10.7/10.8 and Figures 4, 6, 7, 14 and 16. This implements the three-agent
communication design agreed on 28 October 2026 without adding a broker, separate
agent servers or a fourth model-based supervisor.

## Agent ownership and actual handoffs

| Role | Responsibilities | Communication |
| --- | --- | --- |
| CustomerAgent | Existing capture step; Qwen catalogue recommendations; deterministic budget tool; customer result | Requests availability from InventoryProcurementAgent using validated product IDs and trusted server context |
| InventoryProcurementAgent | Read-only lookup, availability, low-stock alerts and reorder quantities | Returns typed inventory evidence to Customer/Business Insights; uses InventoryQueryService for its own alert/reorder graph |
| BusinessInsightsAgent | Restocking, profit and demand trends over authorised completed sales | Requests Inventory evidence for restocking; profit/demand read sales directly |

Customer and Business Insights have separate LangGraph workflows. A graph node
executes each real handoff; trace entries record its actual request and result.
No Customer-to-Business-Insights link is invented. Inventory alert/reorder graphs
and Business Insights demand graph are implemented with actual source reads,
deterministic approved rules and saved traces. See `remaining-core-acceptance.md`.

UC-M1-01's capture endpoint still only extracts, validates, saves and publishes
CustomerRequest. It does not generate recommendations or access inventory. The
explicit **Run agent workflow** action starts the subsequent use cases:

1. Customer Agent generates or reads the saved recommendation result.
2. Its budget tool applies the saved budget to current authorised catalogue prices.
3. Customer Agent asks Inventory Agent for availability of the remaining IDs.
4. Inventory Agent uses InventoryQueryService and classifies the returned evidence.
5. Customer Agent returns the combined result and the persisted communication trace.

Missing budget means filtering is skipped and the result is explicitly partial;
recommended products may still be checked for availability. Invalid/unsupported
budget stops the workflow. No matches stop before inventory. Unknown stock stays
unknown. Re-running the workflow refreshes inventory evidence but reuses the
recommendation result.

## Qwen recommendation boundary

Live mode uses `campus-qwen` through the existing OpenAI-compatible proxy. The
payload contains structured needs and the authorised catalogue, excluding budget,
prices and inventory. Qwen selects/ranks IDs and supplies evidence references.
The response must be JSON with recommendations and unresolved-needs lists.

Code validates schema, unique known IDs, ranks, exact stated-need references and
actual catalogue attribute values. Every explicit constraint needs supporting
evidence; recognised hard constraints retain deterministic checks and can have
their evidence completed directly from the validated catalogue facts.
Product names, prices and attributes in the result are supplied by the catalogue,
not model-generated replacements. Short explanations are assembled from validated
evidence references rather than arbitrary model prose.

The catalogue has no explicit occasion-suitability or serving-capacity metadata.
Those needs remain unresolved rather than becoming invented suitability or serving
claims. Qwen handles broader taste language, but validated facts/references do not
prove every semantic match is correct. Evaluate representative model behaviour;
this code does not claim unrestricted language accuracy.

Fixture mode retains Cedar's labelled rule matcher and uses zero model calls.
Live failures never fall back silently to that matcher. The provider is configured
with JSON mode, temperature 0.2, a 2,048-token capture ceiling and 4,096-token
recommendation ceiling, 30-second university timeout and zero automatic retries.
Only the proxy-compatible `max_tokens` field is sent. Three agent roles do not imply three model calls for arithmetic
or stock reads.

## Durable recommendations and quota

`recommendation_results` has one row per immutable customer request. Creation
uses `BEGIN IMMEDIATE` to reserve a pending row before contacting the model.
Concurrent requests cannot both generate. A saved row stores the validated result,
mode, creation time and catalogue digest. Empty/no-match results are saved too.

- Reloads, restarts, repeated generation requests and workflow runs reuse saved data.
- A crash, invalid output or provider failure leaves pending/failed state. It is
  never automatically released or retried, because provider usage may be unknown.
- For another intentional attempt, explicitly start a new customer request.
- Fixture results remain labelled fixture after a mode switch. A live evaluation
  requires a fresh request; changing configuration does not invalidate the cache
  and spend allowance automatically.
- Cached product facts describe the generation-time catalogue snapshot. Budget
  filtering rereads current prices while preserving saved candidate order. A
  deleted candidate is reported rather than assigned an invented price.
- Capture and recommendation attempts share UTC-day usage tracking. There is no
  application daily cap by default; optional numeric test caps remain supported. Each
  live recommendation reservation is recorded in `attempts` with a
  `recommendation:<request UUID>` ID. Failed attempts count; cached reads do not.

Optional [local Qwen fallback](local-qwen-fallback.md) takes over when the university
is unreachable, times out, returns a server error or rejects calls for rate/quota
capacity. Every new operation tries university first; historical day-long quota
latches are ignored. Provider/model/reason are saved and displayed. Authentication,
request-schema and validation errors remain explicit and do not select local.

Complete untrusted recommendation output and its input snapshot are retained only
in the private ignored database. Unsupported uncertainty labels are withheld,
while invalid product/need/fact references still reject the result. After a
validator fix, a developer may explicitly validate a retained failed result with
`python -m backend.revalidate_recommendations REQUEST_UUID`. This is offline
validation with zero model calls; it is never automatic and does not retry a
network request. Changed published needs or a damaged snapshot prevent recovery.

Each provider is dispatched at most once per reserved operation; service failure
can dispatch once to university and once to local. This is not a guarantee of
provider billing or successful completion after an interrupted network call.

## API and trace persistence

| Method / path | Behaviour |
| --- | --- |
| POST `/api/requests` | Existing capture-only use case |
| POST `/api/requests/{id}/recommendations` | Explicit generation or saved-result reuse |
| GET `/api/requests/{id}/recommendations` | Saved result only; 409 if not generated/pending/failed; zero calls |
| GET `/api/requests/{id}/budget-filter` | Requires saved candidates; zero model calls |
| GET `/api/requests/{id}/availability` | Requires saved candidates; Inventory Agent handoff |
| POST `/api/requests/{id}/workflow` | Customer LangGraph workflow; generates recommendations at most once |
| GET `/api/requests/{id}/workflow` | Latest saved customer report; no execution |
| GET `/api/workflows/{workflow_id}` | Saved report; operator token required for business reports |
| POST `/api/restocking-priorities` | Business Insights → Inventory → Business Insights graph |
| POST `/api/profit-margins` | Business Insights graph over completed sales; no inventory call |

Workflow reports are stored in `workflow_runs`. Each trace entry contains sender,
receiver, operation, status and product IDs under the report's workflow ID. No
provider prompts, raw responses, operator token or university key are in the trace.
The UI renders these actual handoffs under **Agent communication** and restores
customer reports through a read-only GET after reload.

Only intentional POSTs can generate model output. No graph-level model retry,
automatic cache expiry, public multi-user authentication or distributed message
transport is introduced. Existing localhost/token boundaries still apply.

## Verification

Fixture and intercepted-SDK tests cover provider wire format, grounding failures,
concurrency, restart reuse, terminal pending/failed states, cached no-match,
capture/recommendation shared quota, changed prices without regeneration, and
real Customer/Business Insights-to-Inventory handoffs. Browser tests cover the
visible trace, cached rerun, saved report/recommendation reload and mobile layout.

The live smoke script is deliberately opt-in:

```bash
cd frontend
LIVE_TEST_URL=http://127.0.0.1:8005 CONFIRM_LIVE_CALLS=2 node scripts/verify-live-agents.mjs
```

Run against a separately started live backend with a reachable university proxy
and configured private key. It makes at most two new calls (capture plus one
recommendation), stops on failure, then checks cache reuse and readback without
more generation. Run without other concurrent live users for exact counter checks.
See `VERIFICATION.md` for actual results and any outstanding live-network checks.

To verify an already saved live university result without spending allowance:

```bash
LIVE_TEST_URL=http://127.0.0.1:8005 LIVE_EXISTING_REQUEST_ID=REQUEST_UUID CONFIRM_LIVE_CALLS=0 node scripts/verify-live-agents.mjs
```

The script requires a saved live recommendation before running the workflow;
it then asserts cache reuse, persisted readback and no new university attempts.
