# First-slice verification — 20 October 2026

Story: submit stated needs in React, extract through a LangGraph node, validate,
save a CustomerRequest in SQLite, then read back and render the saved record.

| Boundary | Result | Evidence |
| --- | --- | --- |
| React build | Passed | TypeScript check + Vite production build |
| React → FastAPI | Passed, fixture mode | Chromium submit and error-path tests |
| FastAPI → LangGraph → validation | Passed with injected/fixture extraction | Backend tests |
| SQLite save/read/restart | Passed | Direct SQL assertion, GET readback, new app instance |
| SQLite → React | Passed | Saved fields visible; browser reload retains record |
| Desktop/mobile | Passed | Screenshots; mobile overflow assertion; no page errors |
| Installed model SDK request format | Passed with intercepted HTTP | Chat-completions URL, model and token cap assertions |
| SDK 429 retry behaviour | Passed with intercepted HTTP | Exactly one HTTP attempt |
| Real university model | Passed for one request via SSH tunnel | Live API returned 201; budget/preferences captured and omitted fields null |

After Stage 1 alignment: **31 backend tests, 2 browser tests passed**. `pip check` found no
dependency conflicts. npm installation audit reported zero vulnerabilities.
These checks do not establish absence of all security defects or AI errors.

**University generation requests made: one**, with automatic retries disabled.
After the Mac-to-server SSH tunnel was established, the live request
“I want red wine under $30.” returned budget `under $30` and preference `red wine`,
with party size, occasion and constraints correctly null, and was saved to SQLite.
This validates one live backend case, not general extraction quality. Browser tests
remain fixture-based. Direct server access still times out; the live configuration
depends on the Mac and its SSH tunnel at server localhost port 18000.
The later typed-schema alignment and updated list-extraction prompt were verified
with mocked tests only; no second live request was made. Tests cover numeric
normalization, list evidence, unknown values, shared schema boundaries, OpenAPI,
and read compatibility with the original stored evidence.

Resolved main versions: React 19.3.1, Vite 7.3.7, TypeScript 5.9.3,
FastAPI 0.151.0, Pydantic 2.14.1, LangGraph 1.2.16,
langchain-openai 1.7.2. Exact dependencies are locked. SQLite is from Python 3.13.
Stable release families were selected, not alpha/beta/RC channels; maintenance
activity does not mean a library is experimental.

Browser screenshots (generated, not committed):
`frontend/test-results/capture-desktop.png` and `capture-mobile.png`.

The verification skill guided testing across the complete application boundary,
including persistence and rendered output rather than just HTTP success.

## Clean-source onboarding rehearsal

On 20 October 2026, copied an explicit source-only file set into a separate
temporary directory without `.env`, databases, `.venv`, `node_modules` or `dist`.
Created a new Python 3.13 virtual environment, installed `requirements.txt`,
ran `pip check`, installed frontend dependencies with `npm ci`, rebuilt React,
and ran both test suites: **31 backend + 2 browser tests passed**.
The previously downloaded Playwright Chromium browser was reused.

A temporary Git index verified ignore rules for `.env`, database files and
dependency directories; staged whitespace checks passed. The known university
key was not present in staged source. No model calls were made.

This rehearsal ran on the same Linux ARM64 host, not on macOS or Windows/WSL.
It is a fresh source/dependency setup, not a GitHub clone: the working source
has not yet been committed or pushed. Cross-platform teammate onboarding and
the updated live browser flow remain unverified.

## UC-M1-01 completion work — 20 October 2026

Implemented the detailed main/extension paths: numeric word normalization,
explicit incomplete results for unusable content, a durable downstream inbox,
confirmed/unavailable persisted statuses, downstream failure preservation,
internal consumer allowlisting, and non-destructive legacy schema upgrade.
See `docs/uc-m1-01-acceptance.md` for the report-to-test matrix.

**57 backend tests and two fixture browser tests passed**, with a successful
TypeScript/React production build. Browser fixture results now show
`RequestConfirmed`. The new manual live verification script is opt-in only and
stops on the first failure; it is not part of normal automated tests.

The first updated live browser submission returned **502**. No automatic retry
or second case ran. An immediate empty, unauthenticated proxy probe through the
SSH tunnel timed out (HTTP 000). Thus network reachability is currently blocked;
this probe does not establish the precise cause of the earlier extraction error.
The local counter is now **2 attempts total**: the earlier successful call plus
this failed attempt. Actual provider token usage for the failure is unknown.

