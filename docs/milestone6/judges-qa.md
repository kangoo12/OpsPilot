# Judges' Q&A — honest answers

## Why not use ChatGPT directly?

OpsPilot demonstrates application workflow: validated ticket records, verified fictional order lookup, separate review decisions, immutable approved drafts and queryable history. A general chat interface alone does not implement this repository's storage/workflow controls. We are not making a claim about every configuration or capability of another product.

## How is this different from existing helpdesk platforms?

The inspectable prototype combines local bilingual classification, constrained grounded drafting and a human audit trail. We have not established competitive novelty, superior accuracy or commercial differentiation through a market study. The value proposition needs customer discovery; mature helpdesks offer many integrations and operations features absent here.

## Can it hallucinate?

Yes, classification and summary semantics can still be wrong. Order IDs are evidence-constrained; reply prose is rendered from verified context and a restricted plan, reducing free-text factual invention. Those controls cannot prove helpfulness or catch every implicit contradiction. The real safety case received inappropriate routine return advice despite correct urgent classification. A human must review every draft.

## How are approvals enforced? Can someone call the API directly?

FastAPI checks confirmation, expected draft version, context fingerprint, documented order review where required, and finite content blockers. Short write transactions prevent stale/concurrent decisions; approved rows/history have SQLite mutation-protection triggers. Direct API approval bypass attempts are tested. A 5D gap allowed unrelated IDs after documented missing/conflicting context; it was reproduced and fixed. There is no authentication: any caller reaching the local API can act as the fixed Local Operator. This is not production authorization or administrator-proof audit evidence.

## What happens when AI fails?

There is a visible error and no fabricated replacement classification or draft. Unavailable/invalid/timeout/busy calls produce explicit errors. Already saved records remain readable while Ollama is offline. If a browser loses a write response, refresh before retrying because the outcome can be uncertain. The backup presentation uses labelled screenshots, never fake live inference.

## What about privacy?

Inference uses local Ollama and customer messages do not require a cloud inference API. The current demo uses fictional data only. Local SQLite/logs/backups still need protection; there is no production encryption/key-management, identity, retention or tenant-isolation product. Local operation alone does not establish legal compliance. Do not load real customer data into this prototype for a demonstration.

## How much does local inference cost?

There are no cloud inference API charges in this implementation. GPU/CPU hardware, power, maintenance and operator time still cost money. We measured latency, not commercial cost per resolved ticket or total ownership cost. The [roadmap](production-roadmap.md) provides explicit planning assumptions and a measurement method, not supplier quotes or a promised price.

## Can it scale?

It currently uses SQLite and a single inference lock per backend process; it has no durable job queue, multi-worker global concurrency control, quotas or tenancy. A pilot needs PostgreSQL, identity, measured limits and recoverable operations. More demand may justify dedicated inference, queues and backend replicas. Start with a modular monolith; no production architecture has been implemented merely because it appears on the roadmap.

## Is it production-ready?

No. Final audit: CONDITIONAL GO for a trusted, supervised fictional-data demo. Physical-danger reply usefulness is HIGH severity; some returns fail narrative validation; all reply semantics require human review. No live customer sending, real refunds, authentication or integrations exist. A real pilot must pass the documented gates first.

## What do the benchmark numbers actually mean?

5A: 43/60 accepted exact category/priority/order-ID tuples. 5B: 56/60 on that reused development set and 39/40 on a new 20-English/20-Greek set. “Complete” does not include every summary/reply semantic requirement: eleven held-out English cases had Greek summaries. 5C constrained language and physical-danger priority but retained narrative rejections. 5D's nine new classifications yielded eight accepted exact tuples. Small, same-author synthetic sets are not independent production samples. [Exact denominators and source links](benchmark-summary.md).

## Why did the held-out set matter, and was it truly independent?

Expectations were written before Qwen outputs and the implementation frozen before evaluation. New messages reduce direct reuse of development examples and exposed additional problems. However, the implementer also authored the set and knew the product rules. It was held out from those tuning runs, not externally blinded, statistically representative or permanently unseen after inspection. We preserve failures and require new adjudicated samples for future changes.

## How was it developed with coding agents? What did the human contribute?

AI coding agents wrote code, tests, audit helpers and documentation under the human product owner's requirements. The owner defined the product, local-only constraints and milestone scope, tested/reviewed outcomes and decided what to accept. We do not claim the human hand-wrote the repository or independently performed every automated audit. Agent-written tests can share implementation assumptions; real-model probes and a critical audit found failures despite green unit tests. Further human security/semantic review is still needed.

## Why not let AI send answers or issue refunds?

There are no sending/refund routes or external action tools. Classification is advisory; local approval records a human decision only. Any future sending needs authenticated permissions, explicit authorization, an auditable outbox, idempotency and failure recovery. Autonomous financial actions are outside the roadmap's proposed pilot.

## Are your dates and orders real? Are approved drafts truly immutable?

Orders are fictional fixed November 10, 2026 snapshots, including the November 14 estimate on the lamp. They are not today's carrier data. Approved content cannot be edited through the application; an edit creates a pending child and preserves the parent. SQLite triggers provide additional protection. A person controlling the database file can alter its protections; do not describe the history as cryptographically tamper-proof or authenticated non-repudiation.

## What is the license or traction?

No project license is currently declared, and no verified customers, paid subscriptions, revenue, certifications or measured productivity gains are claimed. The owner must choose licensing and review dependency/model terms before distribution or commercial commitments.
