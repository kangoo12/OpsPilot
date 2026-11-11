# Production scaling roadmap — future work only

None of the capabilities proposed here are implemented by Milestone 6. The current product is a local supervised prototype with fictional orders, no authentication/integrations/sending and a CONDITIONAL GO demo audit. This is a planning document, not a deployment commitment, cost quote, security certification or compliance claim.

## Readiness levels and strategy

| Level | Evidence required before claiming it |
| --- | --- |
| Demo | Trusted operator, fictional data, localhost, disclosed safety limits; current qualified decision |
| Limited pilot | Stage 0 safety gates + Stage 1 secure single-company operation + a narrowly authorized Stage 2 workflow + legal/privacy review |
| Production SaaS | Sustained pilot evidence, tested tenant isolation, repeatable releases/recovery, measured capacity and staffed operations |
| Enterprise | Customer-specific identity, retention/residency, security/legal obligations and exercised service commitments; not implied by SaaS launch |

Prefer a modular monolith: separate ingestion, ticketing, order context, drafting, review, sending and audit modules, with explicit interfaces and a shared transactional store. Add a durable worker/inference boundary when measurements require it. Avoid a microservice per current Python file. A roadmap stage can be deferred or stopped if discovery does not justify it.

Effort below means **engineer-weeks of focused implementation/validation**, not calendar guarantees. Estimates assume the current prototype can be evolved, substantial test reuse, one initial integration and access to product/security/legal reviewers. They exclude procurement, customer onboarding delays, model retraining, extensive legacy migration and certification. Ranges should be re-estimated after each exit gate. Suggested roles need not all be full-time.

## Stage 0 — safety and reliability gates

**Objective:** prevent the known dangerous relevance failure and establish evidence suitable for any real customer data/workflow. **Priority:** P0, blocking all real usage. **Effort:** 2–4 engineer-weeks initially; unresolved safety work can extend this indefinitely. **Roles:** backend/AI engineer, bilingual support-domain reviewer, QA/security reviewer, product owner.

**Prerequisites and dependencies:** preserve 5A–5D evidence; define permitted support actions, risk taxonomy and a company-approved policy owner. No sending until this gate passes. Data/rubric authors should be separated from implementation review where feasible.

**Deliverables:**

- Dedicated fail-closed handling for recognized physical danger/security/financial-risk cases. Route uncertain high-risk cases to a human queue; do not produce routine return/troubleshooting advice while an emergency is unresolved. Have qualified policy owners approve any safety guidance; never invent medical/emergency/company policy.
- Correct narrative-generation reliability without removing gender/language/narrative constraints or silently replacing meaningful summaries with generic content.
- Versioned prompt/model/policy/renderer manifests and a release-evaluation pipeline retaining all failures. Physical hazard detection, guard failure and model unavailability must have explicit operator outcomes.
- Factual-grounding/injection tests across paraphrases, mixed languages, missing/competing IDs, implied delivery contradictions, indirect role overrides and unsupported action demands. Human approval remains mandatory for any future outbound text.
- Blinded bilingual review with two adjudicators for disputed labels and semantic relevance, clarity, facts, risk and usefulness. Mark genuine label ambiguity explicitly before inference.

**Proposed measurable acceptance criteria (targets, not achieved scores):**

1. Freeze ≥500 newly authored/adjudicated classification cases, ≥250 per language, with ≥40 per category overall and representative missing/conflicting IDs. Accepted complete tuples ≥95% overall and ≥90% per language/category; invalid ordinary-message rejection rate ≤1%. Evaluate confidence intervals and subgroup counts, not just aggregate scores.
2. A separate ≥300-case critical-hazard/fraud/security suite has **zero observed missed urgent-or-human-risk-routing outcomes** and no reply inviting dangerous ordinary handling. A separate ≥200 ordinary/negated/historical-risk set has false urgent/risk routing ≤5%. Zero observed failures is a sample gate, not proof of zero real-world risk.
3. No invented IDs in the explicit extraction adversarial suite; uncertain competing references fail closed or remain null. Language and gender checks pass on all accepted outputs, including preserved product/name tokens.
4. ≥100 unseen reply scenarios, including ≥30 high-risk/uncertain contexts, show zero unsupported completed-action/approval/date claims under deterministic and adjudicated human review. ≥90% meet the documented usefulness rubric; every high-risk draft is suppressed/routed or rated appropriate by the qualified reviewer.
5. No regression to approval immutability, stale-context/version rejection, audit preservation, error visibility or safe unavailable-model behavior. Independent reviewer signs the release evidence, including rejected cases and limitations.

