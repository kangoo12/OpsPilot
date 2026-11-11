# Milestone 5B: evidence and implementation decisions

Reviewed the complete 5A report/rubric, 60 individual classification records (including
raw schema-valid labels on failures), and all 12 actual reply outputs. The 5A files
and expected answers remain unchanged; pre-work hashes are retained privately.

| Evidence | Cause assessment | Focused change |
| --- | --- | --- |
| Ten Greek `Gendered customer assumption` rejections | Model instruction failure; a working guard causes availability loss rather than accepting unsafe summaries. Negative examples repeatedly prime the same wording. | Positive impersonal Greek examples/schema descriptions and explicit summary language. Preserve old guards, add customer-narrative rejection in reasons. No output rewriting or validation retry. |
| EN22 battery danger becomes high; EN13 duplicate billing becomes urgent | Severity calibration mistakes despite correct schema. | Explicit urgent-first severity precedence, physical hazard/account compromise rules and distinction between duplicate billing and evidence of unauthorized use. No regex label overrides. |
| EN15 payment information medium, EL11 unusable return medium | Information vs incident and remedy vs severity conflation. | Nonblocking information stays low; a return retains underlying unusability/safety severity. |
| EN16 checkout failure technical instead of payments | Category boundary partly ambiguous; target is payment completion rather than general software. | Clarify payment-completion vs unrelated outages; keep old gold labels fixed and document alternative readings. |
| EL23 conflicting receipt/technical problem becomes delivery | Main issue mixed with evidence conflicts; original benchmark label is contestable. | Ask model to classify requested help, leaving reconciliation to existing human review. No hardcoded case override. |
| EN23 null reference with a questionable purchase match | Null is defensible under old uncertainty wording, not necessarily a fabricated/missed ID. | Preserve a tentative explicitly offered reference for verification; still permit null for incompatible multiple IDs without a principal reference. No auto-fill from the database/candidate list. |
| Explicit override-only IDs can enter candidate schema | Raw evidence parser finds tokens, not intent. Prior tests cover basic injection, not an exhaustive threat model. | Mask explicit role/output-control spans when collecting classification candidates. Keep raw parser for approval checks; retain runtime membership validation. Expand common order-reference labels. Masking is conservative and fallible, not a trust boundary. |
| R08 duplicate warranty sentences | Renderer independently offers eligibility and generic policy. | Known eligibility is required exactly once; generic warranty policy offered only without a verified order. Remove duplicate sentences and redundant `none` follow-up. |
| R11 general 30-day policy follows ineligibility | Allowed facts are individually true but their juxtaposition may confuse. | Require recorded eligibility; do not offer generic 30-day policy for known ineligible/not-started/unknown eligibility. |
| R09 fraud victim asked for order ID | Order-centric default next step is inappropriate for unrelated security incidents. | Conditional card/account safety guidance and non-order next steps, retaining discrepancy warnings and review flags. Ordinary payment and general/site questions also avoid irrelevant product lookup. |
| R10 repeats already supplied condition | Fixed next-step prose lacks acknowledgment. | Ask only for missing details; no claim that anything has already been assessed or acted upon. |

No approval API, immutability trigger, order snapshot, review requirement or ticket
workflow is relaxed. Existing drafts remain historical text with their original
policy version. New reply material uses policy version `aster-demo-2026-11-v3`.
The model still selects a validated plan; arbitrary free-text facts are not allowed.

The new held-out messages introduce address/locker handling, invoice/VAT and FX
fees, historical-security negation, wholesale/employment/privacy questions,
nonblocking website indicators and conflicting receipts. They are newly authored,
not translations or surface rewordings of the 5A messages. Themes overlap by design
because the five categories are unchanged. The same implementer knows the rules
and authored the set: this is an unseen operational holdout, not an externally
blinded scientific validation. Expected labels and implementation will be hashed
before real inference; no tuning follows the held-out results in this milestone.
