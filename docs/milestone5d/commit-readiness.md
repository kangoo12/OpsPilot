# GITHUB COMMIT READINESS — Milestone 5D

Reviewed November 11, 2026. Initial Git status was clean; the changes below are the actual 5D changes, not an assumed list from earlier milestones. No files were staged, committed, pushed or deleted. Publication safety is distinct from the conditional demo recommendation.

## A. SAFE TO COMMIT

| Exact repository-relative path | Reason |
| --- | --- |
| `backend/app/workflow_common.py` | Reviewed approval guard now rejects unrelated order references in unknown, missing and disputed contexts; focused API regressions pass. |
| `backend/tests/test_release_audit.py` | Four deterministic isolated tests for the reproduced approval defect, literal SQL-like search and API enum contracts. |
| `backend/scripts/audit_milestone5d.py` | Local, one-shot synthetic audit harness with QA path checks and original-data/evidence fingerprints; no credentials. Requires preserved local baseline files. |
| `backend/scripts/verify_milestone5d_restart.py` | Verified QA-only process restart and read-only API/persistence checks; stops only its own child processes. |
| `frontend/index.html` | One local data-favicon link removes the observed console 404. |
| `frontend/scripts/smoke5d.mjs` | Reviewed localhost browser QA harness and explicit continuation after its locator failure; not application UI code. |
| `frontend/scripts/verify5d.mjs` | Read-only browser follow-up and explicitly simulated API error recovery; no inference/workflow writes. |
| `docs/milestone5d/scenarios-v1.json` | Nine new fictional cases and browser messages; expected labels frozen before inference. |
| `docs/milestone5d/freeze-v1.json` | Original source/expectation hashes and timestamp; preserved despite later browser-harness correction. |
| `docs/milestone5d/environment-v1.json` | Local model name/release digest and Ollama version; no host/user/hardware identifiers. |
| `docs/milestone5d/ai-results-v1.jsonl` | Reviewed synthetic outputs, failures and order snapshots. No real customer data or secrets. |
| `docs/milestone5d/data-integrity-v1.json` | Original inference-run integrity summary; historical meaning retained. |
| `docs/milestone5d/browser-verification-v1.json` | Reviewed browser evidence/provenance, including harness failures and separate successful follow-up; no private profile contents. |
| `docs/milestone5d/restart-verification-v1.json` | Two actual QA process starts, persistence/health checks and final integrity counts. |
| `docs/milestone5d/final-source-manifest-v1.json` | Final executable-source hashes; explicitly explains the changed browser-harness hash. |
| `docs/milestone5d/final-quality-report.md` | Evidence-based CONDITIONAL GO, limitations, exact test outcomes and remaining safety issue. |
| `docs/milestone5d/commit-readiness.md` | This publication review with exact paths and exclusions. |

All 17 changed/new public files were reviewed and scanned for credential/private-key patterns, email/customer identifiers, private absolute paths and unexpected large files. No such content was found; largest candidate is the approximately 32 KB synthetic AI JSONL. Synthetic QA UUIDs, model hashes and benchmark timestamps are not personal identifiers. Existing source and static synthetic order data were inspected during the audit. No new dependencies or generated database files are in this list.

## B. DO NOT COMMIT

| Exact repository-relative path | Reason |
| --- | --- |
| `.env` | Local configuration; may contain private values. |
| `data/` | Original SQLite database and backups, including `data/opspilot.db`; preserve locally. |
| `.cache/` | All local run state, logs, browser profiles and diagnostics. |
| `.cache/milestone5d/baseline.json` | Private original-data fingerprints and absolute database path. |
| `.cache/milestone5d/browser-qa.db` | Generated synthetic QA database; preserve for audit continuation. |
| `.cache/milestone5d/quality-qa.db` | Generated model-evaluation QA database. |
| `.cache/milestone5d/pre-restart.json` | Local row fingerprint snapshot. |
| `.cache/milestone5d/seed.json` | Local QA sentinel/run state. |
| `.cache/milestone5d/browser-results-resumed.json` | Raw local browser result; reviewed publication summary is in docs. |
| `.cache/milestone5d/browser-readonly-followup.json` | Raw local follow-up; reviewed publication summary is in docs. |
| `.cache/milestone5d/smoke5d-before-locator-fix.mjs` | Historical debugging copy, retained locally and hash-linked from docs. |
| `.cache/milestone5d/restart-1.log` | Generated local server access log. |
| `.cache/milestone5d/restart-2.log` | Generated local server access log. |
| `.cache/milestone5d/focused-tests.xml` | Generated test report; contains machine-local execution metadata. |
| `.cache/milestone5d/commit-scan.json` | Local publication-scan output. |
| `.cache/milestone5d/browser-profile/` | Browser profile/cache, including machine-specific state. |
| `.cache/milestone5d/browser-profile-resume/` | Browser profile/cache. |
| `.cache/milestone5d/browser-profile-readonly/` | Browser profile/cache. |
| `.cache/milestone5d/desktop-Analytics.png` | Local QA screenshot, unnecessary generated output. |
| `.cache/milestone5d/desktop-Smart-Inbox.png` | Local QA screenshot. |
| `.cache/milestone5d/mobile-Analytics.png` | Local QA screenshot. |
| `.cache/milestone5d/mobile-Smart-Inbox.png` | Local QA screenshot. |
| `.cache/milestone5d/failure.png` | Local failure capture; preserve, do not publish as release evidence alone. |
| `.cache/milestone5d/cv_debug.log` | Generated browser diagnostic log. |
| `.tools/` | Local tooling artifacts. |
| `.pytest-tmp/` | Generated isolated test databases and temporary files. |
| `backend/.pytest-tmp/` | Generated isolated test databases and temporary files. |
| `backend/.pytest_cache/` | Test cache. |
| `backend/.venv/` | Installed Python environment. |
| `backend/app/__pycache__/` | Generated bytecode. |
| `backend/benchmarks/__pycache__/` | Generated bytecode. |
| `backend/scripts/__pycache__/` | Generated bytecode. |
| `backend/tests/__pycache__/` | Generated bytecode. |
| `frontend/node_modules/` | Installed dependencies/cache. |
| `frontend/dist/` | Generated production build. |

Existing `.gitignore` covers these paths; `git ls-files -ci --exclude-standard` returns no tracked ignored files. Ignore rules were not used to conceal tracked files. The complete `.cache/` exclusion also covers browser-created subdirectories not enumerated above. No local artifacts or user data were deleted.

## C. MANUAL REVIEW NEEDED

| Exact repository-relative path | Reason |
| --- | --- |
| `docs/milestone5/hardware-supplement-v1.json` | Already tracked and unchanged. Contains workstation hardware profiling from 5A; the product owner should decide whether to publish it. It is not a new 5D change and ignore rules cannot protect an already-tracked file. |

No new 5D file remains in category C. The unresolved semantic/safety limitations are disclosed in the final report; committing source does not authorize customer use or approve generated drafts.

Recommended commit message: `Close order-reference approval gap and document final demo quality gate`
