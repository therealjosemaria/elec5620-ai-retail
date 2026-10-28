# Jira contribution evidence — 28 October 2026

Target: [KAN board 2](https://mbse5620.atlassian.net/jira/software/projects/KAN/boards/2).
Jira access is now working. KAN-4 through KAN-20 were created and their statuses
verified: 10 Done, 2 In Review, 4 To Do and 1 In Progress. See `jira-issue-map.json`.
The owner confirmed KAN-1/2/3 were default placeholders and requested deletion;
they still require removal in Jira because the connector has no deletion tool.
Sprints are disabled and require a space-admin UI toggle before sprint setup.

Authority: submitted Stage 1 §6 and §10.1–10.10 with corresponding diagrams.
Names identify report ownership or evidenced contribution, not Jira assignments.
Match actual Jira accounts before assigning anyone.

## Core use cases

| Item | Contributor | Evidence | Suggested state |
| --- | --- | --- | --- |
| UC-M1-01 Submit Product Assistance Request | Jose | [69f1646](https://github.com/therealjosemaria/elec5620-ai-retail/commit/69f1646), capture tests and live browser results; fresh sample passed 28 October | Done for implemented scope; arbitrary-input AI accuracy remains a limitation |
| UC-M1-02 Check Current Stock | Jose | [PR #3](https://github.com/therealjosemaria/elec5620-ai-retail/pull/3); authorised typed lookup, timestamps and operator UI | Done for prototype scope |
| UC-M2-01 Receive Drink Recommendations | Cedar; Jose integration/Qwen | Cedar [2893721](https://github.com/therealjosemaria/elec5620-ai-retail/commit/2893721); [PR #5](https://github.com/therealjosemaria/elec5620-ai-retail/pull/5) adds Qwen ranking/cache; fresh university browser sample passed | In Review: occasion/party-size suitability unresolved without metadata; team acceptance needed |
| UC-M2-02 Review Restocking Priorities | Cedar; Jose integration | Cedar 2893721; [PR #4](https://github.com/therealjosemaria/elec5620-ai-retail/pull/4) connects SQLite/UI; PR #5 adds Business Insights–Inventory graph; actual preview result presented | Done for evidenced prototype scope, retaining data limitations |
| UC-M3-01 Receive Low-Stock Alert | Lio, report owner | No implementation found in fetched branches; placeholder only | To Do; check unpushed work |
| UC-M3-02 Review Profit Margins | Lio; Jose integration | [ec36520](https://github.com/therealjosemaria/elec5620-ai-retail/commit/ec36520), 870261b data and 5bfa980 performance check; PR #4 connects UI/API | Done for prototype scope with explicit missing-cost coverage |
| UC-M4-01 Apply Budget Filter | Avan; Jose integration | [8fe8c3f](https://github.com/therealjosemaria/elec5620-ai-retail/commit/8fe8c3f); PR #4 connects saved candidates and AUD handling | Done on main; newer branch revisions need review |
| UC-M4-02 Check Product Availability | Avan; Jose integration | [bd9c63b](https://github.com/therealjosemaria/elec5620-ai-retail/commit/bd9c63b); PR #4 connects InventoryQueryService/UI | Done on main; newer branch revisions need review |
| UC-M5-01 Review Reorder Suggestions | Lira, report owner | No implementation found in fetched branches; placeholder only | To Do; check local/unpushed work |
| UC-M5-02 Detect Demand Trends | Lira, report owner | No implementation found in fetched branches; placeholder only | To Do; check local/unpushed work |

These are present-day tracking suggestions, not formal acceptance or historical
start/finish dates. Missing published commits do not prove a member did no work.

## Shared contributions and remaining work

| Item | Contribution/evidence | Suggested state |
| --- | --- | --- |
| Shared development foundation/onboarding | Jose: React/FastAPI/LangGraph/SQLite, contracts, locked dependencies, README, tests and clean-source rehearsal; 69f1646 and VERIFICATION.md | Done for foundation; final rehearsal separate |
| Shared three-agent frontend | Cedar: [7acbe45](https://github.com/therealjosemaria/elec5620-ai-retail/commit/7acbe45), catalogue/navigation/responsive workspaces; integrated in [PR #2](https://github.com/therealjosemaria/elec5620-ai-retail/pull/2). Jose connected forms in PR #4 | Done for implemented features; placeholders labelled |
| Persist Qwen recommendations/prevent duplicate calls | Jose: PR #5; reservations, cache, grounding, failures, restarts and concurrency | Done; fresh university sample passed |
| Verify three-agent LangGraph communication | Jose: PR #5 and [PR #6](https://github.com/therealjosemaria/elec5620-ai-retail/pull/6); actual Customer–Inventory and Business Insights–Inventory traces visible in React; profit reads sales directly | Done for implemented paths |
| Review Avan's latest Member 4 integration | Avan: [1a9f5f8](https://github.com/therealjosemaria/elec5620-ai-retail/commit/1a9f5f8) and [0c85855](https://github.com/therealjosemaria/elec5620-ai-retail/commit/0c85855) on `feat/avan-budget-availability`; Decimal/stale-status alignment and extra API/tests are not ancestors of current main | In Review; reconcile endpoints, authorisation and contracts before merge; new branch tests not run in this audit |
| Clean deployment/joint demo rehearsal | Earlier foundation source-only rehearsal exists; current complete source, Canvas download/deploy and contribution statement still need team rehearsal | To Do |
| Jira sprint/real Agile meeting evidence | KAN-17 tracks actual setup. Real backlog created; Sprints disabled; no genuine meeting attendance, estimates or historical burndown supplied | In Progress; space admin enables Sprints/Reports, team supplies real meetings/estimates |

Main includes PRs #2–#6. Current checks: 230 mocked/fixture backend tests,
11 browser tests and production build passed. Fresh university capture and
recommendations plus customer graph used two attempts; cached repeat/reload and
actual Business Insights handoff added zero. See `../../VERIFICATION.md` for IDs
and exact limitations.

## Remaining Jira setup

1. Existing issues, statuses, assignable users, board configuration and sprint
   support were inspected. Enable Sprints and Reports in the space settings UI.
2. Use the saved issue map to update existing records and create only missing items.
   Include both original author and integration credit in the description.
3. Add evidence links and present-day notes; do not invent historical worklogs,
   completion dates, meetings, votes or estimates.
4. Use actual available transitions and verify accounts before assigning anyone.
5. Enable sprint/backlog/report support for the assessed burndown. Track from the
   actual sprint start, using team-agreed remaining estimates. Reported source
   deadline is 1 November 2026, 11:59 PM; confirm Canvas/demo timing before dates.
6. Record actual meetings using `meeting-log-template.md`; none is inferred from
   chat or Git history.
