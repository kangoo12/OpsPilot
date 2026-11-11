# OpsPilot pitch pack

Suggested narration, not claims of market validation. Timing varies with delivery; rehearse before the event. Target-customer and business proposals are hypotheses.

## 30-second elevator pitch

OpsPilot is a local AI support-workflow prototype. It classifies English and Greek customer messages, checks fictional order records, and prepares constrained reply drafts for human review. Operators can edit, approve and trace revisions without sending anything. Local inference avoids cloud inference API charges, but hardware and operations still cost money. The final audit permits a supervised fictional-data demo; safety-related reply usefulness and some classification failures remain unresolved.

## 90-second product pitch

Customer support is not just an answer-writing problem. A useful workflow must identify the issue, recognize urgency, check the order, and make the human decision visible.

OpsPilot demonstrates that workflow locally. A customer message becomes a validated ticket. Verified fictional order data supplies context, while recognized discrepancies remain flagged. Qwen chooses a constrained reply plan, and the backend assembles facts and policy wording. A person reviews the draft, edits it and explicitly approves or rejects it. Approved content stays immutable; revisions and activity remain available. Approval sends no message.

Our possible audience is a small ecommerce support team that needs Greek and English handling and values control over where inference happens. That is a product hypothesis, not a claim of customers or demand. We are not claiming capabilities absent from existing helpdesks; our contribution is an inspectable implementation combining local inference, verification and review.

Historical synthetic testing showed 39 of 40 accepted exact classification label tuples on the 5B held-out set. That score excluded summary-language correctness: eleven English cases initially had Greek summaries, addressed in later validation. Some return requests still fail closed, and physical-danger replies can be inappropriate despite urgent classification. The next step is a measured safety gate and a secure single-company pilot, not public deployment of this demo.

## 3-minute presentation narrative

**0:00–0:35 — Problem.** “A support operator needs to understand an incoming message, assess urgency, check facts and decide what can safely be said. A fluent answer alone does not establish that the order is correct or an action happened. We built an inspectable workflow around those needs.”

**0:35–1:15 — Demonstration.** “Here is a fictional question about a lamp shipment. OpsPilot classifies it locally, then retrieves the dated fictional order. The reply preserves the estimate as an estimate. Qwen chooses a structured plan; the backend renders known facts. A human reviews and approves the saved draft, while activity/revisions remain visible. Nothing is sent and no order is changed.” Show the [main-case flow](demo-script.md) or explicitly labelled screenshots.

**1:15–1:45 — Why local and why structured.** “React, FastAPI, SQLite and Ollama run on one computer. Messages do not require a cloud inference API. That reduces one data-transfer boundary, not all privacy risk. We deliberately constrain reply construction and validate model output. Local inference has GPU, memory, electricity and maintenance costs; it is not free computing.”

**1:45–2:20 — Evidence and limitations.** “We kept frozen synthetic datasets and retained failures. The original 60-case complete label result moved from 43/60 to 56/60 during development. A separate 40-case held-out run reached 39/40 label tuples, but also exposed eleven wrong-language summaries. Later language constraints improved that issue; ordinary return messages can still be rejected, and safety replies can still be unhelpful. The final audit therefore says CONDITIONAL GO for a supervised demo, not production readiness.”

**2:20–2:45 — Intended customer and future product.** “We want to test whether smaller ecommerce teams value bilingual triage and controlled drafting with local or dedicated inference. No customer acquisition, revenue or time savings have been measured. Our roadmap starts with safety/reliability gates, then authenticated operator permissions, recoverable storage and one explicitly authorized integration. Multi-tenant SaaS comes later.”

**2:45–3:00 — Ownership and ask.** “Coding agents wrote the implementation and much of the testing/documentation. The human product owner defined constraints, selected scope, tested/reviewed work and accepted milestones. We are seeking feedback on usefulness and supervised pilot requirements, not asking anyone to trust autonomous refunds or unreviewed replies.”

Use [benchmark summary](benchmark-summary.md) for denominators and [judges' Q&A](judges-qa.md) for follow-up. Do not shorten the pitch by removing the safety limitation or turning historical held-out performance into current production accuracy.
