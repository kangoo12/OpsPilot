# GITHUB COMMIT READINESS ? Milestone 5C

Reviewed actual Git status/diff and every changed/new public file. This list includes
all still-uncommitted 5B work; nothing was reverted or silently omitted. A means
reviewed publication safety and the stated functional tests, not production-grade
model reliability. No staging, commits, pushes or user-file deletion occurred.

## A. SAFE TO COMMIT

| Exact repository-relative path | Reason |
| --- | --- |
| `backend/app/classification_rules.py` | Language/name checks and affirmative hazard evidence, with negation/history/control exclusions; no secret data or summary/label rewriting. |
| `backend/app/classifier.py` | Functional language review passes: conditional styles/schema plus runtime checks; all 11 former wrong-language cases now English (9 accepted, 2 narrative rejections). No validation relaxed. Remaining model errors disclosed. |
| `backend/app/customer_data.py` | Preserves 5B masking/security helpers; prose-only language counting ignores URLs and identifiers without modifying original text. |
| `backend/app/reply_generator.py` | Retained uncommitted 5B grounded-reply improvements; byte-for-byte unchanged by 5C, including v3 policy and safety constraints. |
| `backend/benchmarks/milestone5b.py` | Preserved 5B measurement/postprocessing source; no credential or environment change. |
| `backend/benchmarks/milestone5c.py` | Explicit versioned serial local runner; checked isolated QA targets and no result overwrite; all attempts retained. |
| `backend/benchmarks/reply_eta.py` | Fact-aware ETA assertion v2; unknown dates stay unknown; no inference or fabricated ETA. |
| `backend/benchmarks/report5b.py` | Preserved 5B measurement/postprocessing source; no credential or environment change. |
| `backend/benchmarks/report5c.py` | Read-only postprocessor exposing both runs, failures and conditional language/acceptance counts. |
| `backend/tests/test_ai_quality.py` | Preserved 5B synthetic regression/isolation tests; no production inputs or credentials. |
| `backend/tests/test_benchmark_5b.py` | Preserved 5B synthetic regression/isolation tests; no production inputs or credentials. |
| `backend/tests/test_final_reliability.py` | Synthetic positive/negative safety, bilingual, identifier/control-boundary and ETA regressions; no live data. |
| `backend/tests/test_support.py` | Retained 5B missing-details wording assertion; existing refund/eligibility checks stay intact. |
| `backend/tests/test_tickets.py` | Greek length-limit input now receives a correctly localized mock; length acceptance and API validation remain. |
| `docs/milestone5b/classification-results-v1.csv` | Unchanged historical 5B synthetic evidence/documentation, already uncommitted when 5C began; do not rewrite old scores. Historical classifier review is superseded only by the current 5C review. |
| `docs/milestone5b/commit-readiness.md` | Unchanged historical 5B synthetic evidence/documentation, already uncommitted when 5C began; do not rewrite old scores. Historical classifier review is superseded only by the current 5C review. |
| `docs/milestone5b/environment-v1.json` | Unchanged historical 5B synthetic evidence/documentation, already uncommitted when 5C began; do not rewrite old scores. Historical classifier review is superseded only by the current 5C review. |
| `docs/milestone5b/freeze-v1.json` | Unchanged historical 5B synthetic evidence/documentation, already uncommitted when 5C began; do not rewrite old scores. Historical classifier review is superseded only by the current 5C review. |
| `docs/milestone5b/heldout-v1.json` | Unchanged historical 5B synthetic evidence/documentation, already uncommitted when 5C began; do not rewrite old scores. Historical classifier review is superseded only by the current 5C review. |
| `docs/milestone5b/metrics-v1.json` | Unchanged historical 5B synthetic evidence/documentation, already uncommitted when 5C began; do not rewrite old scores. Historical classifier review is superseded only by the current 5C review. |
| `docs/milestone5b/reply-review-v1.json` | Unchanged historical 5B synthetic evidence/documentation, already uncommitted when 5C began; do not rewrite old scores. Historical classifier review is superseded only by the current 5C review. |
| `docs/milestone5b/reply-rubric.md` | Unchanged historical 5B synthetic evidence/documentation, already uncommitted when 5C began; do not rewrite old scores. Historical classifier review is superseded only by the current 5C review. |
| `docs/milestone5b/reply-scenarios-v1.json` | Unchanged historical 5B synthetic evidence/documentation, already uncommitted when 5C began; do not rewrite old scores. Historical classifier review is superseded only by the current 5C review. |
| `docs/milestone5b/report.md` | Unchanged historical 5B synthetic evidence/documentation, already uncommitted when 5C began; do not rewrite old scores. Historical classifier review is superseded only by the current 5C review. |
| `docs/milestone5b/results-v1.jsonl` | Unchanged historical 5B synthetic evidence/documentation, already uncommitted when 5C began; do not rewrite old scores. Historical classifier review is superseded only by the current 5C review. |
| `docs/milestone5b/root-causes.md` | Unchanged historical 5B synthetic evidence/documentation, already uncommitted when 5C began; do not rewrite old scores. Historical classifier review is superseded only by the current 5C review. |
| `docs/milestone5c/classification-results-v1.csv` | All classification attempts, labels, language validation and errors, including rejected cases; synthetic data only. |
| `docs/milestone5c/commit-readiness.md` | This actual-status, exact-path commit safety and functional review. |
| `docs/milestone5c/environment-v1.json` | Sanitized local model/digest/timing/integrity metadata; no new hardware, user or host identifiers. |
| `docs/milestone5c/eta-correction-v2.json` | Separate versioned reevaluation of the unchanged N06 output; explicitly retains old false result and null ETA. |
| `docs/milestone5c/followup-v2/environment-v1.json` | Sanitized local model/digest/timing/integrity metadata; no new hardware, user or host identifiers. |
| `docs/milestone5c/followup-v2/eta-correction-v2.json` | Separate versioned reevaluation of the unchanged N06 output; explicitly retains old false result and null ETA. |
| `docs/milestone5c/followup-v2/freeze-v1.json` | Relative code/expectation/evidence hashes and freeze timestamp; no private database row fingerprints. |
| `docs/milestone5c/followup-v2/regression-v1.json` | Frozen, newly authored fictional scenarios and labels; no actual customer data. |
| `docs/milestone5c/followup-v2/replies-v1.json` | Frozen, newly authored fictional scenarios and labels; no actual customer data. |
| `docs/milestone5c/followup-v2/results-v1.jsonl` | Necessary synthetic raw model evidence with all failures and timings; no production messages or generic server logs. |
| `docs/milestone5c/freeze-v1.json` | Relative code/expectation/evidence hashes and freeze timestamp; no private database row fingerprints. |
| `docs/milestone5c/metrics-v1.json` | Computed denominators, confusion matrices and timing statistics; not private production analytics. |
| `docs/milestone5c/regression-v1.json` | Frozen, newly authored fictional scenarios and labels; no actual customer data. |
| `docs/milestone5c/replies-v1.json` | Frozen, newly authored fictional scenarios and labels; no actual customer data. |
| `docs/milestone5c/reply-review-v1.json` | Synthetic actual replies and explicitly pending semantic review; no approvals or sends. |
| `docs/milestone5c/report.md` | Audit report documenting actual results, limits, corrections and preserved historical evidence; no secrets. |
| `docs/milestone5c/results-v1.jsonl` | Necessary synthetic raw model evidence with all failures and timings; no production messages or generic server logs. |