**Main risks:** template improvements may trade relevance against grounding; keyword risk detection can miss paraphrases or over-route ordinary requests; test authors may overfit. **Exit gate:** named domain/safety reviewer and product owner accept all targets or explicitly reject real usage. Do not average a safety failure away with many easy cases. If the gate fails, keep the product fictional/demo-only.

## Stage 1 — secure single-company pilot foundation

**Objective:** operate for one explicitly authorized company with accountable operators and recoverable data. **Priority:** P0 for pilot. **Effort:** 6–10 engineer-weeks. **Roles:** backend/platform engineer, frontend engineer, QA/security reviewer, operations owner; legal/privacy advisor as needed.

**Prerequisites:** Stage 0 accepted; selected pilot scope/data inventory and company policies approved. **Technical dependencies:** identity provider/session design, PostgreSQL target, migration tooling, secrets store, HTTPS termination, CI environment and recovery storage. Choose maintained components after a fresh security/version review; no specific current vendor price or library version is promised here.

**Deliverables:**

- Authentication, secure server sessions, expiry/revocation and least-privilege roles: viewer, support editor, approver, administrator. Reject direct API attempts outside role scope. Avoid treating frontend flags or a fixed actor string as authorization. Protect cookies, CSRF, origins/hosts, request sizes and rate limits at the relevant boundary.
- PostgreSQL persistence with explicit schema migrations, transactions/constraints and optimistic concurrency equivalents. Preserve original messages, source classifications, order snapshots, review versions, parent links, timestamps and audit provenance.
- Secrets/configuration separated from source, rotation and restricted service accounts; HTTPS, secure headers, backup encryption and controlled access. Logs redact customer content/secrets and carry request/job/operator IDs with defined retention.
- Containerized reproducible deployment, dependency/SBOM/license review, CI tests/type/build/security checks, staged releases and a restricted pilot environment. No public exposure of raw Ollama or admin endpoints.
- Structured health/metrics/alerts for queue/AI/storage errors, rejected outputs, approval conflicts, backup age and capacity. Document on-call owner and incident procedures.

**Migration and rollback:**

1. Export from a consistent read-only SQLite backup; inventory counts, stable IDs, UTC timestamps, JSON snapshots, authoritative workflow tables and legacy status fields. Do not merge snapshot and current states incorrectly.
2. Rehearse schema transformation/import into an isolated PostgreSQL staging database. Reproduce constraints, append-only/approved-history protection and indexes with PostgreSQL-compatible mechanisms. Validate row counts/content hashes, relationships, decisions, context hashes and API/analytics parity.
3. Test restore and rollback before cutover. Freeze writes for a bounded migration window, make an encrypted verified backup, migrate, reconcile and run acceptance checks. Prefer a simple cutover over untested dual writes.
4. Before reopening writes, rollback can return to the unchanged SQLite snapshot. **After PostgreSQL writes begin, do not switch blindly to stale SQLite:** stop writes and use a tested reverse/replay or fix-forward plan with preserved IDs/audit. State this decision point in the runbook.

**Acceptance criteria:** all privileged API tests deny wrong/expired roles; no cross-user unauthorized approval; migration parity across every original entity; stale/concurrent writes have one valid winner; staging restore meets a proposed pilot RPO ≤24 h / RTO ≤4 h; 14-day synthetic/shadow soak without lost records; no unresolved critical/high security findings before real data. RPO/RTO are proposed targets to validate, not current promises.

