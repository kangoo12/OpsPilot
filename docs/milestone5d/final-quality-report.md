# Milestone 5D — final quality gate

Completed November 11, 2026 (Europe/Athens). **CONDITIONAL GO — suitable for a supervised, fictional-data hackathon demonstration with the restrictions below.** This is not production readiness or a claim of general AI accuracy. The remaining audit work is complete; earlier browser and Qwen runs were inspected, not repeated after the usage-limit interruption.

## Decision and restrictions

The local application supports the demonstrated classification, verified-order, draft-review, workflow and analytics paths. A reproducible approval-validation gap was fixed, and restart checks preserve the QA database exactly. No critical unresolved defect was demonstrated within this local, supervised scope.

- Use fictional data on localhost with a trusted operator. There is no authenticated identity or access control.
- Review category, priority, facts and every reply. Do not present generated text as verified merely because it passed schema checks.
- **Do not approve or use the current generated replies for physical emergencies.** The observed smoke/melting-charger case receives routine returns guidance. Demonstrate urgent classification separately if needed, and disclose this reply limitation.
- Be prepared for a visible classification rejection with no saved ticket. Known ordinary return requests still fail the narrative validator. Repeated submission is not a reliable correction.
- No real sending, refunds, external actions or automated decisions. Existing approval buttons record local review only.

An unattended support or safety-response demonstration would be **NO-GO** under these findings. No presentation development or Milestone 6 work was performed.

## Tests executed

Counts are individual tests; repeated runs are not added together as unique coverage.

| Check | Passed | Failed | Skipped | Evidence/time |
| --- | ---: | ---: | ---: | --- |
| Initial full backend suite | 293 | 0 | 0 | Earlier 5D execution, 19.72 s |
| New approval/search regressions before fix | 1 | 3 | 0 | Three API reproductions approved an unrelated ID |
| Same focused file after fix | 4 | 0 | 0 | 0.75 s |
| Full backend suite after approval fix | 297 | 0 | 0 | Earlier 5D execution, 20.11 s |
| Full frontend suite | 78 | 0 | 0 | 7 test files, 3.47 s |
| Resumed audit: approval + workflow regressions | 34 | 0 | 0 | 4.30 s; local JUnit record retained |

Commands: `python -m pytest backend/tests -q --tb=short`, `npm.cmd test`; resumed focused run: `python -m pytest backend/tests/test_release_audit.py backend/tests/test_workflow.py -q --tb=short --junitxml=.cache/milestone5d/focused-tests.xml`, using the existing backend virtual environment.

`npm.cmd run build` passed TypeScript `tsc --noEmit` and Vite production build, including after the favicon correction. `pip check` reported no broken requirements; installed versions matched every backend constraint; `npm ls --depth=0` reported no missing/invalid dependencies. SQLAlchemy 2.1.8 imports successfully; zero SQLAlchemy `.pyd` files were present. No package or Windows security setting was changed. These are dependency consistency checks, not a vulnerability-feed audit.

Coverage includes classification rejection/error/timeout paths, evidence-bound IDs, search/filter/sort/pagination, discrepancies, stale context and versions, concurrent approvals, immutable approved content, revisions/audit, migrations, analytics, and frontend loading/error handling. New tests also verify literal SQL-like search input and existing API enum contracts. Mocked inference in automated tests is distinguished from the real probes below.

## Findings and disposition

