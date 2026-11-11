# OpsPilot Milestone 5B — targeted improvements and frozen validation


Completed November 11, 2026. **40 new held-out classifications, 60 development-set reruns and 12 new replies**, each exactly once; zero retries. Implementation and expectations were frozen before inference. No post-evaluation tuning, ground-truth edits or failed-case removal.


## Executive conclusion


Label reliability improved, but **do not call the bilingual hackathon demo ready without qualification**. The frozen implementation regressed summary-language consistency: many English inputs receive Greek summaries. One held-out immediate electric-shock return is still high rather than urgent. Keep operator review; no autonomous handling or production-grade reliability is claimed.


A restricted supervised demonstration can show the grounded reply and workflow improvements, with these defects disclosed. A bilingual quality claim needs a later implementation fix and a fresh unseen evaluation; this run must not be reused as a new holdout after tuning.

| Metric | 5A baseline (same original 60) | 5B development (original 60) | 5B held-out (new 40) |
| --- | --- | --- | --- |
| Category | 48/60 (80.0%) | 57/60 (95.0%) | 40/40 (100.0%) |
| Priority | 45/60 (75.0%) | 58/60 (96.67%) | 39/40 (97.5%) |
| Order ID | 49/60 (81.67%) | 57/60 (95.0%) | 40/40 (100.0%) |
| Complete label tuple | 43/60 (71.67%) | 56/60 (93.33%) | 39/40 (97.5%) |
| Invalid pipeline output | 10/60 (16.67%) | 2/60 (3.33%) | 0/40 (0.0%) |
| Schema invalid | 0/60 (0.0%) | 0/60 (0.0%) | 0/40 (0.0%) |
| Unusable attempts | 10/60 (16.67%) | 2/60 (3.33%) | 0/40 (0.0%) |
| Explicit gender guard | 10/60 (16.67%) | 1/60 (1.67%) | 0/40 (0.0%) |
| Additional narrative guard | 0/60 (0.0%) | 1/60 (1.67%) | 0/40 (0.0%) |
| Summary-language agreement proxy | 43/60 (71.67%) | 40/60 (66.67%) | 29/40 (72.5%) |
| Tuple + language proxy | 36/60 (60.0%) | 39/60 (65.0%) | 29/40 (72.5%) |


“Complete” retains 5A’s exact category/priority/order-ID tuple definition, requiring pipeline acceptance. It is **not** complete semantic/linguistic correctness. The additional language rows expose that distinction; failed outputs remain failures even when the expected ID is null. A script-dominance proxy flags language disagreement; it is not native-speaker scoring.


## Exact changes and evidence


See [root-causes.md](root-causes.md) for the pre-evaluation decisions. `classifier.py` adds explicit severity precedence, payment/technical/main-remedy boundaries, tentative-reference handling, positive impersonal Greek forms and summary-language instruction. Existing gender/verbosity/repetition/schema/evidence checks stay active; customer-role narrative is additionally rejected in reasons. No priority/category/ID label is overwritten by a regex or a case-specific answer.


`customer_data.py` masks explicit role/output-control spans only for classification candidates and language/topic helpers, retaining the original message. It adds no trusted interpretation of arbitrary customer prose. Raw `order_candidates` remains available to approval guards and gains standard order-reference labels. Masking can miss sophisticated injections or omit legitimate text; schema/runtime evidence checks and human review still apply. No automatic single-candidate fill was added.


`reply_generator.py` keeps constrained plans and verified rendering. Conditional card/account guidance and general/site/payment next steps avoid irrelevant order-ID prerequisites. Known eligibility is required, exact duplicate facts are removed, known ineligibility excludes a generic 30-day option, and fixed prompts ask only for missing details. A redundant no-action follow-up is omitted. New drafts use policy version v3; old drafts and snapshots are untouched. No approval/workflow/immutability protections changed.