## Functional classifier review

`backend/app/classifier.py` is now recommended for commit for the targeted language
correction: all 11 former wrong-language inputs have English raw summaries on the
final implementation. Nine are accepted; two remain rejected for customer narrative.
Every classification in both 5C batches passes the raw language/name check; runtime
language validation prevents saving a wrong-language result. Gender and narrative
checks remain active, no translations/generic fallbacks are used, and the known
electric-shock return is urgent. This supersedes the language-specific C warning in
the historical 5B review, without editing that historical document.

Remaining limitations are not hidden: narrative rejections still reduce availability,
and initial CEL12 exposed an adversarial priority false positive. Review the report;
this is not a claim that every category, priority or semantic judgment is reliable.

## B. DO NOT COMMIT

The following task-local files are private audit bookkeeping, generated SQLite QA
storage, source snapshots or duplicate diagnostics, covered by `.cache/` (and
`*.db` for databases). They are unnecessary for the public application/report:

- `.cache/milestone5c/baseline-lock.json`
- `.cache/milestone5c/classification_rules.v1.py.before`
- `.cache/milestone5c/classifier.py.before`
- `.cache/milestone5c/commit-scan.json`
- `.cache/milestone5c/customer_data.py.before`
- `.cache/milestone5c/evaluation-v1.db`
- `.cache/milestone5c/followup-v2/evaluation-v1.db`
- `.cache/milestone5c/followup-v2/original-fingerprints.json`
- `.cache/milestone5c/original-fingerprints.json`
- `.cache/milestone5c/reply_generator.py.before`
- `.cache/milestone5c/runner.v1.py.before`

The retained 5B `.cache/milestone5b/` directory likewise contains generated QA data,
private original-record fingerprints and temporary review copies; keep it local.
Other exact local-only paths: `.env` (private configuration), `data/opspilot.db`
(original records), `data/backups/`, `backend/.venv/`, `frontend/node_modules/`,
`backend/.pytest-tmp/`, `backend/.pytest_cache/`, `backend/app/__pycache__/`,
`backend/benchmarks/__pycache__/`, `backend/tests/__pycache__/`, `frontend/dist/`.
These directories cover generated bytecode/dependency/test artifacts individually;
none are proposed for Git. Ignore coverage was verified.

## C. MANUAL REVIEW

- `docs/milestone5/hardware-supplement-v1.json` ? unchanged but already tracked
  workstation profile (CPU family/threads, RAM, GPU and driver). Review publication
  privacy; ignore rules cannot remove tracked content. It was not deleted or modified.

No other changed/new files require privacy review based on this inspection.

## Actual checks and boundaries

- All proposed files were read/reviewed and scanned for common private/API keys,
  bearer values, credential assignments, emails, user-home and absolute workspace
  paths. No candidate secrets, real customer data or personal machine paths were
  found. Adversarial requests for secrets are fictional test inputs, not secrets.
- `git ls-files -ci --exclude-standard` returned no tracked ignored artifacts.
  `git check-ignore` confirmed local database/cache/environment/dependency coverage.
  No `.gitignore` change was necessary. The hardware profile above is tracked and
  explicitly flagged rather than incorrectly assumed protected by ignore rules.
- Raw model evidence is synthetic and of modest size; retaining both experiments
  is necessary to avoid hiding failures. Databases, source snapshots, bytecode and
  temporary inspection copies are unnecessary generated artifacts and remain local.
- No new hardware probe or external account access occurred. Model metadata contains
  the public model identifier/digest and timestamps, not credentials/hostnames.
- Original database fingerprints and every original 5A/5B evidence hash match the
  pre-work lock. Final source/expectation freeze verification passes.

**Recommended commit message:**
`Correct bilingual summaries and safety triage; version the ETA evaluation fix`

Stop after Milestone 5C. No presentation work or later milestone was started.