**Main risks:** identity gaps, history corruption during migration, insufficient log redaction, deployment secrets, backups that cannot restore. **Exit gate:** security review, recovery rehearsal and company approval for a private single-company pilot; no real outbound integration enabled yet.

## Stage 2 — authorized business integrations

**Objective:** one end-to-end pilot workflow with real source data and explicitly approved reply sending. **Priority:** P0 for the minimum pilot path; other connectors P2. **Effort:** 4–8 engineer-weeks for one inbox + one order source; each additional connector requires separate estimation. **Roles:** integration/backend engineer, support-domain owner, frontend/QA engineer, security reviewer.

**Prerequisites:** Stages 0/1, written connector/data/sending authorization, provider sandbox/credentials, documented mapping of policy/order fields. **Dependencies:** ingestion/outbox tables, durable worker queue, scoped credentials, webhook verification and reconciliation APIs.

**Deliverables:**

- Start read-only with an email inbox or helpdesk and Shopify/another ecommerce source chosen by the pilot. CRM and additional helpdesk connectors are optional extensions, not implemented prototype features.
- Verify webhook signatures/replay windows, record provider event IDs, normalize with provenance and synchronize orders with freshness/conflict status. Remote payloads remain untrusted. Handle missed webhooks by periodic reconciliation.
- Transactional inbox/outbox with unique event/send keys and explicit state machines. Bounded retries with backoff/jitter, poison-message/dead-letter review, correlation IDs and observable failure handling. Never promise exactly-once delivery merely because a queue retries.
- Bind sending authorization to authenticated actor, tenant/company, exact saved content revision, recipient, current context and idempotency key. Separate approval from dispatch permission where policy requires. Recheck at dispatch; edits/context changes invalidate the authorization.
- Delivery receipts, ambiguous provider timeouts and manual reconciliation. A timeout must not trigger duplicate sends. Store minimal necessary content/metadata with retention rules. Inbound attachments require explicit safe handling/scanning before extraction.
- No autonomous refunds, financial approvals or unapproved external actions. Provider cancellations/refunds remain out of pilot scope.

**Acceptance criteria:** repeated/reordered webhook fixtures create one logical record; crash/retry tests produce no duplicate logical send; expired/revoked/changed approvals block dispatch; failures reach an operator-visible queue within a proposed 5 minutes; rate-limit/outage/recovery tests reconcile without lost audit entries. A supervised sample of ≥100 sandbox/shadow conversations passes support-owner review before a narrowly authorized real-send pilot.

**Main risks:** credential scopes, provider policy/API changes, message loops, stale order data, wrong recipients, duplicate sends and customer content in logs. **Exit gate:** company explicitly approves limited real data and, separately, sending scope after sandbox evidence. Pilot begins with small volume and human-approved dispatch; rollback disables connectors/dispatch while retaining records and replay state.

## Stage 3 — multi-tenant SaaS

**Objective:** isolate organizations across every request, job, store and operation. **Priority:** P1 after a successful single-company pilot, P0 before a second real tenant shares infrastructure. **Effort:** 8–14 engineer-weeks. **Roles:** backend/security engineer, platform engineer, frontend/QA engineer, billing/product owner.

**Prerequisites:** stable Stage 2 workflow, documented tenant threat model, validated need for shared hosting. **Dependencies:** authenticated organization memberships, tenant-aware data layer, storage layout, job context and customer administration; a billing provider may be assessed later with authorization.

**Deliverables:**

- Organization/workspace model and scoped roles/invitations. Tenant identity comes from verified membership/session context, not a trusted client-supplied `tenant_id`.
- Consistent tenant enforcement in every DB query, join, object relationship, queue job, cache key, blob path, webhook, search index, metric and admin/export tool. Consider PostgreSQL row-level security with restricted application roles plus application checks; test both.
- Tenant-specific policies, connector credentials, model/prompt configuration boundaries, feature flags and usage quotas. Avoid hidden cross-tenant context in AI requests or prompt caches.
- Onboarding, workspace administration, ownership transfer, retention/deletion workflow and tenant-scoped backup/export/restore. Review the tension between audit immutability and legitimate deletion: minimize stored personal data and define lawful retention, redaction/tombstone/key-erasure approaches with counsel rather than promising “immutable forever.”
- Usage ledger and auditable metering foundations for subscription billing; reconcile charges/quotas separately from support ticket data. No payment-card handling inside the app.

