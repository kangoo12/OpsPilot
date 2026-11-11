# GITHUB COMMIT READINESS — Milestone 6

Review scope: actual changes from an initially clean Git workspace. Application source, dependency manifests, original data and historical 5A–5D evidence remain unchanged. No staging, commit, push or public deployment was performed. Publication safety is distinct from production readiness.

## A. SAFE TO COMMIT

| Exact repository-relative path | Reason |
| --- | --- |
| `README.md` | Reviewed portfolio/setup guide with conditional-demo limits, accurate historical denominators and preserved pure-Python installation path; removes private workstation installation details from the old README. |
| `backend/scripts/check_launch_docs.py` | Dependency-free local links/anchors/fences and basic diagram checks; executed and explicitly not described as a Mermaid renderer. |
| `frontend/scripts/capture-milestone6.mjs` | Read-only localhost screenshot helper with QA sentinel and GET-only/origin assertions; successful capture made no inference or API writes. Requires existing ignored synthetic QA state. |
| `docs/milestone6/architecture.md` | Actual code architecture, trust boundaries and limits, separated from future plans. |
| `docs/milestone6/benchmark-summary.md` | Historical scores, failures, denominators and semantic/validity distinctions; no changed ground truth. |
| `docs/milestone6/demo-script.md` | One audited fictional case, isolated startup/preflight, timed flow and honest failure/recorded backup. |
| `docs/milestone6/pitch.md` | Three timed scripts; no unsupported adoption, revenue, production or competitive-superiority claims. |
| `docs/milestone6/judges-qa.md` | Transparent answers on coding agents, human contribution, costs, safety, privacy and scaling. |
| `docs/milestone6/local-reference.md` | Accurate local ports, configuration/APIs, error behavior and official hash-pinned SQLAlchemy repair retained from prior verified setup. |
| `docs/milestone6/production-roadmap.md` | Future-work stages, measurable gates, migration/rollback, roles/effort and explicitly hypothetical budgets; no implementation or legal-compliance claim. |
| `docs/milestone6/release-checklist.md` | Verified checks distinguished from pending licensing, publication, rehearsal and event-day actions. |
| `docs/milestone6/screenshots/README.md` | Capture provenance, isolation and synthetic-data scope; no private paths/profile contents. |
| `docs/milestone6/screenshots/01-overview.png` | Reviewed real UI capture; fictional filtered tickets and connection status only. |
| `docs/milestone6/screenshots/02-smart-inbox.png` | Reviewed real selected-ticket capture with synthetic message/order. |
| `docs/milestone6/screenshots/03-order-verification.png` | Reviewed fictional order snapshot; estimate caveat visible. |
| `docs/milestone6/screenshots/04-draft-review.png` | Reviewed saved pending QA draft and human controls; no real customer data. |
| `docs/milestone6/screenshots/05-analytics.png` | Reviewed actual synthetic QA metrics, not invented adoption/production figures. |
| `docs/milestone6/verification.json` | Reviewed status codes, counts, dimensions/checksums and integrity summary; no original DB contents or machine identifiers. |
| `docs/milestone6/commit-readiness.md` | This exact-path review and pending owner decisions. |

Source/document changes and screenshots were inspected for secrets, real customer data, private usernames/absolute paths, accidental databases and unnecessary generated output. Local URLs, repository-relative QA paths, synthetic ticket UUIDs, benchmark dates, official artifact hashes and publicly cited legal/documentation URLs are intentional. The five PNGs are requested portfolio assets rather than temporary captures. No new dependency/install is needed.

## B. DO NOT COMMIT

| Exact repository-relative path | Reason |
| --- | --- |
| `.env` | Private local configuration. |
| `data/` | Original database/backups, including `data/opspilot.db`; preserve locally. |
| `.cache/` | All local benchmark/browser/demo run state and logs, including older milestones. |
| `.cache/milestone6/baseline.json` | Private original-data fingerprints and absolute database path. |
| `.cache/milestone6/screenshots-before.json` | Private QA table fingerprint baseline. |
| `.cache/milestone6/screenshots.db` | Generated isolated synthetic snapshot, not a source asset. |
| `.cache/milestone6/live-demo.db` | Fresh isolated demo database, kept locally for rehearsal. |
| `.cache/milestone6/capture-profile/` | Browser state/profile/cache. |
| `.cache/milestone6/capture-result.json` | Local raw capture metadata; public provenance/checksums are in docs. |
| `.cache/milestone6/capture-result-refreshed.json` | Local final ready-state recapture metadata; no new inference or API mutation. |
| `.cache/milestone6/commit-scan.json` | Generated local publication-scan output. |
| `.tools/` | Local tooling artifacts. |
| `.pytest-tmp/` | Generated isolated test artifacts. |
| `backend/.pytest-tmp/` | Generated isolated test databases. |
| `backend/.pytest_cache/` | Test cache. |
| `backend/.venv/` | Installed Python environment. |
| `backend/app/__pycache__/` | Generated Python bytecode. |
| `backend/benchmarks/__pycache__/` | Generated Python bytecode. |
| `backend/scripts/__pycache__/` | Generated Python bytecode. |
| `backend/tests/__pycache__/` | Generated Python bytecode. |
| `frontend/node_modules/` | Installed dependencies and caches. |
| `frontend/dist/` | Generated production build. |

Existing ignore rules cover these files/directories (and any browser-created children under `.cache/`). No ignored artifacts are already tracked. Preserve the files locally; do not delete user records or historical run evidence.

## C. MANUAL REVIEW NEEDED

| Exact repository-relative path | Reason |
| --- | --- |
| `docs/milestone5/hardware-supplement-v1.json` | Already tracked and unchanged. Contains prior workstation hardware profiling; owner must decide whether it belongs in a public portfolio. Ignore rules cannot protect tracked files. |

No new Milestone 6 file remains in category C. The owner still needs to choose a project license (no `LICENSE` currently exists) and review/rehearse the public narration. Documentation acknowledges those pending actions rather than claiming licensing or rehearsal is complete.

Recommended commit message: `Package OpsPilot demo, evidence and staged production roadmap`