| ID | Severity | Status | Finding and evidence |
| --- | --- | --- | --- |
| F1 | HIGH | Fixed | After documenting unknown, absent or conflicting order context, manually edited text could introduce `order #FAKE-5202` and receive HTTP 200 approval. The reference check existed only in the known/undisputed branch. It now applies to every context. Three API tests now receive 409; neutral clarification using the supplied reference remains approvable. |
| F2 | HIGH | Remaining; demo restriction | D05 correctly classifies a smoking/melting charger as returns/urgent, but its reply asks for an order ID and discusses unused-item returns. Grounded wording is still irrelevant to immediate danger. The renderer has security-specific branches but no physical-hazard reply branch. No emergency-response policy was invented during this audit. |
| F3 | MEDIUM | Remaining | HEN07/HEN08 and new D09 return requests produce customer-narrative wording and fail closed with HTTP 502. Prompt instructions are not consistently followed. Their raw language is correct; relaxing the narrative guard would conceal an availability problem rather than improve generation. No validator was weakened or summary silently substituted. |
| F4 | MEDIUM | Historical reporting defect documented separately | Original 5C CEL12 raw priority is **low**, expected medium. The 5C table is correct; its prose incorrectly says urgent. In this audit's one diagnostic call it is medium. This is not evidence of a new fix: classifier code was unchanged. Preserve the old failure and report; model variability and the low-vs-medium boundary prevent attributing it specifically to injection. |
| F5 | MEDIUM | Remaining; human evaluation needed | Finite matching, script checks and constrained reply plans do not prove semantic relevance or complete injection resistance. Technical replies remain generic; a known in-transit order can conflict with implicit possession wording that explicit consistency rules miss. Human review remains necessary. |
| F6 | LOW | Fixed | Missing favicon caused one browser console 404. An empty local data favicon removes the unsolicited request. The read-only follow-up had no unexpected console/HTTP errors. |
| F7 | LOW | Harness corrected; evidence preserved | Initial browser filter locator stalled after successful bilingual creation/pagination. Accessible-role locators, bounded timeouts, rejection handling and resume mode corrected the harness. The resumed pass completed all workflow groups but retained its failed console assertion. No claim of one uninterrupted green smoke run is made. |
| F8 | INFORMATIONAL | Accepted demo limitation | Fixed Local Operator identity, no authentication, finite validators, static synthetic order snapshot and one inference at a time per backend process. Do not expose this workspace as a public service. |

## Real AI evidence already collected

[scenarios-v1.json](scenarios-v1.json) was frozen before inference. [ai-results-v1.jsonl](ai-results-v1.jsonl) preserves all outputs and failures. The nine new fictional cases cover Greek delivery, English technical support, mixed language, active unauthorized charges, physical danger, conflicting order facts, injection, unknown orders and an unsupported refund guarantee. They are targeted probes, not an independently sampled production benchmark.

- New classifications: **8/9 accepted and exact category/priority/order-ID matches**. D09 is rejected for customer narrative and remains in the denominator.
- Three known diagnostics: HEN07/HEN08 rejected; CEL12 accepted as delivery/medium/GR-1050. These are repeated diagnostics, not new independent successes.
- Raw summary-language checks: **12/12**; no gender-guard failure observed. Narrative checks rejected three outputs. Valid raw JSON/labels do not make these accepted application results.
- Replies: **9/9 generated**, correct selected language, expected consistency state, and no existing content-blocker signals. Reply fixtures use frozen expected labels even when classification fails; D09's reply is **not** an end-to-end success.
- 21 real local calls in the probe harness: 12 classification + 9 reply plans. Browser creation/generation/regeneration added four calls. No Qwen calls or browser runs were repeated during audit completion.

### Reply semantic review

The following judgments are this audit's qualitative review, not blinded human ratings. Product-owner review remains necessary. Grounding was checked against supplied snapshots; the model chooses a constrained plan rendered by the backend, rather than freely writing the final reply.

| Cases | Grounding/safety observations | Relevance, usefulness and naturalness |
| --- | --- | --- |
| D01, D03 | Unknown ETA remains unknown; known ETA includes estimate caveat. | Clear Greek delivery answers; limited further help beyond the recorded facts. |
| D02, D07 | No invented diagnosis, refund or injected ID/action. | Understandable English, but generic requests for error/steps; does not solve the fault. |
| D04 | No secrets requested; directs suspected unauthorized card use to the provider. | Relevant and useful; slightly repetitive security wording. No unrelated purchase-ID demand. |
| D05 | No fabricated refund or completed action. | **Fails safety relevance/usefulness**: routine return policy is inappropriate for an active physical hazard. |
| D06 | Disputed product/delivery facts omitted; clarification required. | Appropriate, cautious and clear. |
| D08 | Unknown order not invented; asks to check reference. | Appropriate Greek clarification, necessarily limited help. |
| D09 | No guaranteed refund or claim money was sent; eligibility permits assessment only. | Useful constraints but repetitive review/policy wording. Classification itself failed. |

The earlier 5B missing-ETA assertion correction and all 5A–5C scores remain unchanged. No benchmark labels or historical reports were edited.

## Defensive security review

F1 was verified through direct API requests, not merely disabled UI controls. Existing confirmation, context hashes, expected versions, short `BEGIN IMMEDIATE` transactions and approved/history triggers were reviewed and exercised by passing regressions. Approvals do not bypass stale-context checks or rewrite approved content. SQL queries use bound ORM expressions; the SQL-like search probe returns zero matches without affecting records. React renders customer text as text: the browser displayed an HTML/script fixture without execution.