**Acceptance criteria:** a comprehensive two-tenant/three-role API, worker, export and restore suite has zero observed cross-tenant leaks; adversarial swapped IDs and admin paths are denied; credential/prompt/cache isolation is tested; a tenant restore cannot overwrite another tenant; quota/replay tests do not double-charge usage. Independent isolation/security review and incident procedures are required.

**Main risks:** a missed join/filter, privileged database role bypass, shared inference/cache contamination, support-admin tools, logs/backup exports and incomplete deletion. **Why `tenant_id` alone is insufficient:** a column expresses ownership but does not enforce access; all paths and infrastructure need scoped authorization, constraints and adversarial tests. **Exit gate:** signed isolation review before onboarding tenant two; no unbounded self-service signup while controls remain unverified.

## Stage 4 — scalable AI infrastructure

**Objective:** meet measured latency/capacity/cost targets while preserving validation and tenant privacy. **Priority:** P1 when queue/latency measurements justify it; P2 for speculative infrastructure. **Effort:** 4–8 engineer-weeks for a first dedicated/queued service, then measurement-led increments. **Roles:** backend/ML-infrastructure engineer, platform/SRE, evaluation/QA owner.

**Prerequisites:** versioned Stage 0 evaluations and stable provider contract; actual pilot workload profile. **Dependencies:** durable queue, inference resource controls, telemetry with redaction, deployable model manifests and capacity budget. Stages 3/4 can overlap only with tenant-safe interfaces already defined.

**Deliverables:**

- A pluggable inference contract for classification/planning with timeout/error/structured-output semantics. The prototype currently supports only local Qwen; any future provider/model must pass equivalent evaluation, privacy, licensing and policy gates. A cloud provider is not automatically an acceptable fallback.
- Compare local per-company machines against dedicated private inference hosts. Pin model digest, quantization/runtime, prompt, schema, policy and renderer versions; evaluate before rollout and keep rollback manifests.
- Bounded inference concurrency, per-tenant fairness, admission control, cancellation, separate short classification/long tasks where measured, backpressure and operator-visible queue states. The current process-local lock is not a global multi-worker quota.
- End-to-end deadlines, bounded safe retries, circuit breakers and fallbacks to **human review or unavailable status**, never invented classification/replies or silently switched policy/model.
- Track input/output tokens, load/inference durations, queue depth/wait, GPU utilization/VRAM, failure/guard rates and per-tenant compute costs. Logs must not expose payloads by default.
- Cache only where justified with tenant, message/version, policy, verified context and model digest in the key. Avoid caching mutable authorization decisions or cross-tenant customer material; retention and invalidation are explicit.
- Stateless API replicas with shared durable jobs and transactional storage. Load-test representative distributions and cold starts, not one happy path. Decompose services only if independent scaling/failure/ownership needs justify it.

**Proposed acceptance criteria:** at a declared pilot profile (e.g. 5 concurrent operators, 10 new requests/minute, 2× short burst), warm classification p95≤5 s and reply p95≤10 s, bounded queue waits≤30 s, overload rejection visible and recoverable, no lost/duplicate logical jobs. Include cold-start results separately; meet targets with measured headroom and per-case quality unchanged. These are future goals, not extrapolations from the current one-second medians.

**Main risks:** VRAM pressure, unfair batching, cold-load latency, higher concurrency degrading determinism/quality, queue replay, data leakage through caches and unknown cost per useful output. **Exit gate:** documented capacity/cost envelope, tenant-safe load evidence, rollback exercise and ownership of alerts. Remain a monolith if it meets measured demand.

## Stage 5 — enterprise operations and governance

