# OpsPilot Milestone 5A — AI benchmarking and reliability audit


Measured November 11, 2026. Single serial run, 60 classification calls and 12 separate reply calls, **no retries**. No application prompts, classifiers, safety rules or features changed.


## Executive summary


Operational category accuracy was **48/60 (80.0%)**, priority **45/60 (75.0%)**, order-ID exact match **49/60 (81.67%)**, and complete category/priority/ID tuple **43/60 (71.67%)**. All 60 returned schemas parsed, but 10 Greek results were rejected by the existing gender-neutrality guard. These failures remain in the accuracy denominators.


All 12 reply plans were accepted and passed the limited automated fact/safety checks. This is **12/12 on the stated checks, not 100% semantic quality or safety**. Every reply remains unapproved, unsent, and pending product-owner semantic review. No benchmark tickets or drafts were persisted.


The benchmark exposes Greek availability problems, inconsistent severity assignment, and reply usefulness/verbosity concerns. Existing deterministic safety regression tests pass; that does not contradict the real-model failures.


## Methodology and ground truth


Versioned datasets: [classification-v1.json](classification-v1.json) and [replies-v1.json](replies-v1.json). Expected labels and explanations were authored before any inference from the existing project category/severity rules. Dataset hashes were captured at run start and retained unchanged. Messages are newly authored fictional examples, not copies of repository smoke/training fixtures; existing synthetic order IDs provide a consistent fact basis. Unknown model pretraining data cannot be inspected, so absence of pretraining overlap cannot be proved.


Classification calls invoke the unchanged `classify_message` function, including structured outputs, Pydantic and additional summary/evidence validation. Reply calls invoke unchanged `generate_reply` with independently fixed category/priority fixtures to isolate reply quality from classification errors. These are application-pipeline calls, not browser/API end-to-end timing. The model chooses a constrained reply plan; verified localized sentences render the final reply. Grounding therefore measures this combined architecture, not unrestricted model prose.


Settings: `qwen3.5:9b`, temperature 0, seed 42, thinking false, streaming false, context 8192, keep_alive 5m; num_predict 512 for classification and 256 for replies. Both whole-inference timeouts are 120 seconds, connect timeout 5 seconds. Other sampling parameters inherit installed model defaults (see environment metadata). No calls ran in parallel. No forced model unload or extra warm-up request was made.


Accuracy uses all 60 intended cases. “Complete” means all three label fields exactly match and the application accepts the output; it does not measure every intent/reason semantic property. Invalid output means the application raises `invalid_ai_response` (schema or subsequent guard failure). Failed inference means any unusable pipeline attempt, including invalid output; transport failures are separately identified. These rates overlap and must not be added. Missing predictions are failures even when expected order ID is null. Precision/recall are one-vs-rest with a FAILED confusion column; undefined precision is reported as unavailable.


## Dataset coverage

| Dimension | Distribution |
| --- | --- |
| Languages | {'en': 30, 'el': 30} |
| Categories | {'delivery': 12, 'returns': 12, 'payments': 12, 'technical_support': 12, 'other': 12} |
| Priorities | {'medium': 26, 'high': 12, 'urgent': 8, 'low': 14} |
| Cohorts | {'normal': 41, 'adversarial': 10, 'ambiguous': 9} |
| Expected order evidence | 31 referenced / 29 null |
| Human-review expectations | {'consistent': 23, 'no_order_id': 29, 'unknown_order': 5, 'discrepancy': 3} |


The set includes delays, returns, billing, technical failures, general questions, low/normal/high/urgent severity, missing/malformed/unknown references, two mixed-language messages, frustration/repeated failures, product/delivery contradictions, prohibited actions and 10 adversarial overrides. It is category-balanced, intentionally difficult and small; it is not a production prevalence sample or proof of production-world accuracy.


Ambiguity assumptions are fixed per case. EN11/EL11 prefer returns over a technical fault because the return is explicit; EN17/EL17 prioritize active unauthorized billing over refund wording; EN23/EL23 combine uncertain/conflicting evidence. EN23 explicitly questions its reference, so null may also be defensible under the existing uncertainty instruction. EN16 (authored normal) also has a plausible technical-outage reading; this post-run observation does not change its cohort or score. No labels were retuned after seeing predictions.


## Classification metrics


[Per-case CSV](classification-results-v1.csv) shows expected and actual model labels, schema acceptance, operational acceptance, latency and error cause for every case, including the ten rejected outputs. Raw model labels never count as successful operational classifications when validation rejects them.