Live browser acceptance and the provisional 10-second performance target remain
unverified. Do not label UC-M1-01 fully accepted until the connection is restored
and those live cases are completed. No model requests should be repeated just
to investigate a network outage.

## Restored tunnel: live browser results — 20 October 2026

After restoring SSH forwarding, ran the two planned live cases without retries:

- **Complete request: passed.** “I need dry red wine for a birthday for six
  people, under fifty dollars, no sweet drinks.” produced budget `50`, party size
  `6`, birthday occasion, dry red wine preference and no-sweet-drinks constraint.
  Status was `RequestConfirmed`, no fields were missing, browser reload/readback
  matched, and direct SQLite inspection confirmed both the saved record and
  downstream inbox entry. Measured browser flow time was **5,075 ms**, including
  readback/reload/screenshot; this one sample meets the provisional 10-second target.
  Record ID: `e80343b3-a2bd-4610-b7cc-304527172519`.
- **Conflicting budget: failed.** The application returned HTTP 502 and logged
  `ValidationError`. It rejected the output rather than publishing an invalid
  CustomerRequest. The raw model response was not retained, so its exact schema
  defect cannot be established from the existing logs.

Stopped at that failure; no retries or additional generation calls. The local
daily counter is **4 attempts total**, including the earlier network-failed
attempt; this is not a measurement of provider tokens.

The happy path is live-verified. The conflicting-budget acceptance case remains
open; UC-M1-01 must not yet be described as fully accepted. The next step is
privacy-safe validation diagnostics and a deliberately budgeted conflict test,
not blind retries or relaxing the no-fabrication checks.

## Conflict follow-up — 20 October 2026

Removed contradictory prompt instructions (null for conflicting scalars versus
retaining the conflicting phrase). The prompt now consistently requests null,
while preserving other explicit fields. Added field/code-only validation
diagnostics, excluding response values and unknown field names.

Ran the opt-in conflict-only browser test once, without retries. It returned
HTTP 502 again. The detailed diagnostic output was not retained in the available
tool transcript, so the specific validation defect remains undetermined.
The local daily allowance is now exhausted at **5 attempts**; no further model
requests were made. This is the application's safety cap, not a confirmed
university quota. The conflict case remains **not live-accepted**.

Offline regression verification: **59 backend tests passed**. These cover
both null and quoted conflicting-budget evidence, preserving clear preferences,
and checks that validation diagnostics do not expose response values or unknown
field names. These fixture results do not substitute for live acceptance.

## Conflict fix and final representative acceptance — 20 October 2026

With the user-authorized local cap raised to 50, a diagnostic live attempt
confirmed `json_invalid` at the response boundary. Another diagnostic attempt
passed unchanged, establishing intermittent output-format failure rather than
a consistently failing conflict rule. The precise malformed response was not
retained. No raw provider content or credentials were logged.

The live adapter now requests `response_format={"type":"json_object"}` with
temperature zero, retains strict field/source validation, and rejects
truncated/filtered responses without retry. The proxy accepted this request
configuration. No permissive JSON repair or extra model calls were added.

Final live browser verification with this configuration passed both cases:

- Complete request: **4,472 ms**, ID
  `7592a832-eff1-47b8-b222-318fcf535dd2`; budget 50, party size 6 and all
  other explicit fields preserved.
- Conflicting budget: **3,309 ms**, ID
  `3be595b2-f628-4f67-a571-a251b3161fd1`; budget unknown, red wine preserved,
  other omitted fields unknown/empty.

Both returned `RequestConfirmed`, rendered successfully, survived browser reload,
and matched GET readback. Direct SQLite inspection confirmed saved status and
the typed downstream inbox payload for both. These two samples meet the
provisional 10-second target, not a general performance guarantee.

Four live attempts were used during this follow-up; the UTC-day total is
**9 of the local 50 cap**. University quota remains separate.

**62 backend fixture tests passed** and the frontend production build passed.
The browser regression exposed dependence on the private daily-cap setting;
its fixture server now pins its test cap to 5, independently of the user's
live cap of 50. Representative UC-M1-01 live acceptance is complete; other
use cases, cross-platform onboarding and arbitrary-input model accuracy are
not claimed by these results.

After isolation of the fixture cap, **both browser regression tests passed**.

## Output-limit and concise-response follow-up — 21 October 2026 (Sydney)

A user preview submission raised `LengthFinishReasonError`. Previous passing
samples did not establish reliability for every submission. Raised the completion
ceiling from 512 to 2,048 tokens while retaining the 30-second timeout, explicit
JSON mode, strict validation and zero automatic retries. Added a specific,
sanitized output-limit error for both SDK-raised and metadata-reported truncation.
No partial response is saved or published.