**Objective:** meet specific larger-customer identity, security, privacy and operational requirements. **Priority:** P2 until validated by a real opportunity; core incident/accessibility work starts earlier. **Effort:** 12–24+ engineer-weeks; external reviews/procurement can dominate calendar time. **Roles:** SRE/platform, security, frontend/accessibility specialist, privacy/legal advisor, enterprise product/support owner.

**Prerequisites:** operational SaaS evidence, tested tenant isolation and customer-specific requirements. **Dependencies:** enterprise identity integration, export/access control, region/storage choices, staffing and contractual review.

**Deliverables:** SSO/federated identity and lifecycle management; fine-grained least-privilege permissions; scoped audit exports with redaction/provenance; approved compliance workflows; data-residency options covering inference, storage, logs and backups; configurable retention/deletion; privacy-impact assessment process; incident triage/notification runbooks; disaster recovery and regional restore exercises. Accessibility audits and interface internationalization include keyboard/screen reader/contrast checks, localized dates/status/errors and bilingual policy review, not just model language selection.

GDPR applicability depends on activities, roles and territorial scope; local hosting alone grants no exemption. Before real EU personal-data use, qualified counsel should assess lawful basis/transparency, controller/processor terms, security, data-subject rights, retention/transfers, and whether a DPIA is required. See the [official GDPR text](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng/) (Articles 3, 5–6, 12–22, 28, 32–35 and Chapter V). This roadmap is not a legal determination or compliance claim.

**Acceptance criteria:** independently reviewed SSO/permission tests; customer-scoped export/deletion/restore drills; exercised incident tabletop and disaster recovery; accessibility audit with critical barriers resolved; legal/security approval of each contractual requirement. Propose SLOs (e.g. 99.5% monthly pilot availability initially) only after measuring end-to-end performance and staffing recovery; negotiate SLAs with exclusions/support coverage only when they can be funded and met. No certification is claimed without an actual applicable assessment.

**Main risks:** overstated compliance, residency gaps in logs/inference, untested recovery, human on-call capacity, inaccessible workflows and contracts exceeding engineering capability. **Exit gate:** customer-specific security/legal/operations sign-off; independent testing and a funded support/recovery plan. Enterprise readiness is not achieved merely by adding SSO.

## Stage 6 — product and commercial expansion

**Objective:** validate demand, economic viability and support obligations. **Priority:** P0 discovery in parallel with Stage 0; P1 paid expansion only after pilot safety/operations gates. **Effort:** 4–8 engineer-weeks for initial product instrumentation/onboarding/billing after validation; discovery/sales/support are ongoing. **Roles:** founder/product owner, customer researcher, support lead, backend/billing engineer, finance/legal advisor.

**Prerequisites:** explicit distinction between hypotheses and observed customer evidence. Paid live usage needs the applicable earlier readiness gates. **Dependencies:** consented product analytics, usage ledger, support process, pricing experiments and provider terms.

**Deliverables:**

- Interview ≥10 target ecommerce support teams; document existing workflow, Greek/English volume, approval requirements, data constraints and willingness to trial. Do not treat friendly feedback as willingness to pay.
- Recruit 1–3 authorized, bounded pilot companies only after the private-pilot gate. Obtain baseline and intervention measurements with documented confounders: handling time, drafts heavily edited, semantic errors, high-risk routing, operator confidence and support burden.
- Test pricing hypotheses: per-operator subscription, usage-capped workspace, dedicated/private inference premium. No price is validated yet. Avoid pricing only by tokens when inference/human-review/support dominate costs.
- Unit-economics ledger: hardware/hosting, inference load/idle, storage/backups, logs, connector fees, support/security review, sales/onboarding and payment fees. Measure cost per useful human-approved draft, not raw model output count.
- Consent-aware product analytics, feedback/rejection-reason collection, support ticketing/on-call process, cancellation/export flows and billing reconciliation. Expand ecommerce/CRM integrations only from demonstrated demand and maintenance budget.

