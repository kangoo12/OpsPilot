# Historical AI quality and verification

All measurements below are preserved November 11, 2026 synthetic experiments. This document presents existing evidence; Milestone 6 ran no new inference benchmarks and changed no prompts, validators, expected labels or historical results. Classification calls exercise the application pipeline; reply probes generally use independently fixed ticket labels, not a successful classification prerequisite.

## What each metric means

- **Category / priority / ID accuracy:** exact expected field match across every intended case; rejected attempts remain failures even for a null expected ID.
- **Complete label tuple:** category, priority and ID all exact **and** pipeline acceptance. It does not establish concise/natural/gender-neutral/language-correct summaries or reply quality.
- **Schema validity:** raw structured output parses with the required types/enums. Application guards may reject structurally valid output.
- **Language:** script/name heuristics are proxies, not native-speaker judgments; later raw-language checks include outputs rejected for other reasons.
- **Reply finite checks:** constrained-plan acceptance and stated fact/assertion checks. These do not establish semantic usefulness, comprehensive safety or human approval.
- **Performance:** serial pipeline wall times from the measured machine, not browser-to-storage service guarantees or comparable hardware-controlled experiments.

## 5A baseline and 5B development/held-out comparison

| Metric | 5A original 60 | 5B same 60 — development | 5B new 40 — held-out |
| --- | --- | --- | --- |
| Language composition | 30 EN / 30 EL | Same original messages | 20 EN / 20 EL |
| Category | 48/60 (80%) | 57/60 (95%) | 40/40 (100%) |
| Priority | 45/60 (75%) | 58/60 (96.67%) | 39/40 (97.5%) |
| Order ID | 49/60 (81.67%) | 57/60 (95%) | 40/40 (100%) |
| Complete label tuple | 43/60 (71.67%) | 56/60 (93.33%) | 39/40 (97.5%) |
| Schema failures | 0/60 | 0/60 | 0/40 |
| Pipeline rejected | 10/60 | 2/60 | 0/40 |
| Explicit gender guard failures | 10/60 | 1/60 | 0/40 |
| Customer-narrative guard failures | 0/60 | 1/60 | 0/40 |
| Historical language-agreement proxy | 43/60 | 40/60 | 29/40 |
| Tuple plus language proxy | 36/60 | 39/60 | 29/40 |

The original 60 had 12/category, 41 normal, 9 ambiguous and 10 adversarial cases. The held-out 40 had 8/category, 26 normal, 7 ambiguous and 7 adversarial. Implementation/labels were frozen before the 5B serial run, held-out cases ran first, each case once without retries. The 60 were development examples after analysis, so their improvement is not generalization evidence.

The 40 new messages were operationally held out from tuning, but authored by the same implementer with knowledge of product rules. They are not externally blinded, representative of production traffic, or proven absent from model pretraining. Accuracy on balanced synthetic cases does not estimate real support performance. Ambiguous labels remain frozen rather than retroactively corrected to match the model. Precision/recall, failed confusion columns, individual outputs and per-language/cohort results are available in the original reports/metrics.

5B exposed **11/20 English held-out summary language mismatches** and a return involving electric shock classified high rather than urgent. Those facts qualify the 39/40 tuple headline. No autonomous action was performed.

Sources: [5A report](../milestone5/report.md), [5A metrics](../milestone5/metrics-v1.json), [5B report](../milestone5b/report.md), [5B metrics](../milestone5b/metrics-v1.json), [5B frozen results](../milestone5b/results-v1.jsonl).

## 5C — language and physical-safety corrections

Language-specific prompt/schema constraints and runtime checks were added; selected affirmative physical hazards require urgent. Existing gender/narrative/evidence guards stayed intact. Mixed language uses a documented Greek/Latin script rule, preserving permitted names and IDs.

| Population / version | Category | Priority | ID | Complete tuple | Pipeline rejected | Raw language checks |
| --- | --- | --- | --- | --- | --- | --- |
| Initial new 24 (12 EN / 12 EL) | 21/24 | 20/24 | 21/24 | 20/24 (83.33%) | 3/24 | 24/24 |
| Initial known 11 diagnostics | 9/11 | 9/11 | 9/11 | 9/11 | 2/11 | 11/11 |
| Final new 8 (4 EN / 4 EL) | 7/8 | 7/8 | 7/8 | 7/8 (87.5%) | 1/8 | 8/8 |
| Final repeated known 11 diagnostics | 9/11 | 9/11 | 9/11 | 9/11 | 2/11 | 11/11 |

All **54 raw classification outputs** across both revisions passed language checks, including rejected ones. This is not 54 unique independent successes: the 11 known diagnostics were repeated after a source correction. Final HEN06 became returns/urgent/null; HEN07/HEN08 still failed customer-narrative validation. No summary was repaired/substituted to hide a rejection.