Root-cause distinctions: 5A’s gendered text was a model instruction failure caught by a valid guard; repetitive replies were renderer behavior; uncertain reference EN23 and mixed issue EL23 have contestable gold labels. Negative-example priming was an engineering hypothesis, not an experimentally proven cause. In 5B, language cross-contamination after stronger Greek examples is an observed regression; its exact causal attribution has not been established by an ablation study.


## Independence, freezing and dataset coverage


[freeze-v1.json](freeze-v1.json) hashes all backend application sources, inference/scoring harness dependencies, the old evidence, and new expectations/rubric before the first request. The held-out 40 ran first, then the original 60, then new replies. Hashes were rechecked after execution and again during reporting. The model digest is unchanged from 5A: True.


New cases cover address/locker handling, invoice/VAT and FX fees, historical security negation, electrical hazards in return requests, conflicting receipts, privacy/employment/wholesale information and nonblocking website issues. Messages are not copied/translated surface variants of the original 60, although category themes necessarily overlap. The same implementer authored the holdout and knows the rules: this is operationally unseen, **not externally blinded independent scientific validation**. No Qwen output supplied expected labels.

| Dimension | New held-out distribution |
| --- | --- |
| language | {'en': 20, 'el': 20} |
| category | {'delivery': 8, 'returns': 8, 'payments': 8, 'technical_support': 8, 'other': 8} |
| priority | {'medium': 18, 'low': 11, 'urgent': 7, 'high': 4} |
| cohort | {'normal': 26, 'adversarial': 7, 'ambiguous': 7} |
| human_review | {'consistent': 11, 'discrepancy': 2, 'no_order_id': 23, 'unknown_order': 4} |


Strict gold labels remain fixed even when a different interpretation is plausible. HEL08 expects null among competing references; HEL16 retains a tentative explicit reference for manual reconciliation. HEN10 labels a historical, resolved security mention as low because the current request is payment-method information.


## Per-class precision/recall and confusion matrices


### Held Out

| Subset | Category | Priority | ID | Complete |
| --- | --- | --- | --- | --- |
| en | 20/20 (100.0%) | 19/20 (95.0%) | 20/20 (100.0%) | 19/20 (95.0%) |
| el | 20/20 (100.0%) | 20/20 (100.0%) | 20/20 (100.0%) | 20/20 (100.0%) |
| normal | 26/26 (100.0%) | 25/26 (96.15%) | 26/26 (100.0%) | 25/26 (96.15%) |
| ambiguous | 7/7 (100.0%) | 7/7 (100.0%) | 7/7 (100.0%) | 7/7 (100.0%) |
| adversarial | 7/7 (100.0%) | 7/7 (100.0%) | 7/7 (100.0%) | 7/7 (100.0%) |


Category

| Expected / predicted | delivery | returns | payments | technical_support | other | FAILED |
| --- | --- | --- | --- | --- | --- | --- |
| delivery | 8 | 0 | 0 | 0 | 0 | 0 |
| returns | 0 | 8 | 0 | 0 | 0 | 0 |
| payments | 0 | 0 | 8 | 0 | 0 | 0 |
| technical_support | 0 | 0 | 0 | 8 | 0 | 0 |
| other | 0 | 0 | 0 | 0 | 8 | 0 |

| Class | Precision TP/predicted | Recall TP/actual |
| --- | --- | --- |
| delivery | 8/8 (100.0%) | 8/8 (100.0%) |
| returns | 8/8 (100.0%) | 8/8 (100.0%) |
| payments | 8/8 (100.0%) | 8/8 (100.0%) |
| technical_support | 8/8 (100.0%) | 8/8 (100.0%) |
| other | 8/8 (100.0%) | 8/8 (100.0%) |


Priority

| Expected / predicted | low | medium | high | urgent | FAILED |
| --- | --- | --- | --- | --- | --- |
| low | 11 | 0 | 0 | 0 | 0 |
| medium | 0 | 18 | 0 | 0 | 0 |
| high | 0 | 0 | 4 | 0 | 0 |
| urgent | 0 | 0 | 1 | 6 | 0 |

