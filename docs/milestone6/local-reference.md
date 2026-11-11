# Local setup, operation and APIs

Use Windows PowerShell opened in the repository root. [README installation and isolated demo startup](../../README.md) are the primary instructions. Nothing here is a public deployment recipe.

## Normal workspace versus isolated demo

Normal backend, using `.env` or default `data/opspilot.db`:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Normal frontend in another fresh root terminal:

```powershell
$env:BACKEND_URL = 'http://127.0.0.1:8000'
Set-Location frontend
npm.cmd run dev
```

Normal URL: <http://127.0.0.1:5173>. The isolated live-demo instructions instead use `.cache/milestone6/live-demo.db`, backend 8018 and frontend 5197. Database paths resolve from the repository root even with `--app-dir backend`. Startup creates missing schema/orders without overwriting existing records. For a fresh rehearsal choose a new repository-local filename; never delete/reset existing data. New terminals avoid leftover QA environment overrides.

## Configuration

| Variable | Default | Constraint |
| --- | --- | --- |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | HTTP loopback, no credentials/path/query/fragment |
| `OLLAMA_MODEL` | `qwen3.5:9b` | Only accepted model name |
| `OLLAMA_TIMEOUT_SECONDS` | 5 | Health timeout, >0 and ≤30 seconds |
| `CLASSIFICATION_TIMEOUT_SECONDS` | 120 | Whole inference deadline, 10–300 seconds |
| `REPLY_TIMEOUT_SECONDS` | 120 | Whole reply deadline, 10–300 seconds |
| `DATABASE_PATH` | `data/opspilot.db` | Resolves inside the repository |
| `BACKEND_URL` | `http://127.0.0.1:8000` | Vite HTTP loopback proxy target; restart Vite after changes |

`.env` is optional. Copy `.env.example` only when `.env` is absent. Process environment overrides the file. The browser uses `/api`, not an Ollama URL. Vite development and preview have the proxy; serving `dist` elsewhere requires an equivalent proxy and security design. Preview is not a hardened deployment server.

## Health and failure behavior

For the isolated demo:

```powershell
Invoke-RestMethod http://127.0.0.1:8018/api/health
Invoke-RestMethod http://127.0.0.1:8018/api/health/ollama
Invoke-RestMethod http://localhost:11434/api/version
ollama list
```

Backend health checks SQLite independently of Ollama. Ollama health lists installed models and does not warm inference. The UI button is **Check connections**; checks repeat 15 seconds after completion. A green badge is not a latency or generation-quality guarantee.

One inference runs per backend process; busy→429, unavailable→503, invalid AI output→502, timeout→504. There is no fabricated fallback ticket/draft. Storage errors→503; stale versions/context→409. Lost responses can make write outcome uncertain: refresh before retrying. No durable queue or idempotency key is implemented.

## API reference

The running backend's `/docs` provides full schemas. These are unauthenticated local demo routes.

| Route | Behavior |
| --- | --- |
| `GET /api/health`, `/api/health/ollama` | Storage/service and installed-model checks |
| `POST /api/tickets` | Classify, validate, save (201); original message preserved |
| `GET /api/tickets` | `limit` 1–100, `offset`≥0; optional `search`, `category`, `priority`, `status`, `sort` |
| `GET /api/tickets/{id}` | Current status, summaries and derived consistency/review flag |
| `GET /api/orders`, `/api/orders/{orderId}` | Fictional snapshots; explicit found/unknown |
| `GET`, `PUT /api/tickets/{id}/order` | Effective reference lookup / separate manual correction |
| `GET /api/support-policies` | Seven fictional policies, version v3 |
| `POST`, `GET /api/tickets/{id}/drafts` | Generate pending / list saved drafts |
| `PATCH /api/tickets/{id}/drafts/{draftId}` | Edit pending or fork reviewed content |
| `POST .../drafts/{draftId}/approve`, `/reject`, `/regenerate` | Explicit decisions or new pending AI child |
| `GET .../drafts/{draftId}/revisions` | Preserved revision history |
| `GET /api/tickets/{id}/workflow` | Status/version, context hash and human review |
| `PATCH /api/tickets/{id}/status` | Confirm a valid transition with expected version |
| `POST /api/tickets/{id}/discrepancy-resolutions` | Document review; does not verify disputed facts |
| `GET /api/tickets/{id}/activity` | Paginated local audit history |
| `GET /api/analytics?days=30` | Global distributions, decisions, UTC volume, resolution intervals |

Search covers original message, intent and extracted/manual order references; SQLite case-insensitivity has limited Unicode support. Search/filters apply before pagination and matching counts. Sort values: `newest`, `oldest`, `priority_high`, `priority_low`, `updated`, with deterministic ties for stable data. Offset pagination is not a snapshot across concurrent list requests. Analytics ignores Inbox filters and uses no AI.

Categories: `delivery`, `returns`, `payments`, `technical_support`, `other`. Priorities: `low`, `medium`, `high`, `urgent`. Statuses: new→in-progress; in-progress→waiting or resolved; waiting→in-progress or resolved; resolved→in-progress. Approval never changes status or sends anything.

Workflow writes check expected versions/context and explicit confirmation. Order correction's expected-context field is optional for old-client compatibility. Historical snapshot status fields differ from current workflow status tables. Migrations back up existing legacy databases under their parent `backups/`, perform additive changes and mark imported history. This is not authenticated non-repudiation against an administrator.

## SQLAlchemy compatibility

The known-good Windows environment uses official SQLAlchemy **2.1.8 pure Python**, without optional native accelerators. If recreating the environment gives a blocked `_immutabledict_cy` import, stop the backend and repair only the virtual environment:

```powershell
.\backend\.venv\Scripts\python.exe -m pip install --no-deps --no-cache-dir --force-reinstall "https://files.pythonhosted.org/packages/a3/1e/6eba6770b626a991e58de306385d414b9f3ae780ae60c61aa1d0841dcaaf/sqlalchemy-2.1.8-py3-none-any.whl#sha256=69aea77b5d8a64e95d01fd7ec54985c84b4a8ef3cac3108e9271145441400c1b"
.\backend\.venv\Scripts\python.exe -c "import sqlalchemy; print(sqlalchemy.__version__)"
.\backend\.venv\Scripts\python.exe -m pip check
```

Keep version constraints and Windows security protections intact. The official hash-pinned artifact is retained from the repository's prior verified repair. No reinstall was performed for Milestone 6. [5D compatibility verification](../milestone5d/final-quality-report.md).

## Troubleshooting and verification

- Python/npm missing: reopen the terminal after runtime installation; check PATH/app aliases. Use the project's venv executable without activation or changing execution policy.
- Backend unavailable: inspect its terminal/port; the frontend proxy must target that port. Select unused ports instead of terminating unrelated processes.
- Ollama unavailable: start Ollama and check `ollama list`. Stored tickets remain readable. Show saved evidence explicitly as a recording/history, never as live inference.
- Invalid classification: show the error; no new ticket was saved. Known narrative failures remain. Refresh before resubmitting after uncertain writes.
- Database issue: verify the repository-local resolved path/write access. Preserve the file/backups, never reset it for a demo.

Root README lists deterministic tests/build. Historical browser/benchmark scripts can write to their configured database and may depend on ignored run-state files. Use their exact isolated QA instructions, not the normal database. Do not rerun frozen experiments for improved presentation scores. The [Milestone 6 screenshot helper](screenshots/README.md) is read-only and makes no inference calls.
