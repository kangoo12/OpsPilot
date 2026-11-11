# Milestone 4.5 validation

Implemented in `F:\Projects\OpsPilot` and verified on November 11, 2026.

## Delivered

- Server-side newest/oldest, high/low priority and recently updated sorting, with
  enum-like validation, deterministic ties, existing search/filters and pagination.
- Compact application navigation, Smart Inbox, a collapsible message composer and
  a bounded scrollable ticket list. Search/filter/sort controls remain above the list.
- Overview, Order Details, AI Reply and Activity History tabs reuse the existing
  ticket, order, workflow, editor and revision components. Keyboard arrows/Home/End
  navigate tabs. Draft edits and selected ticket persist across tabs and application
  navigation. Critical current/historical consistency warnings stay visible.
- Read-only `/api/analytics?days=30`, with SQL aggregation and streamed consistency
  checks. Metrics include category, priority, current status, new/resolved, human
  review, unique draft decisions, UTC daily volume and reliable resolution duration.
- Responsive analytics with count labels, distribution bars, daily volume chart
  and accessible daily table, honest empty/loading/error states and refresh.

Metric definitions and exact API/startup/QA commands are in [README](../README.md).
No schema changes or additional dependencies were needed. AI inference remains
local through Ollama `qwen3.5:9b`. Existing approval guards and immutability remain.

## Verification

- **83 targeted backend tests passed**: sorting, filters, search, analytics and
  existing human workflow regressions, including API approval restrictions.
- **78 frontend tests passed** across seven relevant files: dashboard/API, order
  and reply components, approval/workflow, application navigation and analytics.
- TypeScript checking and production frontend build passed.
- **One isolated Edge browser smoke run passed**, guarded by unique QA seed data
  before writes. It used only ports 8015/5185 and `.cache/milestone45/qa.db`.
  The synthetic dataset contained 27 tickets and known draft-decision fixtures.
- The browser verified combined search/filter/sort/counts; ticket tabs; a real
  local Qwen reply; preserving unsaved edits across tabs and Analytics navigation;
  saving/approving, the unchanged ticket status, immutable approved display and
  activity; analytics reporting two approved/one rejected drafts; desktop and
  390px mobile layouts with no horizontal overflow or browser errors.
- The browser screenshot review found a stale static sort subtitle; it now uses
  the selected sort label. The focused dashboard/API checks and build were rerun.
- Read-only fingerprints of **all 10 normal database tables** match before/after.
  Tickets, orders, drafts, references, workflow records, audit and revision history
  were neither modified nor deleted by the automated tests.

Evidence: [browser results and actual Qwen draft](milestone45-smoke.json),
[table fingerprints](milestone45-data-integrity.json).
Screenshots remain ignored in `.cache/milestone45/{desktop,mobile}-{inbox,analytics}.png`.

## Files changed

- Backend: `app/tickets.py`, `app/main.py`, new `app/analytics.py`;
  new `tests/test_ticket_sorting.py`, `tests/test_analytics.py` and
  `scripts/seed_milestone45_qa.py`.
- Frontend: `src/App.tsx`, `src/TicketDashboard.tsx`, `src/TicketSupport.tsx`,
  `src/TicketWorkflowPanel.tsx`, `src/api.ts`; new `src/WorkspaceTabs.tsx` and
  `src/AnalyticsDashboard.tsx`.
- Frontend tests: updated `src/TicketDashboard.test.tsx`,
  `src/TicketSupport.test.tsx`, `src/api.test.ts`; new `src/App.test.tsx` and
  `src/AnalyticsDashboard.test.tsx`.
- Browser verification: new `scripts/smoke45.mjs`, `package.json` script.
- Documentation: `README.md` and this report with the two evidence JSON files.

## Remaining limits

No known blocking bugs remain. Recently updated means recorded audit activity,
excluding historical reference imports with unknown original times. Analytics
cannot reconstruct missing historical resolution timestamps; these are labelled
unavailable. Resolution duration includes elapsed reopened periods and excludes
tickets that are currently reopened. Charts default to the last 30 UTC dates;
KPI totals are all-time. Human review uses the existing conservative consistency
rules, not an unrestricted semantic proof. QA data is kept separate and is never
merged into normal metrics. Selecting a different ticket opens its own workspace;
navigation within the current ticket preserves edits.

No Windows settings, Git commits, pushes, external integrations or real-world
actions were introduced. Milestone 5 was not implemented.