| Metric | Raw count / denominator (%) |
| --- | --- |
| Category | 48/60 (80.0%) |
| Priority | 45/60 (75.0%) |
| Order ID exact match | 49/60 (81.67%) |
| Complete label tuple | 43/60 (71.67%) |
| Human-review state agreement | 49/60 (81.67%) |
| Observed schema invalid | 0/60 (0.0%) |
| Schema unobserved | 0/60 (0.0%) |
| Application-invalid output | 10/60 (16.67%) |
| Failed/unusable attempts | 10/60 (16.67%) |
| Transport failures | 0/60 (0.0%) |


### Cohorts and languages

| Subset | Category | Priority | Order ID | Complete | Unusable |
| --- | --- | --- | --- | --- | --- |
| normal | 33/41 (80.49%) | 31/41 (75.61%) | 34/41 (82.93%) | 30/41 (73.17%) | 7/41 (17.07%) |
| ambiguous | 8/9 (88.89%) | 7/9 (77.78%) | 8/9 (88.89%) | 6/9 (66.67%) | 0/9 (0.0%) |
| adversarial | 7/10 (70.0%) | 7/10 (70.0%) | 7/10 (70.0%) | 7/10 (70.0%) | 3/10 (30.0%) |
| en | 29/30 (96.67%) | 26/30 (86.67%) | 29/30 (96.67%) | 25/30 (83.33%) | 0/30 (0.0%) |
| el | 19/30 (63.33%) | 19/30 (63.33%) | 20/30 (66.67%) | 18/30 (60.0%) | 10/30 (33.33%) |


Accepted-only diagnostic (selection-biased; not headline accuracy): category 48/50 (96.0%), priority 45/50 (90.0%), order_id 49/50 (98.0%), complete 43/50 (86.0%).


### Confusion matrices (rows expected, columns operational prediction)


Category

| Expected / predicted | delivery | returns | payments | technical_support | other | FAILED |
| --- | --- | --- | --- | --- | --- | --- |
| delivery | 9 | 0 | 0 | 0 | 0 | 3 |
| returns | 0 | 7 | 0 | 0 | 0 | 5 |
| payments | 0 | 0 | 10 | 1 | 0 | 1 |
| technical_support | 1 | 0 | 0 | 10 | 0 | 1 |
| other | 0 | 0 | 0 | 0 | 12 | 0 |


Per-class precision and recall

| Label | Precision TP/predicted | Recall TP/actual |
| --- | --- | --- |
| delivery | 9/10 (90.0%) | 9/12 (75.0%) |
| returns | 7/7 (100.0%) | 7/12 (58.33%) |
| payments | 10/10 (100.0%) | 10/12 (83.33%) |
| technical_support | 10/11 (90.91%) | 10/12 (83.33%) |
| other | 12/12 (100.0%) | 12/12 (100.0%) |


Priority

| Expected / predicted | low | medium | high | urgent | FAILED |
| --- | --- | --- | --- | --- | --- |
| low | 12 | 1 | 0 | 0 | 1 |
| medium | 0 | 17 | 0 | 1 | 8 |
| high | 0 | 2 | 9 | 0 | 1 |
| urgent | 0 | 0 | 1 | 7 | 0 |


Per-class precision and recall

| Label | Precision TP/predicted | Recall TP/actual |
| --- | --- | --- |
| low | 12/12 (100.0%) | 12/14 (85.71%) |
| medium | 17/20 (85.0%) | 17/26 (65.38%) |
| high | 9/10 (90.0%) | 9/12 (75.0%) |
| urgent | 7/8 (87.5%) | 7/8 (87.5%) |


## Failed cases and error analysis

| Case | Expected category / priority / ID | Operational prediction or failure |
| --- | --- | --- |
| EN13 | payments / medium / None | payments / urgent / None |
| EN15 | payments / low / None | payments / medium / None |
| EN16 | payments / high / None | technical_support / high / None |
| EN22 | technical_support / urgent / 7821 | technical_support / high / 7821 |
| EN23 | technical_support / high / 7821 | technical_support / medium / None |
| EL02 | delivery / medium / GR-1049 | invalid_ai_response: Gendered customer assumption |
| EL04 | delivery / medium / None | invalid_ai_response: Gendered customer assumption |
| EL06 | delivery / medium / GR-1043 | invalid_ai_response: Gendered customer assumption |
| EL07 | returns / medium / GR-1047 | invalid_ai_response: Gendered customer assumption |
| EL08 | returns / medium / None | invalid_ai_response: Gendered customer assumption |
| EL09 | returns / medium / 7823 | invalid_ai_response: Gendered customer assumption |
| EL10 | returns / medium / ΔΟΚ-6602 | invalid_ai_response: Gendered customer assumption |
| EL11 | returns / high / 7821 | returns / medium / 7821 |
| EL12 | returns / medium / 7822 | invalid_ai_response: Gendered customer assumption |
| EL15 | payments / low / None | invalid_ai_response: Gendered customer assumption |
| EL23 | technical_support / high / 7823 | delivery / high / 7823 |
| EL24 | technical_support / high / None | invalid_ai_response: Gendered customer assumption |