**Acceptance criteria:** documented problem evidence from interviews; pilot owner accepts measurable workflow value with no safety-gate regression; unit economics include human/idle costs and remain viable across low/base/high usage scenarios; at least one explicit commercial commitment before claiming paying adoption; funded support/service commitments. Pricing/revenue claims require real verified transactions, not mock billing.

**Main risks:** solving a demonstration problem rather than customer pain, high operator-review overhead, low willingness to pay, connector maintenance and unsupported service promises. **Exit gate:** evidence-based continue/pivot/stop decision by product owner. Do not sell autonomous resolution or refund execution absent a separately authorized, validated product.

## Dependency-aware timeline and minimum pilot path

Illustrative calendar assuming two experienced engineers, part-time product/QA and timely specialist access; not a fixed schedule or a sum of all effort ranges. Discovery runs in parallel. Safety failures, procurement or legal requirements can stop the sequence.

| Calendar window | Work and dependency | Release decision |
| --- | --- | --- |
| Weeks 1–3 | Stage 0; customer discovery starts | Fictional demo only until safety gate passes |
| Weeks 4–9 | Stage 1 identity, storage migration, operations and security | Private staging; no real sending |
| Weeks 10–14 | Minimal Stage 2: one read-only inbox/order source, then sandbox approval/outbox | Legal/company authorization and restore/security evidence required |
| Weeks 15–18+ | Bounded single-company shadow pilot; separately authorized supervised sending only after gate | Limited pilot, not public SaaS |
| Months 5–8+ | Stage 3 if a second tenant is justified; Stage 4 only where measured | No shared tenancy before isolation gate |
| Months 8–12+ | Stage 5 customer-driven work and Stage 6 paid expansion | Enterprise/SLA commitments only after evidence and staffing |

Minimum viable pilot: **Stage 0 → Stage 1 → one narrowly scoped Stage 2 integration → authorized shadow validation → limited real workflow**. Do not wait for enterprise SSO or broad SaaS billing to learn from one company. Do not skip identity, safety, data protection, backup/restore or audit integrity to shorten the timeline. Real sending can remain disabled while triage/drafting value is assessed.

## Cost assumptions and measurement plan

These are illustrative budgeting inputs in EUR, **not current vendor quotes, validated pricing or total-cost estimates**. Refresh with actual invoices/procurement before commitments; taxes, geographic pricing and specialist services vary.

| Item | Planning assumption/range | What must be measured |
| --- | --- | --- |
| Small private pilot CPU app/PostgreSQL/backups/logs | €100–€500/month assumed | Data volume, redundancy, retention, operational tooling |
| Owned inference hardware | €1,500–€4,000 initial assumption; no purchase recommendation | Model fit, VRAM, lifecycle, warranty, idle/peak load and maintenance |
| Power example | 0.45 kW × 8 h/day × 22 days × €0.25/kWh = €19.80/month | Actual whole-system draw, duty cycle and local tariff; excludes idle/cooling/hardware |
| Dedicated inference capacity | Budget envelope €500–€2,500/month assumed | Runtime hours, memory, reserved/idle cost, throughput and support; obtain quotes |
| Engineering labor scenario | 12–22 engineer-weeks × €1,500–€3,000/week = €18k–€66k | Local rates, actual scope, overhead and specialist review; not a quoted pilot price |

Do not add all rows automatically: owned versus dedicated inference are alternatives, and labor excludes support/legal/security/procurement overruns. Stage estimates and the labor example cover different scopes; no whole-roadmap fixed price is implied. Build low/base/high monthly workload models and report cost per accepted useful draft, p95 latency and human-review minutes together. Revisit the architecture when cost, risk or usefulness fails the business gate, rather than assuming scale solves it.

## Release-governance rule

Every later stage needs a named owner, frozen evidence, change review, rollback trigger and explicit acceptance. Preserve the current known failures and all old benchmark scores. A model, prompt, provider, company policy or connector change is a new release candidate, not an opportunity to overwrite a prior result. Authentication, sending, new models, PostgreSQL, tenant isolation, deployment, billing and integrations remain **future work**.