At the user's request, the prompt now explicitly requires succinct, professional,
JSON-only output with short exact quotations, no paraphrasing or commentary.
The larger ceiling is headroom, not a requested response length.

**64 offline backend tests passed.** One live conflict browser check passed in
**5,248 ms**, including saved-result reload/readback:
`5a9bceca-6a3e-4e96-8a00-59be9409821a`.
Budget remained unknown, red wine was preserved and status was RequestConfirmed.
The port-8000 preview was restarted with these changes. This is representative
verification, not a guarantee that a provider can never truncate again.

## Team integration and UC-M1-02 — 28 October 2026 (Sydney)

Fetched all published branches and retained contributor history. Lio's profit
margin work was already main. PR #2 integrated Cedar's latest unified-UI branch
(which contains the earlier M2 branch), Avan's budget/availability branch, and
Lio's inventory-contract proposal. Verified main at `987d0aa`; all six earlier
contributor/integration remote branches are ancestors. Main's pull-request-only
rule remains active. No remote branches were deleted.

Integration baseline: **159 backend tests, seven browser tests, production build
passed**. No model calls. Existing modules are integrated as source; pending UI
and service connections are labelled rather than claimed complete.

UC-M1-02 on `feat/m1-current-stock` implements report §6.1.2 and §10.2 through
InventoryQueryService / InventoryProcurementAgent. Operator token authentication
precedes lookup; browser-supplied roles are rejected. The service opens SQLite
read-only, preserves current/stale evidence, reports missing/incomplete/outage
results explicitly, and retains the single-ID adapter used by Cedar's code.
Startup seeds labelled prototype inventory once and never refreshes timestamps
on existing data. Lookup performs no other business action or model call.

Final verification: **177 backend tests, eight browser tests and the production
build passed**. Tests cover exact values, zero quantity, mixed invalid/valid IDs,
deduplication, missing/negative/naive/future fields, stale boundary, unavailable
source, denied actor, missing/wrong operator token, role spoofing, empty selection,
unchanged SQL dumps, and 95th percentile of 20 local six-product lookups below
two seconds. Browser verification covers the authenticated form, denial,
found/stale/not-found results, mobile layout and clearing secrets on reload.

Working checkout: `/home/jmos0905/MBSE/team-workspace`. Existing original source,
databases and credentials in the parent folder were preserved. A separate ignored
`.env` configures fixture preview and a private operator token. It is excluded
from Git along with databases, dependencies and screenshots. No university model
calls were used in this integration or UC-M1-02 work.

## Connected team workflows — 28 October 2026 (Sydney)

UC-M1-02 merged to main through PR #3 (`24800b4`). Branch
`feat/connect-team-workflows` adds API/UI adapters for Avan's budget and
availability modules, Lio's profit margins, and Cedar's restocking against the
shared SQLite source. The user agreed AUD for catalogue/unqualified dollar
budgets; recognized explicit foreign currencies fail without FX conversion.

Final checks: **190 backend tests and ten Playwright tests passed; production
build passed.** Tests exercise the complete saved-request → recommendations →
budget → stock availability flow; operator availability; connected restocking;
profit figures and missing-cost coverage; denied operator access; source outages;
future sales exclusion; missing budget/no matches; unsupported currencies; and
unchanged SQL data through read-only operations. No university model calls.

Cross-feature browser tests exposed duplicate React sibling keys that produced
duplicate recommendation panels; keys now identify both feature and request.
A manual Start a new request action clears a failed/pending browser attempt;
this does not introduce automatic retries or new model requests.

Source/diagram checks: report §6.2.1, §10.4/10.6/10.7/10.8 and Figures 14/16,
in addition to the earlier shared-model and stock references. The app still uses
prototype data, a limited rule recommendation matcher and localhost-only access.
Low-stock alerts, reorder suggestions and demand trends remain unimplemented.
`docs/team-status.md` provides the full use-case and contributor overview.

## Qwen recommendations, LangGraph and local fallback — 28 October 2026

Implemented real Qwen catalogue ranking with strict product/need/fact validation,
durable at-most-once recommendation reservations, saved-result reuse, and persisted
Customer → Inventory and Business Insights → Inventory LangGraph traces. Capture
remains a separate use case. Optional quota fallback uses the server's existing
Qwen2.5-1.5B-Instruct Q4_K_M through llama.cpp, bound to localhost with two CPU
threads and one inference slot. No weights/runtime were downloaded or committed.