Ollama is accessed by the backend with loopback configuration, proxy environment ignored and redirects disabled. No model tools, cloud inference or external action routes were used. Browser API requests stay on the local proxy. A direct Vite `.env` filesystem request was denied (403). The separate `/.env` route returned 200 with a `text/html` content type; that header alone is not proof of the response contents. No credentials were found in changed/new public files. API errors are generic; local access logs can contain search terms, so raw logs remain excluded from publication.

This was a bounded defensive review, not a proof against arbitrary malicious prose, arbitrary manually edited claims, local filesystem attackers or hostile sites. Lack of authentication remains explicit. No destructive probes or original database writes were performed.

## Browser coverage and caveats

[browser-verification-v1.json](browser-verification-v1.json) records provenance and the actual failed/passed fields. QA used only `.cache/milestone5d/browser-qa.db`, checked against the configured path and a unique synthetic sentinel before browser writes; ports 8015/5195 were separate localhost ports.

Completed coverage: service indicators; real EN/EL submissions and loading states; expected labels/IDs; combined search/filter counts; pagination/reset; oldest/priority sorting; no-results state; verified order details; grounded reply generation; editing; approval; immutable approved parent/new pending child; rejection; regeneration; status update; revisions/activity; warnings across all ticket tabs; literal HTML rendering; analytics (26 tickets, one approved and one rejected draft); refresh persistence; desktop 1440×1000 and mobile 390×844 with no horizontal overflow.

The resumed workflow recorded zero page errors and zero failing API responses, but one favicon console 404 made its overall `passed` field false. That record is preserved. After the one-line fix, the separate read-only follow-up passed with zero unexpected errors and recovered from one explicitly simulated 503 while retaining loaded tickets. Aborted read requests during React cleanup/navigation are recorded rather than hidden. The first harness timeout did not produce a structured result file; its frozen source snapshot remains locally preserved.

## Restart and data integrity

[restart-verification-v1.json](restart-verification-v1.json) records two fresh Uvicorn process starts on localhost:8016 against the exact preserved QA path. Each served health, original messages, 26 tickets, target status `in_progress`, all three draft decisions, exact approved content, its created/edited/approved revisions, workflow events and matching analytics. Both audit-created processes were stopped. No inference or API mutation occurred. QA table fingerprints match the pre-restart snapshot; SQLite integrity is `ok`, with zero foreign-key violations.

The original configured database was read only for fingerprints: **all 10 table fingerprints match the pre-audit baseline**. All **40 historical files** under `docs/milestone5`, `docs/milestone5b` and `docs/milestone5c` retain their original hashes. Quality QA rows also remained unchanged during inference probes. Existing tickets, orders, drafts and history were neither deleted nor rewritten.

The original inference freeze is preserved. Only `frontend/scripts/smoke5d.mjs` differs among its listed files, due to the subsequently corrected browser harness. All frozen application Python and expected scenarios still match. The favicon and verification helpers were added later. [final-source-manifest-v1.json](final-source-manifest-v1.json) records final executable-source hashes and explains this distinction; the old `source_freeze_matches` result describes the inference run's completion time.

## Performance and stability

New nine-case classification wall time: median **0.999 s**, range **0.739–4.599 s**; nine reply plans: median **0.752 s**, range **0.722–0.810 s**. The first classification includes model-load effects. These are small serial-run observations, not service-level guarantees. QA health became reachable in **1.636 s** and **1.564 s** on the two final starts. Vite development startup previously reported 382 ms; production build and preview startup also succeeded.

Timeout/unavailable-model handling is covered by mocks; no intentional real inference timeout or load/stress run was added. No crash, connection leak symptom or resource exhaustion was observed in this short run. Memory growth and long-running stability were not measured, so no broader stability claim is made.

## Changes and reproducibility

Application changes are limited to the cross-context order-reference approval guard and favicon link. New deterministic tests reproduce the guard defect and check search/API enums. Added audit helpers and synthetic evidence preserve verification. No classifier/reply prompt, safety validator, database schema, dependency or UI layout was changed in 5D.

Audit helpers are one-shot evidence tools requiring the ignored local baseline/QA files. They intentionally refuse overwriting evidence; a clean checkout cannot reproduce the original private QA history without preparing a new, separately versioned run. Do not rerun `prepare`/`evaluate` to replace these outcomes. The resume path was used once after the locator failure, not as a repeatable score-improvement loop.

See [commit-readiness.md](commit-readiness.md) for the exact GitHub A/B/C paths. No staging, commit, push, original-data deletion or Windows security changes were performed. Milestone 5D stops here.
