# Focused reliability review — order 7821

Reviewed on November 10, 2026, entirely within `F:\Projects\OpsPilot`.

## What was wrong

Two different tickets had been given the same fictional order ID for unrelated
scenarios. The original ticket reports a defective smartphone received that day;
the new seed incorrectly defined `7821` as a lamp in transit. The original seed
was created without checking the existing ticket's product/delivery claims.

The reported draft did **not** belong to the original smartphone ticket:

| Record | Database | Ticket ID | Evidence |
| --- | --- | --- | --- |
| Original smartphone ticket | `data/opspilot.db` | `07735cb2-a2fc-4d09-ac59-af14e2e499a0` | Greek message reports receipt of a defective phone; no saved drafts |
| Latest lamp smoke-test ticket | `data/milestone3a-smoke.db` | `f36e6876-767c-4bcc-a702-ffefaa8069af` | Synthetic English shipping query/injection message, not the phone message |
| Reported lamp draft | `data/milestone3a-smoke.db` | Parent ticket above | Draft `dd75910d-8d0d-4b3c-8c55-055730c05577` used the lamp record |

The [original smoke output](milestone3a-smoke.json) is preserved unchanged. Its
response was grounded in the smoke ticket's matched database row, but that did
not make the reused fixture ID consistent with the earlier phone scenario.
The application also lacked a customer-report versus order-record comparison:
without this fix, the original phone ticket could have received a contradictory
lamp reply. No such reply was found in its saved history.

## Fixes

- Fresh seeds reserve `7821` for a delivered Aster Nova smartphone. Lamp shipping
  scenarios and their source/test fixtures use unique ID `DEMO-LAMP-9001`.
- Explicit English/Greek product and delivery statements are compared with the
  matched record. Material mismatches and competing statements derive a visible
  human-review flag in ticket lists, details and the order panel. Unknown orders
  are separately marked as needing verification.
- A conflict forces a clarification-only reply plan. It excludes product, status,
  date and eligibility assertions, does not select a supposedly correct source,
  and does not invent an explanation or claim an escalation.
- Old draft snapshots are checked on read. Conflicting historical text is retained
  unchanged, collapsed under a warning, even if a later correction resolves the
  current order context. New safe clarification drafts remain visible.
- Explicit manual corrections refresh the derived flags without changing the
  original extracted ID, message, category or ticket status. There is no approval
  action, sending mechanism or status workflow.
- Order-ID tokens are excluded from product claims. Delivery questions, negated
  product statements and common incidental phone references have regressions to
  avoid treating them as affirmative claims. Greek `πότε` is not mistaken for a
  negative receipt assertion when accents are normalized.
- `.cache/debug_classification.py` was a one-off capture helper, not application
  code. It was removed. Cache/browser artifacts remain ignored; useful diagnostics
  now include `backend/scripts/audit_order_references.py`, a read-only local audit.

The checker is deliberately conservative and vocabulary-based; unrecognized
wording is not proof of agreement. The UI says “No material discrepancy detected,”
not that all customer assertions have been verified. All drafts still require
human review.

## Existing data preserved

Audits opened both existing SQLite files in read-only mode. Existing ticket,
draft, correction and original order rows have the same SHA-256 table-content
fingerprints before and after the review:

| Database / existing table | Rows | SHA-256 |
| --- | ---: | --- |
| `opspilot.db` / ticket | 5 | `0910f3e019e2d23eade7d2c0ffd2f91cb2203b5d9afb58082ff4a8ed46496357` |
| `opspilot.db` / replydraft | 0 | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |
| `opspilot.db` / ticketorderreference | 0 | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |
| `opspilot.db` / original order rows | 18 | `c9abc7b16ef2eda2de55cd554b4719eab295564d8d205116ae2979f62ba314a6` |
| `milestone3a-smoke.db` / ticket | 4 | `4e7dd5df2fe7ad6145daf54b43cdba886b1127e62229e157faa0998c9e79264a` |
| `milestone3a-smoke.db` / replydraft | 8 | `0a22e67fd5a9541f04a3fbba2197a3b0121a3b1d59d08a5ba590e77d52011e98` |
| `milestone3a-smoke.db` / ticketorderreference | 2 | `4c27bb4a7081caf884806111ec58520eadb7ebf4ed4b5cfa43303255bbde1a20` |
| `milestone3a-smoke.db` / order | 18 | `c9abc7b16ef2eda2de55cd554b4719eab295564d8d205116ae2979f62ba314a6` |

The new lamp ID was added as a missing fixture to `opspilot.db`, bringing its order
count to 19. The original 18 order rows were not altered. In particular, the legacy
lamp row at `7821` was **not** overwritten: the original smartphone ticket now
derives `product_mismatch` and `delivery_status_mismatch` warnings against it.
That legacy discrepancy remains for human review rather than being silently fixed.

## Validation

- **141 backend tests pass**, covering product/status mismatch, unknown orders,
  conflicting statements, matching orders, non-assertions, fixture preservation,
  historical snapshot checks and the read-only audit, plus the existing suites.
- **38 frontend tests pass**; the production build succeeds.
- The complete real Edge / local `qwen3.5:9b` flow passes, including the original
  Milestone 3A scenarios, visible review badges, a neutral conflict reply, explicit
  correction to the matching smartphone, persisted drafts, and desktop/mobile.
- QA uses `data/reliability-smoke.db` on ports 8010/5180. No existing ticket data
  was deleted or rewritten. No cloud inference, commits, pushes or 3B features.

Actual Qwen-assisted conflict draft:

> Thank you for explaining the issue.
>
> The details in your message and the available order information need clarification. The correct product and delivery details have not been confirmed.
>
> Please confirm the order ID, the product ordered, and whether the item was delivered. Human review is needed before order-specific advice can be given.
>
> We are here to help with any further questions.

Full final responses: [reliability-smoke.json](reliability-smoke.json).
Local screenshots: `.cache/smoke3a/conflict.png`, `desktop.png`, and `mobile.png`.