**220 backend tests passed**, with mocked/fixture providers and intercepted SDK
requests; production TypeScript/Vite build and **11 fixture browser tests passed**.
Coverage includes concurrency, restarts, failed/pending reservations, quota-only
fallback, provider provenance, shared university cap, saved no-match, changed
prices, offline revalidation, actual typed handoffs and protected business traces.
The React review checked hook dependencies, asynchronous restore guards, accessible
labels/statuses and stable product keys. These checks do not establish AI accuracy.

University checks used **seven application attempts**: three capture/recommendation
pairs and one schema-rejected capture request. One recommendation truncated; a
second failed validation before raw retention was added. The third response had
valid products/facts but unsupported uncertainty labels. The transport now sends
only legacy `max_tokens` (the proxy rejected both token fields together), with
2,048 capture / 4,096 recommendation ceilings, temperature 0.2, JSON mode and zero
automatic retries. Unknown uncertainty references are withheld; invalid product,
need or fact references still reject the result.

The retained third university response was revalidated explicitly offline after
that validator fix, with **zero additional model calls**. Request
`302cdd78-b3c5-4eff-818b-b77626d663fd` then passed the live-browser cache-only
workflow, repeated workflow, GET readback and reload check with **zero new university
attempts** (saved workflow `7816bbf2-cc2f-481d-a2ca-a615a987f229`). Outcome was
partial because the catalogue cannot establish occasion/party-size suitability.
This verifies actual university-generated recommendations plus reuse; a fresh
generation after the final prompt/validator changes was not retested against the
university. The counter is not a university token/balance measurement.

Actual local inference passed a JSON transport check and grounded recommendation
check (one direct recommendation took 9.61 seconds). An isolated backend with
`LIVE_DAILY_LIMIT=0` then completed actual local capture → recommendations → budget
→ inventory → saved trace, followed by cached rerun: **39.8 seconds**, **zero
university calls**, request `a3d110cd-d8e3-4780-b090-ed0020396871`, workflow
`df0a04bf-aa7e-4029-ae15-6c95852f778a`. Earlier local captures paraphrased numbers
and were rejected; removing numeric examples from the extraction prompt produced
source-valid output. The successful sample still omitted an explicit constraint,
so complete extraction quality is not established. The full local sample does not
meet the provisional 10-second target. Both providers retain the same validators;
local failure never silently becomes fixture output.

The owner's private preview enables local fallback while retaining the university
as primary. The checked-in example leaves it disabled for teammates. Explicit
quota codes or the application cap select fallback; authentication, connection,
generic rate-limit and validation failures do not. No model calls occur on reload
or saved-result reads. A quota rejection can cause one university request followed
by one local request in the same reserved operation; neither provider is retried.

Agile preparation includes a 14-item importable backlog and blank meeting-log
template linked to the owner's existing KAN board. The Atlassian connector still
returns an access/service error; no issues, sprint, historical meeting records or
burndown data were created. Alert, reorder and demand UCs remain unimplemented.

## Unlimited university primary and outage fallback — 28 October 2026

PR #5 was merged to main at the owner's request. The subsequent policy change
sets `LIVE_DAILY_LIMIT=unlimited` by default and in the owner's private preview.
Status returns a null application cap and React explicitly says there is no daily
application cap. This cannot remove university-enforced quotas. Numeric caps are
still opt-in for isolated tests; no cap automatically selects local Qwen.

Every new operation tries university first. Connection failures, timeouts, HTTP
408/429, 5xx server responses or explicit quota rejection permit one local
fallback. Authentication/permission errors without a quota code, wrong endpoints,
request schema failures, truncation and invalid output do not. The next operation
tries university again; historical day-long quota-state rows are ignored. Saved
recommendations are still reused and neither provider is automatically retried.

**230 mocked/fixture backend tests passed**, including unlimited operation above
the old 50-attempt cap, ignoring old quota latches, one-shot outage fallback,
university recovery on the next operation, terminal local failure and no fallback
on invalid output. Production build and **11 fixture browser tests passed**.
Outage scenarios were mocked; the live university tunnel was reachable.

A **fresh live React test passed** with actual university capture and recommendation
generation, budget filtering, Customer → Inventory → Customer handoffs, saved
trace, cached repeated workflow, GET readback and browser reload. Request
`1cca1bbd-aa78-40ff-9c64-9bab0b5ef659`; saved workflow
`3e6ec5f7-93d7-48a5-a5dd-2609394bf307`. Exactly **two new university application
attempts** were recorded; repeated workflow and reload added zero. Both operations
used university Qwen. Outcome was partial because catalogue occasion/party-size
suitability is unknown. This resolves the earlier fresh-generation verification
gap for this representative input, not arbitrary-input model accuracy.

