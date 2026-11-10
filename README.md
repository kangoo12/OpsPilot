# OpsPilot

Local AI customer support automation. Milestone 1 provides a React status page,
a FastAPI backend, a SQLite connection through SQLModel, and an Ollama connectivity
check. Ticket classification, generation, and ticket workflows are not implemented.

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
    app/                 # Configuration, database connection, health endpoints
    tests/               # Isolated API and failure-path tests
    requirements.txt
    requirements-dev.txt
    constraints.txt      # Versions verified with Python 3.13
    pytest.ini
  frontend/
    src/                 # React status page and connection-check tests
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
| `OLLAMA_MODEL` | `qwen3.5:9b` | Exact installed Ollama model name |
| `OLLAMA_TIMEOUT_SECONDS` | `5` | Ollama request timeout, greater than 0 and at most 30 seconds |
| `DATABASE_PATH` | `./data/opspilot.db` | File path inside this repository |
| `BACKEND_URL` | `http://127.0.0.1:8000` | Vite's local API proxy target |

Restart servers after changing configuration. The browser uses same-origin `/api`
requests; Vite forwards them to FastAPI, so no broad CORS policy is needed. Both
the development server and `npm.cmd run preview` include this proxy. Serving
`dist` from a different host requires an equivalent `/api` proxy.

Ollama requests ignore HTTP proxy environment variables and never follow redirects.
SQLite is created on the first backend health check. No ticket tables are created.

## Tests and build

```powershell
Set-Location F:\Projects\OpsPilot\backend
.\.venv\Scripts\python.exe -m pytest
Set-Location ..\frontend
npm.cmd test
npm.cmd run build
```

Backend tests mock Ollama and keep temporary SQLite files inside this repository.
Frontend tests check success, network failures, invalid responses, and missing
models. The build runs TypeScript checks before producing `frontend/dist`.

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