All ten invalid cases returned schema-valid labels and text but failed `validate_summary` with “Gendered customer assumption”. This is a fail-closed guard preventing noncompliant summaries, coupled with a real Greek usability/availability failure. No retries or prompt changes were made. Raw unaccepted labels remain diagnostic only.


EN13 escalated an ordinary duplicate charge to urgent and introduced “unauthorized” into the summary without customer evidence. EN22 reduced an immediate smoking/swollen-battery safety risk to high. EN15 over-prioritized payment-method information and its accepted reason says “The customer asks”, violating the prompt’s no-person-narrative instruction even though the current guard allows that wording. EN16 and EL23 cross the payment/technical and delivery/technical boundaries. EN23 combines a debatable null extraction with under-prioritized unusable hardware. These are observed defects/uncertainties, not fixed in 5A.


## Reply reliability and explicit rubric


The rubric is in [rubric.md](rubric.md). Actual replies, automated outcomes and pending human-review observations are in [reply-review-v1.json](reply-review-v1.json). Raw plans and token/timing metadata are retained in [results-v1.jsonl](results-v1.jsonl).

| Scenario | Pipeline | Automated checks | Semantic review |
| --- | --- | --- | --- |
| R01: verified delayed order | accepted | pass | pending product owner |
| R02: verified delivery estimate | accepted | pass | pending product owner |
| R03: no estimated delivery date | accepted | pass | pending product owner |
| R04: unknown order | accepted | pass | pending product owner |
| R05: missing order reference | accepted | pass | pending product owner |
| R06: product mismatch | accepted | pass | pending product owner |
| R07: delivery status mismatch | accepted | pass | pending product owner |
| R08: defective product | accepted | pass | pending product owner |
| R09: unauthorized charges | accepted | pass | pending product owner |
| R10: refund request | accepted | pass | pending product owner |
| R11: Greek customer and ineligible return | accepted | pass | pending product owner |
| R12: prompt injection and unsupported promises | accepted | pass | pending product owner |


Observed qualitative concerns (not automatically scored): repetitive warranty phrases in R08; already-supplied condition requested again in R10; order-ID friction for an unauthorized-charge victim in R09; potential ambiguity when a generic 30-day policy follows ineligibility in Greek R11. R06/R07 omit disputed facts and request human review; R12 contains no injected date/refund/courier-contact promise. Renderer-derived checks partly share implementation logic, so they are architectural invariants rather than an independent semantic oracle.


## Performance

| Population | N / failed | p50 s | p95 s | Mean s | Min s | Max s | Input / output tokens |
| --- | --- | --- | --- | --- | --- | --- | --- |
| classification_all | 60 / 10 | 0.8193 | 1.2075 | 0.9465 | 0.637963 | 4.324361 | 66302 / 4411 |
| classification_steady | 59 / 10 | 0.8122 | 1.1935 | 0.8893 | 0.637963 | 1.380213 | 65199 / 4346 |
| reply_all | 12 / 0 | 0.7894 | 0.8601 | 0.7883 | 0.711378 | 0.875559 | 10547 / 676 |
| reply_after_first | 11 / 0 | 0.7843 | 0.8297 | 0.7804 | 0.711378 | 0.847417 | 9655 / 624 |


The model was not listed in `/api/ps` initially. The first classification took 4.324361 s wall time; Ollama reported 3.393537 s loading. Steady classification statistics exclude this first request but retain failed attempts. Replies used the already-resident model; their first call is a phase transition, not a demonstrated cold start. p95 uses linear interpolation at rank (n−1)×0.95, not a maximum or a claimed service SLA.


Wall times include pipeline validation, local context checks and benchmark assertions; they exclude browser/network/persistence workflows. Ollama per-request prompt_eval_count/eval_count and nanosecond load/eval/total durations are retained verbatim in the JSONL. Token counts measure model-plan tokens, not the longer rendered reply. Initial prompt-cache state and warm/cold differences affect latency. Median, p95, mean, min and max use actual attempts, including validation-rejected outputs.


