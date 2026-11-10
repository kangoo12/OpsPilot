# Milestone 3B — human approval and ticket workflow

Implemented and verified locally on November 10, 2026 in `F:\Projects\OpsPilot`.

## Implemented behavior

- Pending replies can be edited and saved with versioned content history.
- Approval/rejection require explicit confirmation. Rejection requires a reason.
- All decisions retain reviewer identity, modification time and decision time.
- Approving sends nothing and does not change the ticket's status.
- Approved content is immutable. Editing approved or rejected content creates a
  new pending draft with a parent link; original content and decisions remain.
- Regeneration invokes local `qwen3.5:9b` and creates a separate pending draft.
- Manual ticket states support New → In Progress → Waiting for Customer / Resolved,
  Waiting for Customer → In Progress / Resolved, and Resolved → In Progress.
- Current discrepancies and missing order information require a reasoned human
  review before approval. The recorded reason remains visible alongside the warning.
- Review documentation is bound to a context fingerprint. Order changes invalidate
  earlier documentation. It never approves unsupported claims or changes order data.
- API guards still reject recognized contradictory facts, unverified dates and
  unperformed actions, even after the operator documents a discrepancy.
- Persistent activity/revision histories record all required operations.

The fixed actor **Local Operator** is a local demo identity, not authentication.
There is no email sending, real refund handling, external integration or deployment.

## Data integrity and migration

Migration version 1 adds workflow tables alongside the original tables. It does
not rebuild or overwrite historical ticket/draft/order records. A consistent
SQLite backup is created before upgrading an existing database; schema and
backfill changes are committed atomically. Failure rolls them back. Repeated
startup does not duplicate backfill history or create another upgrade backup.

Current workflow status lives in `ticketworkflow` and `draftreview`; original
`ticket` / `replydraft` snapshot values remain unchanged. Original draft content,
revisions, audit records and resolution documentation are immutable in SQLite;
approved review rows also have database protection against modification/deletion.

Workflow updates lock briefly and compare mandatory versions. Approval, editing,
regeneration and human review also check the context fingerprint. Duplicate
approval and stale updates receive HTTP 409. No write transaction spans inference.

Historical creation events use original timestamps and actor `Historical import`.
Missing historical correction timestamps are explicitly unknown, not fabricated.
Audit entries contain IDs, versions, necessary reasons and change summaries, not
copies of customer messages or credentials. Required draft revision content stays
in the revision history.

The original demo table fingerprints before and after implementation are equal:

| Original table | Rows | SHA-256 |
| --- | ---: | --- |
| ticket | 5 | `0910f3e019e2d23eade7d2c0ffd2f91cb2203b5d9afb58082ff4a8ed46496357` |
| replydraft | 1 | `aae14b631ffafaac01b15dd66247f1c5337e8b53a5ba1d3f216e9f14fe301140` |
| order | 19 | `8d2890151945005df5e6438d966922aa722d8de983b6e60a7fc20350c316fc22` |
| ticketorderreference | 0 | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |

The existing backend's normal reload created a pre-upgrade backup under
`data/backups/`. All automated browser actions targeted only
`data/milestone3b-qa.db`, via isolated ports 8010/5180. The test refuses to proceed
if the backend does not identify that dedicated QA database.

## Verification

- **171 backend tests**: existing functionality plus draft editing/saving,
  approval/rejection, required reasons, regeneration, approved-content forks,
  revision history, duplicate/concurrent approval, stale edits/status changes,
  allowed transitions/reopening, audit persistence/immutability, discrepancy
  documentation and backend bypass attempts. Migration tests cover a legacy 3A
  schema, unchanged historical rows, backup creation, idempotency and rollback.
- **52 frontend tests**: existing features plus editor states, save requests,
  action confirmations/cancellation, rejection reasons, approval blockers,
  retained stale edits, approved-content revision creation, revision history,
  status transitions/reopening, review documentation and activity loading.
- Production build and Python dependency checks pass.
- Real local Qwen + Edge browser smoke passes: editing and approving; unchanged
  ticket status after approval; a pending child of an approved draft; rejection
  with a reason; regeneration; all transitions and reopening; timeline display;
  discrepancy approval blocked at the API; documented review with a persistent
  warning; unsupported human-edited claims still blocked; reload persistence;
  desktop and 390px mobile layout. No browser errors or horizontal overflow.

Full synthetic evidence: [milestone3b-smoke.json](milestone3b-smoke.json).
Local screenshots: `.cache/smoke3b/approved.png`, `desktop.png`, `mobile.png`.
Startup, API and isolated-test commands are in [README.md](../README.md).

## Practical limits

Human review is still required. Rule-based language/fact checks are not a proof
of the semantic correctness of arbitrary manually written prose. The demo identity
does not authenticate users or restrict different people who can reach the local
API. The interface shows the latest 20 draft IDs; full revisions and paginated
activity remain available through their APIs. Older order-correction clients may
omit an optimistic fingerprint for compatibility; workflow approvals and edits
always require their own version/context preconditions.

No production ticket data was deleted or reset. No Git commits or pushes were made.