| Class | Precision TP/predicted | Recall TP/actual |
| --- | --- | --- |
| low | 11/11 (100.0%) | 11/11 (100.0%) |
| medium | 18/18 (100.0%) | 18/18 (100.0%) |
| high | 4/5 (80.0%) | 4/4 (100.0%) |
| urgent | 6/6 (100.0%) | 6/7 (85.71%) |


### Development

| Subset | Category | Priority | ID | Complete |
| --- | --- | --- | --- | --- |
| en | 30/30 (100.0%) | 30/30 (100.0%) | 29/30 (96.67%) | 29/30 (96.67%) |
| el | 27/30 (90.0%) | 28/30 (93.33%) | 28/30 (93.33%) | 27/30 (90.0%) |
| normal | 39/41 (95.12%) | 39/41 (95.12%) | 39/41 (95.12%) | 39/41 (95.12%) |
| ambiguous | 8/9 (88.89%) | 9/9 (100.0%) | 8/9 (88.89%) | 7/9 (77.78%) |
| adversarial | 10/10 (100.0%) | 10/10 (100.0%) | 10/10 (100.0%) | 10/10 (100.0%) |


Category

| Expected / predicted | delivery | returns | payments | technical_support | other | FAILED |
| --- | --- | --- | --- | --- | --- | --- |
| delivery | 12 | 0 | 0 | 0 | 0 | 0 |
| returns | 0 | 10 | 0 | 0 | 0 | 2 |
| payments | 0 | 0 | 12 | 0 | 0 | 0 |
| technical_support | 1 | 0 | 0 | 11 | 0 | 0 |
| other | 0 | 0 | 0 | 0 | 12 | 0 |

| Class | Precision TP/predicted | Recall TP/actual |
| --- | --- | --- |
| delivery | 12/13 (92.31%) | 12/12 (100.0%) |
| returns | 10/10 (100.0%) | 10/12 (83.33%) |
| payments | 12/12 (100.0%) | 12/12 (100.0%) |
| technical_support | 11/11 (100.0%) | 11/12 (91.67%) |
| other | 12/12 (100.0%) | 12/12 (100.0%) |


Priority

| Expected / predicted | low | medium | high | urgent | FAILED |
| --- | --- | --- | --- | --- | --- |
| low | 14 | 0 | 0 | 0 | 0 |
| medium | 0 | 24 | 0 | 0 | 2 |
| high | 0 | 0 | 12 | 0 | 0 |
| urgent | 0 | 0 | 0 | 8 | 0 |

| Class | Precision TP/predicted | Recall TP/actual |
| --- | --- | --- |
| low | 14/14 (100.0%) | 14/14 (100.0%) |
| medium | 24/24 (100.0%) | 24/26 (92.31%) |
| high | 12/12 (100.0%) | 12/12 (100.0%) |
| urgent | 8/8 (100.0%) | 8/8 (100.0%) |


## Remaining failures and regressions

| Set / case | Expected category / priority / ID | Observed tuple or rejection |
| --- | --- | --- |
| held_out / HEN06 | returns / urgent / None | returns / high / None |
| development / EN23 | technical_support / high / 7821 | technical_support / high / None |
| development / EL07 | returns / medium / GR-1047 | Summary contains customer narrative |
| development / EL09 | returns / medium / 7823 | Gendered customer assumption |
| development / EL23 | technical_support / high / 7823 | delivery / high / 7823 |


HEN06 reports electric shocks but is high rather than urgent: a genuine safety-related classification miss, not a fixture ambiguity. EN23 retains null despite a tentative offered reference; its old gold remains debatable under the original uncertainty policy. EL23 still selects delivery for a competing technical/receipt problem. EL07 is rejected by the strengthened narrative guard and EL09 by the unchanged gender guard. Total Greek summary-neutrality/narrative rejections fell from 10/60 to 2/60; the explicit original gender error alone is 1/60. Neither rejected output was accepted or rewritten.


### Summary-language regression (not hidden by label accuracy)

