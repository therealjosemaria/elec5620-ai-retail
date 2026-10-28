# ELEC5620 — shared development foundation

**Team integration:** all published contributor branches as of 28 October 2026
are integrated into `main` through PR #2; PR #3 adds UC-M1-02 stock lookup.
PR #4 connects budget, availability, profit and restocking modules to the shared
frontend. PR #5 adds saved Qwen recommendations, LangGraph handoffs and optional
local Qwen fallback. University usage has no application daily cap; local Qwen
handles service unavailability. See the [full UC/contribution status and joint test walkthrough](docs/team-status.md).

This guide covers first setup, seeing React, daily development, live-model access,
tests and the team Git workflow. Start with fixture mode; no API key or VPN is
needed for the sample demonstration.

**Guide:** [Setup](#requirements-and-setup) ·
[Live model](#live-university-model--opt-in) ·
[Tests](#tests-zero-university-calls) ·
[Shared contracts](#project-map-and-feature-boundaries) ·
[Git workflow](#git-workflow) · [Troubleshooting](#troubleshooting) ·
[Merge/submission checks](#before-merging-or-submitting) ·
[Limitations](#known-limitations)

Includes **UC-M1-01 / M1-AR-01: Submit Product Assistance Request / User Need Input**.
React → FastAPI → LangGraph extraction + validation → SQLite → React readback.
Member 2 contributed catalogue recommendations and restocking priorities. Live
recommendations now use Qwen; fixture mode retains the labelled phrase matcher.
See [agent workflows](docs/agent-workflows.md) for generation, cache and communication
behaviour, and [Member 2 implementation](docs/member2-implementation.md) for the
original contribution.

The unified [three-agent interface](docs/unified-interface.md) now opens on a
catalogue landing page. Use **Customer assistant**, **Inventory & procurement**
and **Business insights** in the navigation. All ten core use cases now have
connected implementations; prototype data and AI limitations remain explicit.

For stock lookup, set a private `OPERATOR_TOKEN` in `.env`, restart FastAPI,
open **Inventory & procurement**, select products and enter that token.
Lookup makes no model calls. See the stock guide for sample data, stale records,
the read-only API and trusted agent access. The token is never committed.

## Requirements and setup

### Install prerequisites

Install Git, Python **3.13**, and Node **22 LTS (22.12 or newer in that major)**.
Use stable releases, not alpha/beta/RC versions.
Official downloads: [Python](https://www.python.org/downloads/),
[Node.js](https://nodejs.org/en/download), [Git](https://git-scm.com/downloads).

The commands below assume **macOS/Linux with a POSIX shell**. On Windows, use
**WSL2 and a Linux terminal**, installing Git/Python/Node inside WSL. Do not mix
Windows and Linux dependency directories. Native PowerShell is not covered by
the current browser-test launcher.

Check:

```bash
git --version
python3.13 --version
node --version
npm --version
```

Debian/Ubuntu may additionally need the matching Python venv package.
No separate SQLite server, Docker, Vercel or Tailscale installation is required.
Internet is needed for the initial dependency downloads.

### Clone and create a feature branch

After the foundation has been merged:

```bash
git clone https://github.com/therealjosemaria/elec5620-ai-retail.git
cd elec5620-ai-retail
git switch main
git pull --ff-only origin main
git switch -c feat/your-name-your-use-case
```

Replace the branch name with a descriptive, unique name. “Repository root” below
means the folder containing this README, `backend/`, `frontend/` and the Python
requirements. If GitHub gives you only the old README, wait for the foundation
merge or ask which branch contains it.

### Install dependencies

Use Python 3.13 and Node 22.12+ (tested with Node 22.22).
From this directory:

```sh
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pip check
test -f .env || cp .env.example .env
chmod 600 .env
cd frontend
npm ci
npm run build
cd ..
MODEL_MODE=fixture python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Select **Customer assistant**, click **Use sample**,
then **Capture and save**.
The UI performs a separate database GET after saving and restores the saved record after reload.
Expand **Inspect stored record** to see the database representation.
Data lives in `data/retail.sqlite3`, excluded from source control.

After capture, choose **Run agent workflow** to run recommendations → budget →
Inventory Agent availability. Expand **Agent communication** to inspect actual
handoffs. Repeated runs reuse saved recommendations and refresh stock evidence;
capture alone remains UC-M1-01. Individual use-case buttons are also available.

Expect budget `30`, party size `6`, preferences/constraints, and status
`RequestConfirmed`. Expand **Inspect stored record** to compare normalized values
and original evidence. Stop the server with **Control-C**; data remains on disk.

The explicit `MODEL_MODE=fixture` launch setting overrides `.env` for that process.
Do not overwrite an existing `.env` or use `sudo pip install`.

Useful addresses on the computer running the backend:

| Address | Purpose |
| --- | --- |
| `http://127.0.0.1:8000` | Built React UI |
| `http://127.0.0.1:8000/docs` | Interactive FastAPI documentation |
| `http://127.0.0.1:8000/api/status` | Mode and local attempted-call count |
| `http://127.0.0.1:8000/openapi.json` | Machine-readable API schemas |

Using “Try it out” on POST `/api/requests` in live mode can consume a model call.

Default **fixture mode makes no external AI calls**. It accepts only the displayed
sample and returns a fixed extraction. It verifies plumbing, NOT model capability.

For frontend development, run FastAPI as above and `npm run dev` in `frontend`;
visit http://127.0.0.1:5173. Vite proxies `/api` to FastAPI.
Keep services on localhost. For access from another computer, use an SSH tunnel:
`ssh -L 8000:127.0.0.1:8000 your-server`, then open localhost:8000 on that computer.
This MVP has no authentication and must not be exposed publicly.

### Daily development: two terminals

Terminal 1, repository root:

```bash
source .venv/bin/activate
MODEL_MODE=fixture python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2, repository root:

```bash
cd frontend
npm run dev
```

Open **http://127.0.0.1:5173** for hot-reloading frontend changes. If Vite prints
another port, use that URL. Port 8000 serves the last built frontend; it does not
automatically rebuild your React edits. Rebuild before production-preview/browser tests.
Stop both processes with Control-C.

If your browser is on another machine, its `127.0.0.1` is not the server. Use a
local SSH forward as described above; do not expose the unauthenticated app publicly.

## Live university model — opt in

Create a local `.env` using the variable names in `.env.example`:
set `MODEL_MODE=live` and set your `ELEC5620_API_KEY` privately. Restart FastAPI.
Do not place keys in React, source control, screenshots, or the submission package.
The backend connects to the guide's `campus-qwen` endpoint.
It needs university-network/VPN routing; Tailscale alone does not establish that route.

Use an individual university key when available. A local `.env` should contain:

```dotenv
MODEL_MODE=live
ELEC5620_API_KEY=REPLACE_PRIVATELY_WITH_YOUR_KEY
ELEC5620_BASE_URL=http://10.167.60.148:8000/v1
LIVE_DAILY_LIMIT=unlimited
DATABASE_PATH=data/retail.sqlite3
```

Do not prefix the key with `Bearer`. Do not place it in a frontend `VITE_` variable.
Do not use a Mimecast-protected URL or the VPN gateway as the model base URL.

Follow the university connection guide; if needed, connect Cisco Secure Client
to **`vpn.sydney.edu.au`** on the machine running FastAPI. Complete MFA yourself.
Check connectivity without a key or prompt:

```bash
curl --noproxy '*' --connect-timeout 5 --max-time 10 \
  -i -X POST http://10.167.60.148:8000/v1/chat/completions \
  -H 'Content-Type: application/json' -d '{}'
```

The observed response is `422` with `messages Field required`. This demonstrates
endpoint reachability, not successful key authentication. Timeout means routing
or connectivity trouble. `/v1/models` previously returned 404; don't use that
route alone to diagnose an outage.

Stop the fixture backend and deliberately start live mode:

```bash
source .venv/bin/activate
MODEL_MODE=live python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Confirm **Live · campus-qwen** in React before a single planned test.
For `I want red wine under $30.`, expect captured preference/budget and missing
party size/occasion/constraints. This consumes a real model attempt.
Restart using `MODEL_MODE=fixture` to return to zero-call development.
Changing `.env` alone does not update an already running production process.

**Owner-specific remote setup:** the Pi may use `http://127.0.0.1:18000/v1`
through a reverse SSH tunnel on a Mac. That depends on the Mac staying awake,
SSH staying open and the required network connections remaining active.
Teammates running locally should use the direct university URL, **not port 18000**.

We do not yet know the university's numerical quota. Local safeguards:

- There is **no application daily cap** by default (`LIVE_DAILY_LIMIT=unlimited`).
  University-enforced limits still apply; attempts remain counted in SQLite.
- Capture and recommendations each reserve one operation per request ID; duplicate
  submissions and saved recommendation reads do not regenerate output.
- No SDK retries, no graph retry policy, no automatic JSON repair calls.
- Input limited to 1,500 characters; completion ceilings are 2,048 tokens for
  capture and 4,096 for recommendations; university timeout is 30 seconds.
  The ceiling is not a fixed token spend. Truncated responses are rejected with
  an explicit output-limit error and no automatic retry.
- Failed calls remain counted. A numeric cap can be set explicitly for isolated tests.
- The UI shows attempted live calls; it is not a provider balance/token dashboard.
- Preserve the database for saved results and usage history. Calls made through
  other apps/team members are not counted here.

If a timeout or malformed response occurs, no CustomerRequest is saved and an error
is shown. Reusing that attempt ID never calls the model again. Editing the input
creates a new attempt; do so deliberately since it may consume another call.
The attempt ID survives reload in the same tab. A different tab/browser session
or edited input creates a new ID; after an uncertain network failure, check the
saved record/database before submitting again.

The optional [local Qwen fallback](docs/local-qwen-fallback.md) uses an existing
localhost service when university Qwen is unreachable, times out, returns a server
error or rejects a call for rate/quota capacity. New operations always try university
first. Start the runtime and enable it privately;
teammates can leave it disabled. Records show the actual provider/model. Local-only
operations do not consume university allowance. Failed validation never silently
becomes a fixture result. See [Agile setup](docs/agile/README.md) for the team's
Jira board, prepared backlog and meeting-log template.

## Extraction contract

`needs` follows the Stage 1 `CustomerRequest`: optional decimal `budget`,
optional integer `party_size`, optional `occasion`, lists of `taste_preferences`
and `constraints`, and a request `status`. Decimal values use JSON strings to
preserve precision. `evidence` retains the original quoted wording, e.g. `under $30`.
No currency or per-person/per-bottle basis is assumed. `missing_fields` is derived
in code. Original text, mode, UUID and UTC timestamp are retained.
See [Stage 1 alignment](docs/stage1-alignment.md) for source mappings, supported
normalization and the remaining inventory-interface discrepancy.

Validation rejects unexpected keys, wrong types, malformed JSON and values not
present in the source. It cannot prove semantic accuracy, completeness or correct
ambiguity handling: those require live model evaluation. An all-unknown result is
allowed for unusable/ambiguous content; the UI identifies missing/unresolved fields.

## Tests (zero university calls)

From the repository root:

```sh
.venv/bin/python -m pytest -q
cd frontend
npm run build
npx playwright install chromium
npm run test:e2e
```

Backend tests inject fake extractors. Browser tests start a separate fixture-mode
server on port 8001 with `data/e2e.sqlite3` and exercise the real compiled React UI,
API, LangGraph, persistence and reload. Browser downloads need internet.
Do not run against a live-mode server; the test config starts its own.

The current combined baseline is recorded in `VERIFICATION.md`.
See `VERIFICATION.md` for scope and evidence. Port 8001 must be free. Browser tests always
start their own fixture backend, even if your development `.env` says live.
They use the compiled React build, not the Vite development server.

On Linux, if Chromium reports missing system libraries, follow Playwright's
printed dependency instructions; installing system packages may require admin
approval. Backend tests inject fake extractors or intercept the SDK HTTP request.
They do not establish real model quality.

Direct inspection (optional, if the sqlite3 CLI is installed):

```sh
sqlite3 data/retail.sqlite3 'SELECT request_id, needs, missing_fields, mode FROM customer_requests;'
```

## Scope and reproducibility

UC-M1-01 is implemented; Member 2 prototype coverage and integration limitations
are documented separately. The user-confirmed submitted report §5 assigns each
member two core features; it does not make optional features MVP requirements.
SQLite uses Python's standard library, avoiding an unnecessary ORM.
`requirements.txt` and `frontend/package-lock.json` pin the tested dependency resolution.
`requirements.in` describes allowed stable release families; do not upgrade automatically
before the demo. No alpha/beta/RC dependencies are intentionally selected.
The university proxy must be live-verified separately before claiming AI end-to-end success.
Existing `team-setup/` files are untouched historical planning material.

## Project map and feature boundaries

| File | Purpose |
| --- | --- |
| `backend/main.py` | API, graph, provider adapter and SQLite persistence |
| `backend/capture.py` | Evidence validation and normalization |
| `backend/models.py` | Shared Stage 1 domain models |
| `backend/interfaces.py` | Inventory service outline, not a stock implementation |
| `backend/retail_data.py` | Shared products/sales tables, prototype data and loaders |
| `backend/profit_margin.py` | UC-M3-02 profit margin calculation |
| `backend/low_stock.py` | UC-M3-01 low-stock alert decision (Figure 20 states) |
| `backend/recommendations.py` | UC-M2-01 conservative catalogue matcher |
| `backend/restocking.py` | UC-M2-02 authorised evidence ranking |
| `backend/member2_demo.py` | Isolated, labelled restocking fixtures |
| `frontend/src/Member2.tsx` | Recommendation and sample restocking UI |
| `frontend/src/main.tsx` | Request entry and saved-record UI |
| `tests/` | Backend/schema tests |
| `frontend/e2e/` | Browser tests |
| `docs/stage1-alignment.md` | Report-to-code mappings and gaps |
| `docs/uc-m3-01-low-stock-alert.md` | UC-M3-01 states, decisions and acceptance |
| `docs/uc-m3-02-profit-margin.md` | UC-M3-02 decisions, shared data tables and acceptance |
| `VERIFICATION.md` | Verification evidence and limitations |
| `AGENTS.md` | Standing project instructions |

**Connected:** all ten core functions: request capture, stock lookup, Qwen
recommendations, restocking priorities, low-stock alerts, profit margins, AUD
budget filtering, availability, reorder suggestions and demand trends.
[Remaining-core acceptance](docs/remaining-core-acceptance.md) records source
mappings, approved reorder/trend rules and evidence limits. [Team status](docs/team-status.md)
distinguishes original contribution and gap-completion work.
Shared products, sales, inventory and inventory-item tables contain labelled
prototype data. Operator endpoints require the private token; the app remains
localhost-only with no public account system.

### Always read Stage 1 first

Use the submitted Sequence Fixed report, not Critical Fixes. See [AGENTS.md](AGENTS.md).
Consult the requirement, use case and diagrams before adding behaviour or asking
the team to decide something. Where diagrams omit details, follow the detailed
written requirement while preserving the architectural boundaries.

Use `backend.models` instead of defining competing versions of shared entities.
CustomerRequest represents customer needs. Product holds catalogue attributes.
InventoryItem holds quantity/threshold/timestamp and references a Product and
the store-level Inventory. SalesRecord holds completed-sales evidence.
Schemas alone do not enforce database foreign keys or the one-inventory rule.

Customer/Business Insights agents must obtain inventory through
`InventoryQueryService`, not direct SQL. The implemented contract includes trusted
requester context and found/not-found/stale/error results, plus a compatibility
single-ID overload. See the [stock reference](docs/uc-m1-02-stock-lookup.md).

### Current API contract

POST `/api/requests` accepts a valid UUID `request_id` and a `text` string.
Generate a fresh UUID per new intentional attempt; keep the same ID for duplicate
transport submissions. GET `/api/requests/{request_id}` reads a saved request.
Both return metadata, normalized `needs`, original `evidence`, and `missing_fields`.
Use `/docs` or `/openapi.json` for full typed definitions.

The SQLite `needs` column currently stores **evidence**, while API `needs` is
normalized on read. This preserves legacy records without re-calling the model.
Do not assume the raw database JSON has the same shape as the API response.

### Adding your use case

1. Read its submitted requirement, main flow, exceptions and diagrams.
2. Identify the assigned agent, required inputs and outputs.
3. Create a focused branch from updated `main`.
4. Reuse shared schemas and coordinate any shared interface changes.
5. Add feature code in focused modules rather than duplicating the application.
6. Add mocked success/failure tests and the necessary UI/API integration.
7. Run all existing tests before proposing a merge.
8. Update the relevant docs and submit a pull request.

Feature ownership is not exclusive agent ownership: several members contribute
to the same agent. Coordinate edits to shared files, especially `main.py`,
`models.py` and the frontend entry point.

## Git workflow

`main` should remain runnable. Use branches per feature/change, not permanent
independent copies of the project. With a clean working tree:

```bash
git switch main
git pull --ff-only origin main
git switch -c feat/your-name-feature
```

Commit existing feature work before switching branches; don't discard it to
resolve synchronization problems.

Before committing:

```bash
git status --short
git diff --check
git diff
git check-ignore .env data/retail.sqlite3 .venv/ frontend/node_modules/
```

The ignore check should list those local-only paths. Review every staged file.
Stage only files you intend to include; for example:

```bash
git add backend/capture.py tests/test_models.py
git diff --cached
git commit -m "Describe the feature or fix"
git push -u origin HEAD
```

Open a pull request against `main`. Include the use-case ID, changes, tests run,
live-call usage, contract changes and known limitations. Have a teammate review
before merging.

To incorporate newer changes into an existing feature branch:

```bash
git fetch origin
git merge origin/main
```

Resolve conflicts deliberately and rerun tests. Never force-push `main` or use
`git reset --hard` to discard someone else's work.
GitHub collaborator access is required to push. GitHub authentication is separate
from your university model key.

The repository's `main` branch has a pull-request-only rule with no bypass list.
Follow the review workflow; this README does not configure CI.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Python command missing | Install Python 3.13; verify its executable/version. |
| `No module named fastapi` | Activate `.venv` and install requirements using that Python. |
| venv/ensurepip failure | Install your Linux distribution's matching venv package. |
| npm engine warning | Use the documented Node 22 version. |
| `npm ci` lockfile mismatch | Check branch/changes; don't delete the lockfile as a workaround. |
| Port 8000 gives UI 404 | Build frontend, then restart FastAPI; static mount is detected on startup. |
| UI shows old code | Use Vite on 5173 or rebuild the production UI. |
| Backend unavailable | Check server terminal and `/api/status`; Vite expects backend port 8000. |
| Port already in use | Stop your own old process. Don't kill unrelated server apps. |
| Fixture rejects arbitrary input | Expected: use the sample or opt into live mode. |
| Live submit disabled | Set the backend key privately and restart. |
| `.env` mode ignored | An explicit launch/shell environment setting overrides `.env`. |
| Proxy timeout | Check VPN/routing on the backend machine, not just another computer. |
| Extraction returns 502 | Provider/authentication or output-validation failure; don't retry repeatedly. |
| Duplicate returns 409 | Pending/failed/conflicting attempt; automatic retry is intentionally prevented. |
| Application returns 429 | Local daily cap reached; switch to fixture tests. |
| Old saved record appears | Browser retains its UUID; check the database/mode without deleting quota history. |
| Browser tests fail to launch | Build React, install Chromium, free port 8001 and inspect printed errors. |
| Owner's SSH tunnel stops | Keep the Mac awake and tunnel open; normal local setups don't need it. |

Report OS, Python/Node versions, branch/commit, command and sanitized error.
Never post `.env`, authentication headers, keys or credential screenshots.

## Before merging or submitting

- Install from a clean source copy without reusing `.venv`, `node_modules` or `dist`.
- Run backend tests, build and fixture browser tests.
- Review staged files for secrets, databases, generated artifacts and private documents.
- Include `.env.example`, not `.env`; don't upload course PDFs/screenshots containing keys.
- Record OS and exact verification scope.
- Have one teammate follow this guide from a fresh checkout before declaring onboarding complete.
- For Canvas, follow packaging instructions and include the contribution statement.
- Rehearse downloading/unpacking submitted source and deploying on site.
- Check internet for dependency downloads and university proxy/VPN access for the live demo.
- Never present fixture mode as evidence of live agent behaviour.

## Known limitations

- Complete-request and conflicting-budget flows passed live browser verification
  with explicit JSON output mode, including SQLite handoff/readback, in 4.5 and
  3.3 seconds respectively. See `VERIFICATION.md`. These representative checks
  do not guarantee correct model extraction for every possible input.
- Number words, correctly grouped thousands and `k` shorthand are supported;
  ranges/alternatives and unsupported ambiguous expressions remain unknown.
- Evidence checks cannot prove complete or semantically correct model extraction.
- Capture publishes to a durable request inbox. Live Qwen recommendations and
  actual LangGraph handoffs are saved and shown in React. Occasion suitability
  and serving quantities remain unknown because the catalogue lacks that metadata.
- The optional small local Qwen has different quality and latency; validation
  can reject its output. It is not a guarantee of university-model equivalence.
- Stock lookup is implemented on this branch with operator authorisation and
  found/not-found/stale/error results. Existing stock is a labelled prototype
  snapshot, not a real store feed; timestamps are never refreshed on restart.
- Operator endpoints use a private token. Customer workflows use saved random
  request IDs; public multi-user authentication is not implemented. Keep the app local.
- Linux ARM64 is the tested platform. Mac/Windows-WSL teammate onboarding remains unverified.
- This is not an offline dependency bundle. Locked stable releases reduce variation,
  but no README can guarantee zero errors on every computer.