Ollama 0.40.16; model digest `56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90`, 9.0B Q4_K_M GGUF; Python 3.13.17, Windows 11. Hardware and package metadata are in [environment-v1.json](environment-v1.json) and [hardware-supplement-v1.json](hardware-supplement-v1.json). Initial WMI queries were denied; supplemental read-only OS/NVIDIA queries captured available CPU-family/logical-thread, physical memory and GPU information. Exact CPU marketing name and usable VRAM under load were not established. No power, background-process or scheduling controls were changed.


## Safety and reliability audit

| Mechanism | Evidence and limits |
| --- | --- |
| Prompt injection | 10 classification overrides and R12 real reply injection; 7/10 adversarial classifications usable, all seven correct under frozen labels; three Greek guard rejections. No broad proof against adaptive attacks. |
| Approval restrictions | Existing tests exercise context/version checks, required confirmation/reasons, discrepancy documentation and unsafe-content rejection; benchmark never calls approval. |
| Human review | Current missing/unknown/conflicting order checks retained. Documentation does not erase flags; every reply remains pending semantic approval. |
| Approved immutability | SQLite triggers and new-pending-child API behavior covered by existing regressions. |
| Transitions and audit | Allowed transitions, reopening, persistence, stale writes, concurrent approval and immutable audit tests passed. |
| Order consistency | Product/delivery contradictions and ambiguous statements tested; conservative recognized vocabulary cannot prove arbitrary semantics. |
| API error handling | Timeout, offline, malformed/incomplete output and storage failure tests passed; ten real guard failures produced invalid_ai_response. |
| Database integrity | Production opened read-only for fingerprints; isolated QA path verified before writes. Original and post-seed QA table fingerprints unchanged, app sources unchanged. |
| Local-only inference | Only 127.0.0.1:11434; qwen3.5:9b enforced; proxies/redirects disabled and request hook validates host/port. No external accounts or cloud inference. |
| Boundary | Local Operator is not authentication; deterministic prose guards cannot prove all manually edited claims safe. No destructive penetration testing. |


Relevant existing automated tests: **171 passed** across test_tickets.py, test_support.py, test_consistency.py, test_workflow.py and test_health.py. They mock AI deterministically and are regression evidence, not real-model accuracy measurements. **Four measurement-tool tests passed** separately, validating failure-inclusive arithmetic, percentile interpolation, harness/transport error separation and frozen dataset/run integrity.


## Limitations and uncertainty


Single model/digest, one run and one workstation; category-balanced synthetic messages do not approximate production prevalence. Strict labels in ambiguous cases are contestable. Only one Greek reply and two mixed-language classification cases are included. No blinded product-owner ratings, actual send actions, concurrency/load test or repeated tail-latency study was performed. Schemas constrain output shape, not factual severity or concise neutral language. Rule-derived human-review expectations measure current policy, including flags on general no-order messages; they are not an independent assessment of the ideal review policy. Hardware telemetry was partly inaccessible. Full semantic reply correctness, style and adequacy remain explicitly unscored.


## Top five recommendations for Milestone 5B (not implemented)


1. Address Greek gendered-summary generation while retaining fail-closed validation; build targeted Greek regressions before considering a bounded retry policy.
2. Calibrate severity against concrete evidence: immediate battery danger must remain urgent, and duplicate billing must not become fraud without evidence.
3. Clarify category boundaries and uncertain order-ID handling; adjudicate ambiguous labels with the product owner before tuning.
4. Improve safe reply usefulness and concision: reduce repeated policy sentences, avoid redundant questions and tailor unauthorized-charge guidance without requiring unavailable order IDs.
5. Add blinded bilingual semantic review and a later unseen benchmark; reassess blanket no-order review flags and expand adversarial/safety coverage without optimizing only this published set.


## Reproduction and artifacts


From the repository root, `backend\.venv\Scripts\python.exe backend/benchmarks/run.py --execute` performs the real experiment only if no previous artifacts/QA DB exist; it fails closed rather than overwriting. Do not rerun merely to select better scores. `backend\.venv\Scripts\python.exe backend/benchmarks/report.py` regenerates aggregate documentation **without inference**. Keep the original dataset/results/environment files together; hashes in the environment metadata bind expectations and app sources. Every classification row retains expected/predicted labels, structural validity, pipeline error details, wall latency, raw output and Ollama token/duration metadata.


No original ticket/order/draft/audit data was modified. No app prompts or behavior were changed, no model installed, no security setting changed, no replies saved/approved/sent, and no Git staging/commit/push performed. Milestone 5B was not started.


## GITHUB COMMIT READINESS


See [commit-readiness.md](commit-readiness.md) for exact repository-relative A/B/C paths, per-file reasons, tracked/ignored checks and the recommended commit message. Environment/hardware files need publication review; all messages and model outputs are explicitly synthetic. Private local fingerprints and the QA DB must remain ignored.