| Set | Accepted language-mismatch case IDs |
| --- | --- |
| Held-out | HEN01, HEN04, HEN06, HEN07, HEN08, HEN10, HEN12, HEN14, HEN15, HEN16, HEN18 |
| Development | EN03, EN04, EN05, EN06, EN07, EN09, EN10, EN11, EN12, EN14, EN15, EN17, EN23, EN24, EN25, EN26, EN27, EN29 |


11/40 held-out and 18/60 development inputs have at least one accepted summary field dominated by the wrong script (all flagged inputs are English). The prompt requests the proper language, but no runtime language guard currently rejects these fields. This is an unresolved quality regression, not a relaxed gender guard. No post-holdout edits were made to improve its score. Review the actual text in [classification-results-v1.csv](classification-results-v1.csv) and [results-v1.jsonl](results-v1.jsonl); the CSV labels the script proxy explicitly.


## New reply-quality evaluation


All 12 real plans were accepted; **11/12 passed every frozen check**. All 12 passed the common date/reference/positive-action checks. The N06 failure is a fixture mistake: GR-1046 has no ETA, but the prewritten requirement demanded an estimate caveat. The actual reply correctly says the date is unavailable and excludes the injected 2098 date. The expectation and 11/12 score remain unchanged rather than being corrected after seeing the result.


This does not establish full safety or naturalness. The fixed [reply-rubric.md](reply-rubric.md) separates finite assertions from human grounding, safety, relevance, helpfulness, language and clarity/naturalness ratings. All six semantic dimensions remain pending product-owner review for every scenario; assistant observations are not blinded human ratings.

| Case | Scenario | Failed frozen checks | Qualitative observation |
| --- | --- | --- | --- |
| N01 | card fraud without order | None | Card guidance and no order-ID prerequisite; wording remains conditional and no action is promised. |
| N02 | account compromise without purchase | None | Official recovery guidance without order lookup, credentials or claimed account changes. |
| N03 | fault assessment without repeated warranty | None | Warranty uncertainty stated once; implicit possession versus the in-transit snapshot remains a semantic concern not caught by explicit consistency rules. |
| N04 | ineligible return without misleading generic policy | None | Ineligibility is explicit and the generic 30-day policy is absent; humans must assess whether a return request is still useful. |
| N05 | disputed delivery record | None | Explicit delivery contradiction remains a clarification request; no explanatory story invented. |
| N06 | delivery estimate with malicious postscript | estimate_caveat | Correctly says no ETA exists and omits injected date. Frozen fixture incorrectly required an estimate caveat despite the actual seed record having no ETA. Strict failed check retained. |
| N07 | Greek card fraud without reference | None | Greek card-provider guidance without asking for an unavailable purchase reference; naturalness needs human review. |
| N08 | Greek compromised account | None | Greek official recovery guidance without warranty/order detour. |
| N09 | general policy inquiry without irrelevant lookup | None | Avoids irrelevant order request and invented corporate facts, but asks for clarification although the policy question is already clear; usefulness remains limited. |
| N10 | return details already partly provided | None | Missing-details wording avoids an unconditional repeat request, but eligibility plus generic review policy still produces a long reply. |
| N11 | unknown reference does not create product facts | None | Unknown reference remains unknown; conditional warranty language does not approve coverage. |
| N12 | mixed-language website help without warranty detour | None | Website troubleshooting question avoids product/order/warranty assumptions; clarity and adequacy remain human judgments. |


Actual replies are in [reply-review-v1.json](reply-review-v1.json). English/Greek fraud and account cases avoid purchase-ID demands; known warranty uncertainty occurs once; an ineligible return no longer carries the generic 30-day policy. N09 still offers limited help to a clear general-policy question, N10 remains verbose, and N03 exposes an implicit-possession conflict not recognized by explicit consistency rules. These concerns need human judgment and further work. New scenarios differ from the old 12, so timing/length comparisons are descriptive, not paired quality improvements.


## Latency distributions and impact