The real preview's Business Insights restocking form also passed an authenticated
browser check: product-003 produced a presented result and visible Business
Insights → Inventory → Business Insights trace, workflow
`13f72b38-59b1-4eab-8fc8-6263c7b65c7e`. University usage did not increase. The
private operator token was supplied only through process memory, not output.

## Jira contribution backlog — 28 October 2026

The connection authorized for the university project successfully accessed Jira;
the earlier connection routed to another linked account. Read all existing issues,
board configuration, issue types, assignable users and sprint support first.
Created KAN-4 through KAN-20 from the 17-item evidence-based backlog. Subsequent
JQL readback verified all summaries/statuses: 10 Done, 2 In Review, 4 To Do,
1 In Progress. Original report ownership and extra integration contributions are
recorded with commit/PR links; retrospective tracking is explicitly labelled.
Only Jose was returned as an assignable human, so other members were credited
in descriptions/labels without guessing Jira identities. No estimates, historical
dates, meetings or worklogs were fabricated. The issue map is in docs/agile/.

The user confirmed KAN-1/2/3 are default placeholders and requested deletion.
The connected tool catalog exposes no issue-deletion operation; they remain
pending UI deletion. Board 2 is team-managed and reports that it does not support
sprints. Its space admin must enable Sprints/Reports in the Jira UI; this toggle
also has no connected operation. KAN-17 records the remaining setup steps. No
sprint or burndown completion is claimed.

## Remaining core completion — 28 October 2026

Merged Avan's newer contract/API branch into the completion branch, preserving
both author commits. Resolved the shared-main conflict by keeping the integrated
application. Decimal budget results and explicit Stale availability evidence are
retained; InventoryQueryService remains the freshness authority. Member 4 HTTP
aliases now use saved request IDs or operator-authorised source product IDs;
browser-supplied prices, stock snapshots and roles cannot establish authority.

Implemented UC-M3-01 low-stock alerts, UC-M5-01 reorder suggestions and UC-M5-02
demand trends, their authenticated React forms and persisted LangGraph reports.
The owner approved reorder target = twice threshold and adjacent equal-duration
completed-period demand comparison with positive/negative/zero units-change
classification. Source diagrams and exact decisions are in
`docs/remaining-core-acceptance.md`. The recommendation acceptance review adds an
occasion-only no-match check and rejects invented occasion evidence. Absent
suitability/serving metadata remains an explicit data limitation.

**262 backend tests passed**, including inherited contributor tests and additional
rule, source, authorization, trace, read-only storage and no-fabrication cases.
**12 fixture browser tests passed**, including all three new forms, wrong-token
denial, real source quantities, reorder 17, stale-evidence withholding, historical
demand and mobile layout. Production TypeScript/Vite build passed. No new model
calls were made by these checks.

The actual port-8004 preview passed browser checks against its retained SQLite
prototype source: low-stock alert workflow `4bf3229c-e54d-44cf-b552-7af66e4eac68`,
reorder `dfa14f7a-fbbb-4639-a620-164ffa97db8b` and demand
`46794f15-73e2-4998-8a5f-fd66759149b5`. Stock 3/threshold 10 produced suggestion
17; Shiraz September quantities 4 versus prior equal-period 2 classified increasing.
All added **zero model calls**. The saved actual university recommendation request
`1cca1bbd-aa78-40ff-9c64-9bab0b5ef659` passed cache-only customer graph/readback/
reload again with workflow `ce16a121-b5bc-43c1-bf6e-8ef67f02359d`, adding zero calls.
This is reuse of earlier real Qwen output, not fresh inference on this revision.

All ten core functions now have connected implementations. Formal team acceptance,
current clean Canvas-package deployment rehearsal, contribution statements and
genuine Agile meeting/sprint evidence are still required. Original report owners
retain ownership; the gap implementation here is Jose's authorized assistant work,
not newly claimed authorship by Cedar, Lio, Avan or Lira.

PR #8 merged the completed features into main; Avan's latest branch is an
ancestor of main. Jira KAN-6/8/12/13/20 were updated with evidence and moved to
Done. Readback verified 15 Done, 1 To Do and 1 In Progress among the 17 real items.
The owner enabled Sprints; automatically created sprint 1 was configured as
**Stage 2 final validation**, with KAN-16/17 only and planned end 1 November 2026
23:59 Australia/Sydney. It remains future pending team-agreed estimates and actual
start time. No historical sprint progress or estimates were fabricated.
