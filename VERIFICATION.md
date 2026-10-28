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
