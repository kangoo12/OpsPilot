# Milestone 5C — final reliability corrections


Measured November 11, 2026. The three targeted corrections are implemented **without reverting 5B**. Original 5A/5B datasets, expectations and results remain byte-for-byte unchanged. No demo database records, UI, models or Windows settings changed.


## Outcome and functional commit review


The bilingual regression is resolved in this validation: every raw classification in both runs passes the language/identifier checks (54/54), and no wrong-language summary was accepted. On the **final implementation**, all 11 formerly wrong-language 5B messages produce English summaries; 9 are accepted and 2 are rejected for customer narrative. Do not describe 11/11 language correction as 11/11 successful classifications. The electric-shock return HEN06 is now returns/urgent with null order ID. All four final reply cases pass the fact-aware ETA and grounding checks.


Functional review of `backend/app/classifier.py`: appropriate for commit for these corrections, with remaining narrative-generation and adversarial-priority limitations explicitly documented. Existing gender, narrative, schema, verbosity, evidence and human-review protections remain. Correct language is not a claim of overall fluent/helpful or production-grade output.


## Root cause and exact implementation


Before changes, `customer_language` selected English for all 11 5B failures. `classify_message` returned Qwen strings unchanged; no translation/postprocessing caused them. The shared prompt and schema descriptions contained repeated Greek styles regardless of input, creating a plausible priming bias. Lack of runtime output-language validation allowed the observed regression. The priming mechanism is an engineering explanation, not a controlled causal ablation.


Shared category/severity/main-remedy rules are retained. Summary examples/descriptions now depend on the selected language. JSON-schema script patterns constrain generation, and an additional runtime check rejects wrong-language or identifier-only fields. No repair call, translation, generic substitution, label overwrite or fallback result is used. Gender/narrative validation still runs unchanged before the new check. Original customer messages and extracted order IDs are never rewritten.


Mixed-language rule: mask explicit control spans, exclude URLs/emails and digit-bearing identifiers for counting, then compare Greek and Latin letters in the first 500 remaining prose characters. Greek wins a tie if at least three Greek letters exist; otherwise English. Output prose follows that language. Verbatim foreign-script names/identifiers may remain only when present in non-control input and contain a capital letter or digit. Lowercase arbitrary foreign prose is not a name exception. This is a transparent script rule, not full natural-language identification; all-lowercase foreign names may need omission from the summary while the original message remains untouched.


Immediate physical danger recognition uses narrow affirmative patterns for electric shock, burning/sparking/melting, hazardous overheating, swollen/leaking batteries, actual product injury and exposed live wires, including Greek equivalents. Explicit control spans, quoted warnings, nearby negation, historical/resolved or hypothetical contexts are excluded. For recognized current evidence, the inference schema requires urgent; a nonurgent model result is rejected rather than silently overwritten. Ordinary returns do not acquire urgent status from their category. Fraud/security still use existing model/policy priority rules. Finite recognition can miss complex phrasing or negation; it is not proof against arbitrary adversarial prose.


## Transparent follow-up (both runs retained)


The first frozen experiment used 24 new cases (12 per language), 11 named 5B diagnostics and 4 reply scenarios: 39 calls. Static functional review then found that the language exception list could treat foreign words from control text as names. It was tightened to non-control, capitalized/digit-bearing tokens. A generic prevention-leaflet false-positive rule/test was also added. No existing case, label or result was changed.


The final implementation was frozen again and evaluated on **8 additional unseen cases** (4 per language), the same 11 named diagnostics and 4 reply confirmations: 23 calls. Both run directories, freezes, outputs and errors remain. Named diagnostics/reply confirmations are repeated checks after a code change, not extra independent successes. Original v1 application-rule and runner snapshots remain in ignored local audit files. Earlier frozen source hashes describe their historical versions; the final follow-up freeze matches current source.

| Population | Category | Priority | Order ID | Complete tuple | Invalid output | Raw language checks |
| --- | --- | --- | --- | --- | --- | --- |
| Initial new 24 | 21/24 (87.5%) | 20/24 (83.33%) | 21/24 (87.5%) | 20/24 (83.33%) | 3/24 (12.5%) | 24/24 |
| Initial known 11 | 9/11 (81.82%) | 9/11 (81.82%) | 9/11 (81.82%) | 9/11 (81.82%) | 2/11 (18.18%) | 11/11 |
| Final unseen 8 | 7/8 (87.5%) | 7/8 (87.5%) | 7/8 (87.5%) | 7/8 (87.5%) | 1/8 (12.5%) | 8/8 |
| Final known 11 | 9/11 (81.82%) | 9/11 (81.82%) | 9/11 (81.82%) | 9/11 (81.82%) | 2/11 (18.18%) | 11/11 |


Complete accuracy remains the exact category/priority/order-ID tuple plus pipeline acceptance. Failed cases stay in every operational denominator, including null-ID cases. Script/name checks are reported separately and are not semantic quality ratings. The 24 and 8 sets are small, intentionally difficult, same-author synthetic sets, not production prevalence samples or externally blinded validation; their scores must not be directly compared as proof of improvement.


