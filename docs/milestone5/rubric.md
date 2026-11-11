# Reply evaluation rubric v1

Frozen scenarios are in `replies-v1.json`; the existing application renderer and
prompts were not changed. All scenarios use real local Qwen plan inference.
All outputs remain unsaved/unapproved/unsent and pending product-owner review.

## Objective checks

Each scenario records a boolean for each applicable check. An unavailable output
is a failed scenario, not silently removed. “All automated checks passed” requires
an accepted pipeline result and every applicable boolean to be true.

| Check | Method and boundary |
| --- | --- |
| Pipeline/schema | Existing strict Pydantic models and reply-plan runtime validation. Shape validity is not semantic correctness. |
| Language | Returned language must match independently authored expected language. The source selects fixed localized sentences; it is not a native speaker's fluency rating. |
| Next step | Plan's fixed action must match the independently authored expected action in the scenario. Its usefulness still needs human judgment. |
| Human-review state | Current order-consistency state must match the authored expectation. Every draft independently requires approval. |
| Dates | ISO calendar dates in output must be a subset of verified order/snapshot/ETA dates. No dates are permitted for unknown or disputed records. This does not recognize every possible written date format. |
| Order references | Explicit extracted references must be within the scenario context. This uses the existing order-evidence parser and cannot prove every paraphrase safe. |
| Completed-action phrases | A specified English/Greek pattern list must find no affirmative refund/contact/shipment claims. Finite-pattern absence is not proof against all unsupported promises. |
| Required facts | Required renderer sentences must occur. This deliberately shares application material logic and is an architectural invariant, not an independent factual oracle. |
| Message preservation | Original scenario string must be unchanged. Neither original database content nor order snapshots are rewritten. |
| Discrepancies R06/R07 | Disputed record product name is omitted and explicit human clarification text is present. |
| Estimates R01/R02/R12 | Estimate-not-guarantee wording is present. |
| Missing ETA R03 | Explicit unknown-ETA wording is present. |
| Unauthorized charges R09 | Card-provider advice is present; sensitive-card-data warning is visible in the actual output. |

Existing approval-guard signals are recorded separately, not represented as an
independent second safety oracle. `reply_checks` performs finite, transparent
checks; it never asks an LLM to score its own answer.

## Subjective/semantic review — intentionally pending

The product owner should rate **each of the 12 actual outputs** before claiming
overall reply quality. No numeric semantic score has been invented.

1. Does the response address the customer's actual main need, including urgency?
2. Is the language natural, respectful, gender-neutral and concise?
3. Are details, conditional eligibility and snapshot limitations understandable?
4. Are requested details necessary, not already provided or inappropriate?
5. Is the advice useful despite no real actions having been performed?
6. Are there unsupported implications, guarantees or invented explanations missed
   by finite checks? Does mixed-language/product-name handling remain understandable?

Suggested human ratings: **acceptable**, **needs revision**, **unsafe**, or
**uncertain**, with a reason. These are future human ratings, not labels already
assigned by the benchmark. Assistant qualitative observations are explicitly
marked and must not be confused with product-owner approval.