An initial exception-list boundary issue and a physical-warning false positive prompted a transparent source revision. The final unseen eight cases were separately frozen before inference. **Do not compare 20/24 and 7/8 as a paired improvement, pool implementations, or report 11/11 language diagnostics as 11 accepted classifications.** Four initial and four final reply probes passed their finite checks; semantic review was still pending. Total 5C calls: 62 = 54 classification + 8 reply, including repeats.

Original 5C CEL12 raw priority is **low**, expected medium. Its report table says low while adjacent prose incorrectly says urgent. 5D documents this reporting defect separately; the historical file is unchanged. 5D's later medium diagnostic result does not prove a fix or injection resistance.

Sources: [5C report](../milestone5c/report.md), [metrics](../milestone5c/metrics-v1.json), [initial results](../milestone5c/results-v1.jsonl), [final follow-up results](../milestone5c/followup-v2/results-v1.jsonl).

## Reply quality and the ETA assertion defect

5A: **12/12** plans accepted and passed limited automated checks; semantic ratings remained pending. 5B: **12/12 accepted**, **11/12** passed the original frozen assertions. N06 used a verified order with no ETA; the reply correctly preserved uncertainty, but the old assertion required an estimate caveat. The separate [5C ETA correction](../milestone5c/eta-correction-v2.json) re-evaluates that same preserved output with a fact-aware versioned check. It does not change the 5B score, generate a new ETA, or count as new inference.

Template-grounded output reduces factual invention but can still be irrelevant, generic or repetitive. Pending semantic ratings are not completed human safety certification. No benchmark draft was approved/sent automatically.

## 5D final audit

- Nine new probes: **8/9 accepted exact tuples**; D09 return request rejected for narrative. Three known diagnostics: HEN07/HEN08 rejected again; CEL12 accepted medium. All **12 raw outputs** passed language checks; no explicit gender-guard failure observed.
- Nine reply fixtures generated with correct selected language, expected consistency state and no existing blocker signals. These use frozen labels even for the rejected classification. The D05 physical-danger reply **failed qualitative safety usefulness** despite urgent classification; “9/9 generated” must not become “9/9 safe/helpful.”
- Main browser workflow covered real EN/EL submissions, lookup, filters/sorting/pagination, drafting, editing/approval, immutable parent/pending child, rejection/regeneration, status/history, analytics and desktop/mobile. The first locator failure and final favicon console failure remain recorded. A subsequent read-only favicon/API-recovery check passed; this is not described as one uninterrupted green smoke run.
- **297 backend tests, 78 frontend tests, TypeScript and production build passed**, with a later **34-test focused** approval/workflow run. Repeated tests are not added as unique coverage. A real unrelated-order-ID approval gap was fixed in every order context, with three before-fix API failures becoming passing rejection tests.
- Two isolated backend process starts preserved 26 QA tickets, all three target drafts/decisions, exact approved content, revisions/activity and analytics; all 10 original database table fingerprints and 40 pre-5D historical evidence files matched. These are audit-specific scopes, not a promise all files in every future milestone are covered by that old lock.

Sources: [5D final report](../milestone5d/final-quality-report.md), [raw probes](../milestone5d/ai-results-v1.jsonl), [browser provenance](../milestone5d/browser-verification-v1.json), [restart verification](../milestone5d/restart-verification-v1.json). Agent qualitative review is distinct from blinded bilingual product-owner evaluation.

## Latency observations

| Historical population | N | Median classification / reply seconds | Qualification |
| --- | ---: | --- | --- |
| 5A steady classification | 59 | 0.8122 / — | Excludes first call; failed attempts retained |
| 5A replies | 12 | — / 0.7894 | Separate fixtures |
| 5B development | 60 | 0.8138 / — | Resident model |
| 5B held-out, all / steady | 40 / 39 | 0.8589 / 0.8528 classification | First call 4.541 s includes load |
| 5B replies | 12 | — / 0.7221 | New scenarios, not paired with 5A replies |
| 5D new probes | 9 each | 0.999314 / 0.751556 | Classification 0.739317–4.599119 s; replies 0.721832–0.809780 s |

These are measured local wall times, including validation, not service-level commitments or cost figures. Hardware, residency, prompts and populations differ. 5C per-population distributions remain in its report. All use local `qwen3.5:9b`; no second model, cloud fallback or repeated-for-score inference was introduced.

## What can be claimed

The prototype has measured synthetic evidence, visible errors, controlled drafting and tested human workflow. It is **CONDITIONAL GO only for supervised fictional demos**. HIGH physical-safety reply usefulness, MEDIUM narrative availability and MEDIUM semantic robustness remain. A production claim needs new adjudicated multilingual datasets, operational monitoring, human evaluation, security/identity/integration gates and repeatable release evaluation. [Proposed gates — future work](production-roadmap.md).