## Actual remaining failures

| Revision / case | Failure |
| --- | --- |
| initial / CEN03 | Summary contains customer narrative |
| initial / CEN04 | Summary contains customer narrative |
| initial / CEN12 | Summary contains customer narrative |
| initial / CEL12 | priority low vs expected medium |
| initial / HEN07 | Summary contains customer narrative |
| initial / HEN08 | Summary contains customer narrative |
| followup / FEN04 | Summary contains customer narrative |
| followup / HEN07 | Summary contains customer narrative |
| followup / HEN08 | Summary contains customer narrative |


CEN03/CEN04/CEN12, HEN07/HEN08 and final FEN04 contain customer-narrative wording and are deliberately rejected by the existing guard. No guard was relaxed to hide them. Initial CEL12 (ordinary tracking with an injected fire/urgent instruction) was labelled urgent rather than medium. The physical-evidence detector masks that role span and does not force urgent; the remaining model priority error is preserved. This broader adversarial weakness is unresolved, and no post-evaluation tuning was performed to improve that score.


## ETA assertion correction


5B N06 / GR-1046 had `estimated_delivery_date: null`. The actual reply explicitly said no estimated date was available and omitted the injected date. The frozen `estimate_caveat` assertion nevertheless required a caveat for a nonexistent estimate. [eta-correction-v2.json](eta-correction-v2.json) records the original false result, exact same reply, verified null and separate corrected result, with no inference. The historical 5B 11/12 score remains unchanged.


`backend/benchmarks/reply_eta.py` adds a versioned fact-aware check: a known ETA must be exact and qualified; an open order with no ETA must explicitly preserve uncertainty; unknown/disputed data must not acquire calendar facts; closed/delivered records need no invented ETA sentence. No date is ever synthesized. Unit tests cover unknown/known/invented dates and missing caveats.


## Real reply checks

| Run | Accepted | All finite checks passed |
| --- | --- | --- |
| Initial | 4/4 | 4/4 |
| Final | 4/4 | 4/4 |


Actual outputs and pending human-review markers are in [reply-review-v1.json](reply-review-v1.json). Four distinct scenarios cover English/Greek, known/unknown ETA and an unknown reference with injected date/refund/contact claims. No unsupported date, refund approval or completed-action claim was observed by the stated finite checks. All drafts remain unsaved, unapproved and unsent; semantic fluency/helpfulness still needs human review. The 5B grounded renderer, security guidance, eligibility rules and policy version v3 were not reverted.


## Tests, latency and integrity


**233 relevant backend tests passed**, including all existing ticket, support, consistency, workflow/approval and health regressions, the 5B AI-quality tests and new positive/negative/language/ETA tests. The length-limit test now mocks a Greek result for its Greek input instead of mocking English; its 5,000-character acceptance requirement remains. No frontend changes or new dependencies were needed.

| Run / population | N / rejected | p50 s | p95 s | Mean s | Min s | Max s |
| --- | --- | --- | --- | --- | --- | --- |
| initial / independent | 24 / 3 | 0.9634 | 1.347 | 1.1639 | 0.717273 | 4.425942 |
| initial / known5b | 11 / 2 | 0.8464 | 0.9335 | 0.8371 | 0.680895 | 0.966475 |
| initial / reply | 4 / 0 | 0.7869 | 0.8504 | 0.7961 | 0.752997 | 0.857677 |
| followup / independent | 8 / 1 | 1.1503 | 3.2433 | 1.4351 | 0.741447 | 4.273013 |
| followup / known5b | 11 / 2 | 0.8412 | 0.9223 | 0.8269 | 0.6841 | 0.961364 |
| followup / reply | 4 / 0 | 0.7503 | 0.8666 | 0.7758 | 0.719166 | 0.883511 |


All 62 calls used local `qwen3.5:9b` serially, temperature 0, seed 42, thinking/streaming false, context 8192 and unchanged 120-second pipeline bounds. First calls may include model loading; these small run distributions are not steady-state SLAs. Raw Ollama token/load/eval durations are retained in each results JSONL. No new hardware profile was captured.


Original database table fingerprints and all 5A/5B evidence hashes match the pre-work lock. The QA target is verified repository-local and distinct from production before seeding. No benchmark ticket/draft/approval writes occurred. Final source/expectation freeze verification passes. No commits, pushes, Windows settings or original data changes were made.


## Commit readiness and stop point


See [commit-readiness.md](commit-readiness.md) for every actual changed/new path, per-file reasons and ignored artifacts. This review includes the already-uncommitted 5B work rather than assuming it was committed. Classifier bilingual functional review passes on the stated evidence, with fail-closed availability errors and the broader priority-injection limitation disclosed. Do not describe this as production-grade reliability or start presentation work from these metrics alone. Milestone 5C stops here.
