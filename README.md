# OpsPilot

Local AI customer support automation. Milestone 2 adds Greek/English customer
message classification, persistent SQLite tickets, and a responsive review dashboard
to the existing React/FastAPI application. Inference uses local `qwen3.5:9b` only.

Paste a message, select **Classify & save ticket**, and review the saved ticket's
category, priority, order ID (when explicitly referenced), intent, and reason.
The dashboard includes service health, counts, a paginated ticket list, refresh,
and individual ticket details. Each ticket starts with status `new`.

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
    app/                 # Configuration, health, classifier, schemas, ticket API/storage
    tests/               # Isolated API and failure-path tests
    requirements.txt
    requirements-dev.txt
    constraints.txt      # Versions verified with Python 3.13
    pytest.ini
  frontend/
    src/                 # React dashboard, API client, unit/component tests
    scripts/smoke.mjs     # Real browser + local model smoke test
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
| `DATABASE_PATH` | `./data/opspilot.db` | File path inside this repository |
| `BACKEND_URL` | `http://127.0.0.1:8000` | Vite's local API proxy target |

Restart servers after changing configuration. The browser uses same-origin `/api`
requests; Vite forwards them to FastAPI, so no broad CORS policy is needed. Both
the development server and `npm.cmd run preview` include this proxy. Serving
`dist` from a different host requires an equivalent `/api` proxy.

Ollama requests ignore HTTP proxy environment variables and never follow redirects.
SQLite and the ticket table are created at backend startup with SQLModel's
`create_all`. This is additive: existing records are preserved. Classification
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

One classification runs at a time per backend process. A concurrent submission
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

Email sending, refunds, generated customer replies, order lookup, authentication,
and external integrations are outside this milestone.

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
