# OpsPilot

Local AI customer support automation. Milestone 3B adds human draft review,
immutable approvals, revision history, ticket statuses and an audit timeline to
Greek/English classification, verified synthetic orders and grounded replies.
Inference uses local
`qwen3.5:9b` exclusively.

Paste a message, select **Classify & save ticket**, and review the saved ticket's
category, priority, order ID (when explicitly referenced), intent, and reason.
The dashboard includes service health, counts, a paginated ticket list, refresh,
and individual ticket details. Each ticket starts with status `new`. Select a ticket
to inspect its order, correct the order reference, and generate a suggested reply.
Every generated reply starts `pending_review`. Operators can edit, approve, reject,
or regenerate it. Approval sends nothing and does not resolve a ticket. Ticket
status changes are separate, explicit operator actions.

All AI connections stay on this computer. There are no cloud inference APIs,
external fonts, analytics, or paid services. Dependency installation needs internet
access; normal app operation uses only local services.

## Requirements

- Windows 11, PowerShell, Git
- Python 3.13 (with pip and venv)
- Node.js 24 LTS (with npm)
- Ollama running at `http://localhost:11434`, with `qwen3.5:9b` installed

Install runtimes from [python.org](https://www.python.org/downloads/windows/)
and [nodejs.org](https://nodejs.org/en/download). Reopen PowerShell after installation
so its PATH includes the new runtimes. No global npm or Python packages are needed.

## Structure

```text
OpsPilot/
  backend/
    app/                 # Health, classifier, tickets, synthetic orders, reply plans/drafts
    tests/               # Isolated API and failure-path tests
    requirements.txt
    requirements-dev.txt
    constraints.txt      # Versions verified with Python 3.13
    pytest.ini
  frontend/
    src/                 # React dashboard, API client, unit/component tests
    scripts/smoke.mjs     # Real browser + local model smoke test
    scripts/smoke3a.mjs   # Order lookup, corrections, reply generation and persistence
    scripts/smoke3b.mjs   # Isolated human-review/status/audit browser verification
    package.json
    vite.config.ts
    tsconfig.json
    index.html
  .env.example
  data/                  # Generated local SQLite database; ignored by Git
```

## First-time setup

Run in PowerShell:

```powershell
Set-Location F:\Projects\OpsPilot
Copy-Item .env.example .env
python -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
Set-Location frontend
npm.cmd install
```

Copy `.env.example` only once; preserve your existing `.env` on later setups.
Using the virtual environment's Python directly avoids activation and PowerShell
execution-policy changes. All project packages are installed into `backend/.venv`
and `frontend/node_modules`.

## Start the backend

In the first PowerShell terminal:

```powershell
Set-Location F:\Projects\OpsPilot\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API documentation: <http://127.0.0.1:8000/docs>.

## Start the frontend

In a second PowerShell terminal:

```powershell
Set-Location F:\Projects\OpsPilot\frontend
npm.cmd run dev
```

Open <http://127.0.0.1:5173>. Keep both terminals open. Stop each server with
`Ctrl+C`. Vite uses a strict port so a conflict is reported instead of silently
moving to another URL. Both servers bind to loopback only.

The page checks both services on load, supports **Check again**, and refreshes
15 seconds after each completed check. Backend health is independent of Ollama
availability. A stopped service or missing model produces a readable error.

## Health checks

| Endpoint | Success | Failure |
| --- | --- | --- |
| `GET /api/health` | HTTP 200, API and SQLite connected | HTTP 503, SQLite unavailable |
| `GET /api/health/ollama` | HTTP 200, Ollama reachable and model installed | HTTP 503, unreachable, invalid response, or model missing |

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:8000/api/health/ollama
```

The Ollama check calls `/api/tags`; it does not load the model or run inference.
A green connection means the service is reachable and the model is installed,
not that generation speed or GPU readiness has been tested.

## Configuration

Root `.env` is optional; `.env.example` documents the defaults. Backend settings
are loaded from the repository root regardless of the current directory.

| Variable | Default | Purpose |
| --- | --- | --- |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | HTTP loopback address only |
| `OLLAMA_MODEL` | `qwen3.5:9b` | Fixed local model for this milestone; other names are rejected |
| `OLLAMA_TIMEOUT_SECONDS` | `5` | Ollama request timeout, greater than 0 and at most 30 seconds |
| `CLASSIFICATION_TIMEOUT_SECONDS` | `120` | Whole inference deadline, including model loading; 10–300 seconds |
| `REPLY_TIMEOUT_SECONDS` | `120` | Whole reply-plan inference deadline; 10–300 seconds |
| `DATABASE_PATH` | `./data/opspilot.db` | File path inside this repository |
| `BACKEND_URL` | `http://127.0.0.1:8000` | Vite's local API proxy target |

Restart servers after changing configuration. The browser uses same-origin `/api`
requests; Vite forwards them to FastAPI, so no broad CORS policy is needed. Both
the development server and `npm.cmd run preview` include this proxy. Serving
`dist` from a different host requires an equivalent `/api` proxy.

Ollama requests ignore HTTP proxy environment variables and never follow redirects.
SQLite schema and additive workflow migrations run at backend startup. Existing
ticket, order and original AI-draft rows remain intact. Classification
does not hold a database transaction open while waiting for Ollama.

## Classification and tickets

| API | Behavior |
| --- | --- |
| `POST /api/tickets` | Accepts `{ "message": "..." }`; classifies, validates, saves, returns HTTP 201 |
| `GET /api/tickets?limit=20&offset=0` | Newest tickets first, global total/new/high/urgent counts; limit 1–100 |
| `GET /api/tickets/{uuid}` | Complete ticket details, or HTTP 404 |

Messages must contain non-whitespace text and be at most 5,000 Unicode characters.
The original text is preserved. Tickets have UUIDs and UTC creation timestamps;
the browser displays times in the viewer's local timezone.

Categories: `delivery`, `returns`, `payments`, `technical_support`, `other`.
Priorities: `low`, `medium`, `high`, `urgent`. General information is low priority,
routine support is medium, blocking failures/critical missed deadlines are high,
and active fraud, security compromise, or immediate safety risks are urgent.

The backend sends `/api/chat` a Pydantic-derived JSON schema, `think: false`,
`stream: false`, temperature 0, a fixed seed, and a bounded output token count.
See [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs)
and [thinking controls](https://docs.ollama.com/capabilities/thinking).
The completed response must pass strict Pydantic validation before any ticket is
written. Truncated output, invalid enums, extra fields, empty intent/reason,
unexpected tool calls, and unsupported order IDs are rejected.

Customer text is JSON-encoded in a separate user message. Fixed system rules
instruct the model to ignore embedded instructions and classify the actual support
problem. The model has no tools or access to application actions. Order IDs are
restricted in the generation schema and checked again against exact references
in the source text. The conservative extractor recognizes explicit English/Greek
order labels with IDs of up to 64 characters containing at least one digit; it
returns null when an identifier is absent or ambiguous. It never generates an ID.
Customer text and AI explanations are rendered as escaped text in React.

One AI request (classification or reply generation) runs at a time per backend process. A concurrent submission
gets HTTP 429; it is never silently queued or retried. Model unavailability returns
HTTP 503, bad AI output HTTP 502, and an inference timeout HTTP 504. None produces
a substitute classification or an unclassified ticket. Stored tickets remain
readable while Ollama is offline. Database errors return HTTP 503 with an action
to refresh before retrying. A lost browser connection can leave the save outcome
uncertain: refresh the list before resubmitting to avoid a duplicate.

AI classification still requires human review. Schema and evidence checks enforce
structure and prevent invented IDs; they cannot prove that every category, priority,
or explanation is semantically correct or that every adversarial message is resisted.
No automatic actions depend on these classifications.

New customer intents are limited to 120 characters and 18 words, use actionable
task phrases, and are checked for gendered customer language and verbatim copying.
Explanations focus on the issue and severity, without a gendered customer narrative.
Older, longer saved summaries remain readable; no historical tickets are rewritten.

## Synthetic orders and suggested replies

The fictional **Aster Shop** catalog seeds 19 orders on startup, including `7821`
(a delivered smartphone), `DEMO-LAMP-9001` (the lamp in transit), and `GR-1042`.
Unrelated scenarios use separate order IDs. Products and all order records are synthetic. There are no customer
names, addresses, card details or other real customer data. The fixed snapshot is
dated November 10, 2026. Delivery statuses, estimates and support eligibility refer
to that snapshot, not to live tracking or the current date. Startup inserts missing
fixtures and does not overwrite existing records.

| API | Behavior |
| --- | --- |
| `GET /api/orders` | List fictional order records |
| `GET /api/orders/{id}` | Found/unknown result; unknown orders have `order: null` |
| `GET /api/tickets/{uuid}/order` | Look up the ticket's effective reference and show its source |
| `PUT /api/tickets/{uuid}/order` | Save `{ "order_id": "7821" }` or `null` as a manual reference |
| `POST /api/tickets/{uuid}/drafts` | Generate, validate and save a pending reply draft; HTTP 201 |
| `GET /api/tickets/{uuid}/drafts?limit=20&offset=0` | Persisted drafts, newest first; limit 1–50 |
| `GET /api/support-policies` | Fictional company policies and their version |

The **Order Details** panel automatically looks up an extracted order ID. **Save &
lookup** can correct it, look up an unknown ID, or clear it. Manual references are
persisted separately: the original AI-extracted ID, category and message remain
unchanged. Draft generation uses the saved reference. Unsaved input changes must
be saved before generating a draft.

Reply generation sends Qwen the original untrusted customer text in a separate
user message and supplies verified order data and seven fictional support policies
in the system context. It uses structured output and `think: false`. For this
milestone, Qwen selects a constrained reply plan: language, tone, relevant verified
fact keys, an information request, and a closing. A deterministic Greek/English
renderer assembles approved wording and verified values. This is intentionally
constrained generation, rather than unrestricted model-written prose with an
unreliable second-model fact check. Unexpected text, invalid plans, unsupported
facts, wrong language and unsafe next steps are rejected without saving a draft.
There is no fallback draft when inference fails.

Mandatory order context cannot be omitted by the model. Known estimates are marked
as estimates; missing estimates stay unknown. Unknown orders ask for the correct
reference. Eligibility permits assessment only, never a return, replacement or
refund approval. No approved sentence claims that a refund, cancellation, escalation,
shipment update or message sending has been performed. Greek/English language is
chosen from the original message using a letter-count heuristic; mixed-language
edge cases still need human review.

Drafts store their order snapshot, policy version, model and UTC timestamp. They
start `pending_review`; current human decisions are stored separately from those
original snapshots. The UI shows the latest 20 drafts with a history selector.
Changing the order reference marks earlier drafts as based on older context.
An order correction during inference causes HTTP 409 instead of saving a stale
draft. No database transaction is held during inference. SQLite foreign keys are
enabled for draft and manual-reference relationships.

Human approvals and ticket workflows are described below. Email sending, real
refunds, live order integrations, authentication and external services remain out
of scope.

## Human approval and ticket workflow (Milestone 3B)

Select a ticket and generate or select a saved reply. **Edit reply** opens a text
editor; **Save Draft** saves a pending revision and its history. **Approve** and
**Reject** require confirmation. Rejection also requires a reason of at least five
characters. **Regenerate** calls local Qwen and creates a separate pending draft
linked to the selected draft. It never replaces an earlier version.

Approved content is immutable. **Create pending revision** edits a copy; saving
creates a new draft ID with a parent link, leaving the approved content and decision
unchanged. Editing rejected content also creates a new pending child. Expand
**Draft revision history** or **Original draft content** to inspect preserved text.
Each draft exposes creation/modification/decision timestamps, version, reviewer,
rejection reason and origin. An unreviewed draft has no decision timestamp or reviewer.

Use **Ticket status** and confirm the change. Allowed transitions are enforced in
FastAPI and reflected in the dropdown:

| Current status | Allowed next statuses |
| --- | --- |
| New | In Progress |
| In Progress | Waiting for Customer, Resolved |
| Waiting for Customer | In Progress, Resolved |
| Resolved | In Progress (reopen) |

Approving or rejecting a draft never changes ticket status. No message is sent by
any workflow action. The **Activity History** timeline records creation, status
changes, reference corrections, draft generation/editing/decisions/regeneration,
and human discrepancy reviews. Events and revisions are append-only.

For a conflicting or unknown order, correct its reference if appropriate, or use
**Document human review**. This requires confirmation and a reason of at least ten
characters describing the review decision. It applies only to the current order
context. The warning and the reason remain visible; documentation does not alter
the customer message, prove disputed facts, or record a real escalation.

Approval is blocked until required context review is documented. It is still
blocked for stale context, contradictory product/status claims, unsupported dates,
and recognized claims of unperformed refunds/actions/guarantees. A neutral
clarification draft can be approved after documentation. Documentation never
authorizes unsupported factual claims. An order/context change invalidates the
earlier documentation; regenerate or save an edited revision using current facts.
These deterministic language checks supplement human judgment, not a full semantic
proof of arbitrary manually written text.

The actor is **Local Operator**, a fixed local demo identity. This is **not user
authentication or access control**. Anyone able to access this local API can act
as the demo operator. The server does not accept a caller-supplied reviewer/actor.
No authentication, multi-user roles, real sending or cloud deployment is implemented.

### Workflow APIs and concurrency

| API | Purpose |
| --- | --- |
| `GET /api/tickets/{id}/workflow` | Status/version, transitions, context hash and documented review |
| `PATCH /api/tickets/{id}/status` | `{status, expected_version, confirmed: true}` |
| `POST /api/tickets/{id}/discrepancy-resolutions` | `{context_fingerprint, reason, confirmed: true}` |
| `PATCH /api/tickets/{id}/drafts/{draftId}` | `{reply_text, expected_version, context_fingerprint}` |
| `POST /api/tickets/{id}/drafts/{draftId}/approve` | `{expected_version, context_fingerprint, confirmed: true}` |
| `POST /api/tickets/{id}/drafts/{draftId}/reject` | Same, plus required `reason` |
| `POST /api/tickets/{id}/drafts/{draftId}/regenerate` | Same as approval; returns a new pending draft |
| `GET /api/tickets/{id}/drafts/{draftId}/revisions` | Preserved version/content/decision history |
| `GET /api/tickets/{id}/activity?limit=30&offset=0` | Paginated audit timeline |

All workflow writes use short SQLite `BEGIN IMMEDIATE` transactions. Mandatory
versions reject stale draft edits, duplicate decisions and stale status changes
with HTTP 409. Context fingerprints protect edits, decisions and documented reviews.
The UI also sends `expected_context_fingerprint` for order-reference corrections;
that field is optional only for compatibility with older order-lookup clients.
An order change still invalidates workflow approval preconditions for every client.
No AI inference holds a database transaction open. Regeneration checks the source
version both before and after inference. Mutations are never automatically retried.

### Safe database migration

Migration version 1 adds `ticketworkflow`, `draftreview`, `draftrevision`,
`discrepancyresolution`, `auditevent`, and `schemamigration`. It does not rebuild,
delete or reset original tables. Before upgrading an existing database, SQLite's
backup API creates a consistent copy, including committed WAL data, under
`data/backups/<database>-pre-3b-<UTC timestamp>-<unique id>.sqlite3`.

The migration runs in one transaction and records its version only on success.
A failure rolls back schema/backfill changes and leaves original data intact.
Repeated startup is idempotent. Existing ticket/draft creation history is explicitly
marked **Historical import**, using original timestamps; previous human actions
are not invented. Historical reference corrections with unknown timestamps are
marked as imports, not backdated guesses.

`ticket.status` and `replydraft.status` retain their original snapshot values;
`ticketworkflow.status` and `draftreview.status` hold authoritative current workflow
state. API responses combine them. This avoids unsafe replacement of old SQLite
CHECK constraints while preserving original metadata. Database triggers protect
approved review rows, original draft snapshots, revisions, audit events and review
documentation against updates/deletion. Do not restore a backup over a running
server; keep the original file and backup if a migration reports an error.

Audit entries store IDs, versions, status changes and necessary review reasons.
Original messages are not duplicated into the audit log, and no credentials are
collected. Revision content is retained because it is necessary for review history.

## Tests and build

```powershell
Set-Location F:\Projects\OpsPilot\backend
.\.venv\Scripts\python.exe -m pytest
Set-Location ..\frontend
npm.cmd test
npm.cmd run build
```

Backend tests mock Ollama and keep temporary SQLite files inside this repository.
Frontend tests include form validation, loading/duplicate prevention, persistence
results in the UI, list/detail loading, refresh, pagination, error recovery, and
HTML escaping. The build runs TypeScript checks before producing `frontend/dist`.

For the real end-to-end smoke test, start the two servers above and run:

```powershell
Set-Location F:\Projects\OpsPilot\frontend
npm.cmd run test:smoke
```

This uses the installed Microsoft Edge browser headlessly (no browser download),
submits three synthetic customer messages to real local `qwen3.5:9b`, verifies
saved tickets and dashboard display/reload, and checks a 390px mobile layout.
It creates real sample tickets in the running backend's database. Results and
screenshots are written under `.cache/smoke/`, which is ignored by Git. This smoke
test is explicit and is not part of `npm.cmd test`, whose Ollama calls are mocked.

Run the additional Milestone 3A browser flow with the servers running:

```powershell
Set-Location F:\Projects\OpsPilot\frontend
npm.cmd run test:smoke:3a
```

This exercises real local Qwen classification and replies, Greek/English drafts,
verified and unknown orders, an injection attempt, manual corrections, persistence,
and desktop/mobile layouts. It creates synthetic test tickets and pending drafts
in the selected backend. Set `OPSPILOT_SMOKE_URL` to another local Vite URL if using
isolated QA ports. Results/screenshots are under `.cache/smoke3a/`. No new runtime
or package installation is required for Milestone 3A.

### Isolated Milestone 3B browser test

This test must not target the production/demo database. Start a separate backend
in a new PowerShell terminal:

```powershell
Set-Location F:\Projects\OpsPilot\backend
$env:DATABASE_PATH = 'data/milestone3b-qa.db'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Start a separate frontend in another new terminal:

```powershell
Set-Location F:\Projects\OpsPilot\frontend
$env:BACKEND_URL = 'http://127.0.0.1:8010'
npm.cmd run dev -- --port 5180
```

Run the test in a third terminal:

```powershell
Set-Location F:\Projects\OpsPilot\frontend
$env:OPSPILOT_SMOKE_URL = 'http://127.0.0.1:5180'
npm.cmd run test:smoke:3b
```

The test refuses to proceed unless port 5180 is used and `/api/health` confirms
the dedicated `data/milestone3b-qa.db` database. It uses the installed Edge browser
headlessly and real local Qwen, creates synthetic QA data, and checks editing,
approval, immutable approved revisions, rejection reasons, regeneration, ticket
transitions/reopening, activity, discrepancy documentation and API bypass attempts.
Results/screenshots are under `.cache/smoke3b/`; no new dependency install is needed.
Stop the two QA servers with `Ctrl+C`. Use new terminals with the normal startup
commands above for your production/demo database so QA environment variables are
not accidentally reused.

## Troubleshooting

- **Python or npm not found:** reopen PowerShell after runtime installation.
  `python --version`, `node --version`, and `npm.cmd --version` should work.
  If Python opens the Microsoft Store, use the installed Python 3.13 executable
  or fix the Windows app execution alias/PATH.
- **Backend unavailable:** inspect the backend terminal and port 8000. The frontend
  may log a proxy connection error while FastAPI is stopped; start it and retry.
- **Ollama unavailable:** open Ollama. Check
  `Invoke-RestMethod http://localhost:11434/api/version`. Use `ollama serve` only
  if another Ollama server is not already running.
- **Model missing:** check `ollama list`. To download it if needed, run
  `ollama pull qwen3.5:9b` (requires internet access and disk space).
- **Port occupied:** stop the process using that port or choose another port.
  If changing the backend port, update `BACKEND_URL` and restart Vite.
- **Database unavailable:** ensure `DATABASE_PATH` is writable and inside OpsPilot.
- **Classification times out:** the first request may need to load the 9B model.
  Check available memory and Ollama logs. Increase `CLASSIFICATION_TIMEOUT_SECONDS`
  up to 300 if needed, then restart the backend. Do not change the 5-second health
  timeout to control classification. No automatic retry or cloud fallback is used.

`.gitignore` excludes dependencies, virtual environments, local environment files,
databases and journals, caches, logs, build output, and editor/OS artifacts.
Dependency manifests and lockfiles should remain tracked. No commits or pushes
are performed by the setup.

The backend requirements apply `constraints.txt` to reproduce the verified package
versions. The frontend uses `package-lock.json`; use `npm.cmd ci` for a clean,
repeatable reinstall after the initial setup.

### SQLAlchemy blocked by Windows Application Control

On November 11, 2026, Code Integrity events 3033/3077 identified policy
`VerifiedAndReputableDesktop` (`{0283ac0f-fff1-49ae-ada1-8a933130cad6}`) blocking
`sqlalchemy/util/_immutabledict_cy.cp313-win_amd64.pyd`. All 270 installed SQLAlchemy
package files matched the hash-verified official Windows wheel byte-for-byte.
The events identify the enforcement policy, but do not establish why enforcement
first affected this installation after the reboot.

The supported repair replaces only SQLAlchemy inside the project virtual
environment with its official **2.1.8 pure-Python wheel**. It preserves the pinned
version and other dependencies; Windows security settings stay unchanged.
SQLAlchemy's optional native acceleration is absent in this installation.
If recreating the virtual environment reproduces this issue, stop the backend
and run from `F:\Projects\OpsPilot`:

```powershell
.\backend\.venv\Scripts\python.exe -m pip install --no-deps --no-cache-dir --force-reinstall "https://files.pythonhosted.org/packages/a3/1e/6eba6770b626a991e58de306385d414b9f3ae780ae60c61aa1d0841dcaaf/sqlalchemy-2.1.8-py3-none-any.whl#sha256=69aea77b5d8a64e95d01fd7ec54985c84b4a8ef3cac3108e9271145441400c1b"
.\backend\.venv\Scripts\python.exe -c "import sqlalchemy; print(sqlalchemy.__version__)"
.\backend\.venv\Scripts\python.exe -m pip check
```

Sources: [official PyPI release](https://pypi.org/project/SQLAlchemy/2.1.8/)
and [SQLAlchemy installation documentation](https://docs.sqlalchemy.org/en/21/intro.html#building-the-cython-extensions).
This repair passed all **213 backend tests** and localhost startup/health checks
against an isolated SQLite copy. Read-only fingerprints confirmed every original
database table was unchanged; all dependency versions were also unchanged.

## Milestone 1 verification

Verified on Windows on November 10, 2026:

- Python 3.13.17, Node.js 24.22.2, npm 11.19.1, Git 2.56.0.windows.4
- Ollama 0.40.16, with `qwen3.5:9b` installed
- 17 backend tests and 7 frontend tests pass; production frontend build succeeds
- Both servers start; direct and proxied health checks return HTTP 200
- Browser appearance still needs manual review; no browser automation was available

Python was installed into the default per-user
`C:\Users\dimi_\AppData\Local\Programs\Python\Python313` directory; Node.js into
`C:\Program Files\nodejs`. Their official installers were downloaded from
[Python's release page](https://www.python.org/downloads/release/python-31317/)
and [Node's release directory](https://nodejs.org/dist/v24.22.2/). Both Windows
publisher signatures and published SHA-256 checksums were verified before execution.
The initial Node installer permission error was resolved with administrator
elevation. Open a new PowerShell terminal to pick up the installed runtime PATHs.

## Milestone 2 verification

Verified on November 10, 2026 with the installed local `qwen3.5:9b`:

- 68 backend tests and 19 frontend tests pass; production build and dependency checks pass.
- Real Edge browser flow passes: submit → local AI → SQLite save → ticket list/details.
- Greek delivery: `delivery`, `medium`, order ID `GR-1042` (1.761 seconds).
- Active unauthorized charges: `payments`, `urgent`, no order ID (0.885 seconds).
- Injection requesting payments/urgent/a fake ID: `delivery`, `medium`, no order ID (1.267 seconds).
- Page reload preserves tickets; desktop and 390px mobile screenshots were inspected.
- No browser JavaScript errors or mobile horizontal overflow were detected.

The measured requests used an already loaded model; they are not cold-start latency
guarantees. Full actual responses are in [docs/milestone2-smoke.json](docs/milestone2-smoke.json).
Local screenshots are `.cache/smoke/desktop.png` and `.cache/smoke/mobile.png`.
Smoke-test sample tickets remain in the local database. No commits or pushes were made.

## Milestone 3A verification (original run)

Historical result before the focused reliability review: the lamp fixture
incorrectly reused `7821`. The output below and archived JSON are preserved as
evidence, not as the current fixture definition. See the reliability review below.

Verified on November 10, 2026:

- 111 backend tests pass, including seeding, known/unknown orders, manual corrections,
  grounded drafts, unsupported facts/actions, injection, failure handling, persistence,
  concurrent context changes and concise/gender-neutral summary regressions.
- 32 frontend tests pass; the production build and Python dependency checks pass.
- Real `qwen3.5:9b` classification and four reply-plan inferences pass through the
  full Edge browser flow. All drafts remain `pending_review` and no actions are sent.
- Greek `GR-1042` draft correctly reports no verified ETA. English `7821` draft uses
  only the recorded November 14 estimate and explicitly avoids guaranteeing delivery.
- An injection requesting a fake delivery date and refund approval cannot add those
  claims. Unknown orders ask for a corrected reference. A manual change to `GR-1042`
  persists without replacing the original extracted ID `7821`.
- Drafts survive page reload; desktop and 390px mobile screenshots were inspected.
  No browser JavaScript errors or horizontal mobile overflow were detected.

This run used separate QA ports **8010 / 5180** and
`data/milestone3a-smoke.db`. Existing servers on **8000 / 5173** were left alone.
The final real inference results are in
[docs/milestone3a-smoke.json](docs/milestone3a-smoke.json); local screenshots are
`.cache/smoke3a/desktop.png` and `.cache/smoke3a/mobile.png`. Measured draft requests
took roughly 0.7–0.9 seconds with the model already loaded, not including a cold start.

Restart an existing backend to load the new routes and seed orders. Startup commands
above are unchanged. Existing tickets and their historical summaries are preserved;
new classifications use the improved quality checks. No new packages, system changes,
Git commits or pushes were needed for this milestone.

## Focused reliability review

The original smartphone ticket in `data/opspilot.db` and the reported lamp draft
were different tickets in different databases. The lamp response came from a
synthetic shipping/injection message in `data/milestone3a-smoke.db`; there was no
draft saved for the original smartphone ticket. However, the seed reused `7821`
for an unrelated product and reply generation did not compare customer claims
with the matched record. That left a genuine consistency gap.

Fresh seeds now reserve `7821` for the delivered smartphone. The lamp and its
shipping fixtures use `DEMO-LAMP-9001`. Seeding still inserts missing rows only:
existing tickets, old order rows, reference corrections and historical drafts are
never rewritten or deleted. An existing legacy lamp row at `7821` is intentionally
left intact and its conflict with the smartphone ticket is visibly flagged.

On ticket creation and reads, the backend derives a `consistency` result and
`requires_human_review` flag from explicit Greek/English product and delivery claims.
It detects product mismatches, delivery-state mismatches and competing statements;
missing/unknown orders are marked as needing verification. These are read-time
flags, not automatic status changes. Milestone 3B's manual status workflow is
separate. Corrections recompute
the result and refresh list/detail badges. Product words inside order IDs are not
treated as customer assertions. Delivery questions are not delivery confirmations.

These conservative rules cover recognized product vocabulary and explicit receipt/
shipping wording. “No discrepancy detected” does not prove that every sentence
has been semantically verified. The customer report and the dated order snapshot
remain distinct sources; neither is silently declared correct or explained away.

If a material discrepancy exists, the renderer excludes product, delivery, estimate
and eligibility claims entirely. Qwen must return a clarification plan; the reply
asks for the order reference, product and receipt information and states that human
review is needed. It never guesses why the sources differ or claims an escalation.
Invalid plans still fail without a fallback draft.

Historical draft snapshots are checked on read without changing stored text.
Conflicting old drafts are collapsed behind a warning, including when the current
order reference has since been corrected. New conflict-aware clarification drafts
remain visible and `pending_review`.

For a read-only provenance audit, run from the repository root:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\audit_order_references.py --database data/opspilot.db --order-id 7821
```

The helper permits only repository-local databases, opens SQLite in read-only mode,
and reports ticket/draft provenance, consistency flags and table fingerprints.
The temporary `.cache/debug_classification.py` capture script was reviewed and
removed; reusable tests, browser checks and the audit helper live in source/test
directories. `.cache/`, browser profiles, reports and temporary captures stay ignored.

Full findings and validation are in [docs/reliability-review.md](docs/reliability-review.md).
