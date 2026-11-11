# Final hackathon release checklist

Checked items below identify their evidence/scope. Unchecked items are pending operator decisions or event-time verification, not failed tests silently omitted. Current decision remains **CONDITIONAL GO for supervised fictional data**. No production roadmap functionality is implemented.

## Package and evidence

- [x] Portfolio README rewritten; entrypoints, PowerShell commands and isolated demo database are documented.
- [x] Architecture, benchmark summary, 3–5 minute demo, pitch, Q&A and staged production roadmap written.
- [x] Five real 1440×1100 screenshots reviewed; all visible data is fictional QA data. [Provenance](screenshots/README.md).
- [x] Static local documentation links/anchors and balanced fences checked by `backend/scripts/check_launch_docs.py` (see [verification](verification.json) for final counts).
- [x] Mermaid flowcharts reviewed and checked for basic header/subgraph structure; no renderer dependency was installed.
- [ ] Confirm rendered Markdown/Mermaid layout on the intended GitHub preview after the owner's manual publication. Basic source checks do not certify rendering.
- [x] Known HIGH physical-danger reply usefulness and MEDIUM narrative/semantic limitations remain visible in README, demo and benchmark summary.
- [x] Original database's 10 table fingerprints and all 50 historical 5A–5D public evidence files match the Milestone 6 baseline.
- [x] Publication review covers actual changed/new files, screenshots, ignore coverage and tracked ignored artifacts. [Exact paths](commit-readiness.md).
- [ ] Owner decides whether to publish the already-tracked hardware supplement.
- [ ] Owner chooses project license; no license/open-source status is claimed without one.
- [ ] Owner manually reviews changes, commits selected files and confirms clean Git status. No agent stage/commit/push was performed.

## Application and isolated demo

- [x] Exact root-based quick-start Uvicorn entrypoint starts against `.cache/milestone6/live-demo.db` on localhost:8018.
- [x] Documented Vite proxy starts on localhost:5197; frontend and proxied API/storage health return HTTP 200.
- [x] Proxied Ollama health returns HTTP 200 and confirms installed `qwen3.5:9b`; no new model generation was requested.
- [x] Fresh isolated demo contains 19 fictional orders and zero tickets. This is intentional: the live submission creates the demonstration ticket.
- [x] The chosen delivery input and its completed review/history flow were exercised in 5D; source/evidence unchanged. Screenshot QA includes saved example tickets/drafts.
- [x] Milestone 6 read-only screenshot browser capture completed with zero page/API errors, inference calls or API mutations. Screenshot-QA table fingerprints unchanged.
- [x] Approval, immutable approved content, revision/history, analytics and responsive layouts have historical 5D evidence; no full flow/AI benchmark was unnecessarily repeated here.
- [x] Recorded screenshot backup is available and clearly labelled as historical QA evidence, not live inference.
- [ ] Presenter performs a timed end-to-end rehearsal on the chosen isolated live-demo database. This milestone did not repeat the real-model submission/approval sequence.
- [ ] If seeded tickets are required before the event, presenter submits the documented fictional case during rehearsal; do not silently preload fake live-AI results.
- [ ] On event day, confirm ports/path, both green status badges, model readiness, screen readability and backup images. Current reachability does not guarantee future availability or warmed inference.
- [ ] Presenter practices the visible-error/uncertain-write branch without weakening validation or inventing successful output.
- [ ] Confirm no HIGH physical-danger reply is approved or used, and no real customer data or sending/refund action enters the demo.

## Completion boundary

The technical launch package is complete with the documented verification limitations. Human rehearsal, licensing, publication decisions and event-day preflight remain. Real customers/public deployment require the [future Stage 0/1/2 gates](production-roadmap.md), not this checklist alone. Stop at Milestone 6; do not implement the roadmap as part of release preparation.