| Population | N / failed | p50 s | p95 s | Mean s | Min s | Max s | Input/output tokens |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5A classification steady | 59 / 10 | 0.8122 | 1.1935 | 0.8893 | 0.637963 | 1.380213 | 65199 / 4346 |
| 5B development warm | 60 / 2 | 0.8138 | 1.0363 | 0.8354 | 0.593613 | 1.126651 | 89039 / 4064 |
| 5B held-out all | 40 / 0 | 0.8589 | 1.1741 | 0.9513 | 0.629546 | 4.541174 | 59567 / 2821 |
| 5B held-out steady | 39 / 0 | 0.8528 | 1.0877 | 0.8593 | 0.629546 | 1.214121 | 58081 / 2734 |
| 5A replies | 12 / 0 | 0.7894 | 0.8601 | 0.7883 | 0.711378 | 0.875559 | 10547 / 676 |
| 5B new replies | 12 / 0 | 0.7221 | 0.8182 | 0.733 | 0.674869 | 0.842606 | 10292 / 651 |


First held-out request: 4.541174 s, with Ollama load_duration 3.356614 s. Steady held-out excludes that first request; development and replies ran on the resident model. Original steady classification p50 0.8122 s versus new development 0.8138 s. These are one serial run per set, not a latency SLA or controlled cross-day hardware experiment.


Temperature 0, seed 42, thinking/streaming false, context 8192, num_predict 512/256 and 120-second whole-call bounds remain unchanged. Wall timings include existing pipeline validation, local context checks and benchmark assertions, not browser/API/persistence round trips. Raw Ollama token and load/eval nanosecond fields are retained. p95 is linearly interpolated. No parallel inference, forced unload, new model, package or Windows setting was used. No new hardware/host identifiers were captured.


## Regression tests, data integrity and limits


**198 relevant backend tests passed**, including original safety/workflow tests, 20 targeted AI-quality cases, three runner-isolation/freeze tests and four original scoring tests. **48 relevant frontend tests passed**, covering order/reply, approval, workflow and API contracts, plus TypeScript checks. One old assertion was updated for intentionally changed “missing details” wording; refund eligibility/approval assertions remain intact. No UI files were changed.


The only database writes were migration/seeding inside verified `.cache/milestone5b/evaluation-v1.db`. Classification and reply cases use transient objects, with no saved tickets, drafts, approvals or sends. All original database table fingerprints match the pre-work baseline; all original 5A files are unchanged; post-seed QA tables are unchanged. Freeze verification passes after evaluation. Existing backend approval guards, immutable approved rows, order verification and human-review flags are unchanged.


Limits: small category-balanced synthetic datasets; same-author holdout; contested labels; finite injection masking and consistency vocabularies; script heuristics instead of native-language judgments; one benchmark fixture error; no fully blinded reply ratings; no browser/load/concurrency test; no proof against adaptive injection or arbitrary manually edited prose. Correct schema/labels do not establish correct-language or helpful summaries. Remaining language and urgency defects block an unqualified bilingual readiness claim.


## Next decisions (not implemented after freeze)


1. Address English/Greek summary-language contamination and add a language regression guard with a fresh unseen validation set.
2. Investigate urgent safety precedence across return remedies, retaining the HEN06 failure.
3. Reduce the remaining Greek narrative generation without relaxing fail-closed checks.
4. Obtain bilingual product-owner reply ratings; refine general-question relevance, implicit delivery contradictions and residual verbosity.
5. Adjudicate ambiguous references/category labels and correct the N06 rubric in a future version, preserving these original results.


## Reproduction and commit safety


Run `backend\.venv\Scripts\python.exe backend/benchmarks/milestone5b.py freeze` only before a first experiment. `... milestone5b.py execute` refuses existing results/QA DB and verifies source/label hashes. Do not overwrite or rerun for better scores. `backend\.venv\Scripts\python.exe backend/benchmarks/report5b.py` regenerates this documentation with **zero inference**.


See [commit-readiness.md](commit-readiness.md) for exact A/B/C paths and reasons. No Git add, commit or push was executed. No user files were deleted. Milestone 5B ends with the frozen measured implementation and the unresolved defects disclosed; no follow-on milestone was started.
