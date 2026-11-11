# Supervised demo — approximately 4 minutes

Purpose: show a reviewable support workflow using fictional data. Current release decision is CONDITIONAL GO. Never approve physical-danger replies or describe the prototype as autonomous support.

## Preflight — presenter must perform before the event

1. Follow [README quick start](../../README.md) in fresh PowerShell terminals. Set the backend database explicitly to `.cache/milestone6/live-demo.db` (or a new repository-local rehearsal filename), backend 8018, frontend proxy 8018, frontend 5197. These ports differ from normal 8000/5173.
2. Confirm the backend terminal/environment points to that exact isolated path before any submit/edit/approval. For an extra non-writing identity check, from the root in that same environment:

   ```powershell
   .\backend\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); from app.config import Settings; print(Settings().database_path)"
   ```

   The printed path must end in `.cache/milestone6/live-demo.db`, never `data/opspilot.db`. Preserve existing data; use a new filename for a new rehearsal. Startup seeds the 19 fictional orders, not example tickets.
3. Visit <http://127.0.0.1:5197>. **Check connections** should show Backend and Local AI connected. `ollama list` must include `qwen3.5:9b`. Green means reachable/installed, not warmed or accurate inference.
4. Read the exact normal delivery case and order snapshot below. Decide which saved fictional ticket to show if a prior rehearsal already exists. Do not claim live tracking; dates are fixed November 2026 fixtures.
5. Open the [five screenshots](screenshots/README.md), [5D report](../milestone5d/final-quality-report.md), and [benchmark summary](benchmark-summary.md) as an offline backup. A screenshot is archival evidence, never a live response.
6. Rehearse once on the isolated database, check visible text before approval and time the complete presentation. **Human rehearsal has not been certified by this package.** Leave spare time for model loading; never hide an error or repeatedly resubmit an uncertain write.

## One audited fictional case

Paste exactly:

> Please check the shipment progress of order DEMO-LAMP-9001. The tracking page has not changed for two days.

The original 5D browser run accepted `delivery`, `medium`, `DEMO-LAMP-9001`. Summary wording can differ and fresh inference can fail; this is an observed outcome, not a guaranteed script.

Fresh synthetic order facts: LumaLite desk lamp, ordered 2026-11-06, in transit in the 2026-11-10 snapshot, estimated delivery 2026-11-14, return period not started, warranty review available. No real carrier/merchant is connected.

## Live sequence

| Time | Screen and action | Narration / evidence |
| --- | --- | --- |
| 0:00–0:30 | Smart Inbox; point to Backend and Local AI | “Support work needs context and review, not just a generated answer. This prototype runs inference locally and uses fictional orders.” |
| 0:30–1:10 | **New customer message** → paste case → **Classify & save ticket** | “Qwen proposes structured labels and concise summaries. The backend validates before saving.” Wait for loading; read actual category/priority/ID. Do not narrate the expected labels as if already returned. |
| 1:10–1:50 | Selected ticket → **Order Details** | “This is a dated synthetic order snapshot. The reference matches a lamp in transit; November 14 is an estimate, not a delivery guarantee.” Show eligibility and original extracted reference. No manual correction is needed. |
| 1:50–2:40 | **AI Reply** → **Generate suggested reply** | “The model selects a restricted plan. The backend renders verified facts and known policy wording.” Read the actual draft. It must not claim a sent message, refund, performed escalation or guaranteed arrival. |
| 2:40–3:15 | **Edit reply** → add a neutral closing such as “Please let us know if you need further clarification.” → **Save Draft** → **Approve** → **Confirm approval** | “A person reviews the saved revision. Approval is recorded; nothing is sent, and the ticket remains in its existing status.” Approve only if facts/language are appropriate and the control is enabled. |
| 3:15–3:45 | **Activity History**; optionally AI Reply → **Draft revision history** | “Edits and decisions remain visible. Approved text is immutable; a later edit creates a new pending child.” Show the recorded approval and preserved original/revisions. Avoid extra live regeneration to save time. |
| 3:45–4:15 | **Analytics** | “These counts come from this SQLite workspace, not invented AI statistics. They update with stored tickets and decisions.” A first-run live database may have one ticket; archival screenshots have 26 QA tickets. |
| 4:15–4:40 | Closing / benchmark summary | “The audit permits a supervised fictional demo. Safety replies and some narrative validation remain unresolved; production requires explicit safety, identity and integration gates.” |

If ahead of schedule, demonstrate searching `DEMO-LAMP-9001` and the Delivery filter, then explain Analytics is independent of Inbox filters. Do not squeeze additional risky cases into the main flow.

## Safe failure and backup

- Model unavailable/timeout/invalid summary: show the actual error. Explain that validation saves no substitute ticket/draft. Do not weaken a validator or change the model/settings during the presentation.
- Lost save response: refresh the list before resubmitting. A timeout at the browser does not prove the backend failed to save.
- If inference is unavailable, switch to the clearly labelled saved 5D screenshot sequence. It contains the actual prior pending draft and observed workflow. State “This is recorded evidence from our synthetic QA run.” Continue with architecture, limits and the unchanged benchmark report.
- Offline screenshots require no Ollama/backend; saved database reads require the backend but no inference. Do not mock a green badge or fabricate a live reply.
- If approval is blocked, display the reason. Do not document a fake review or change facts to bypass it. Explain context/version checks and continue with recorded evidence.

## Optional safety segment — separate from the main case

Use the recorded D05 result in [5D evidence](../milestone5d/ai-results-v1.jsonl): a smoking/melting charger classified returns/urgent, while its reply gave routine return-policy guidance. Show the failure as a reason for human oversight and the Stage 0 roadmap gate. **Do not generate, approve or present this reply as suitable customer advice.** No new safety inference is necessary.

The presenter must identify any additional subjective claims as personal evaluation. No live emailing, refunds or real customer data belong in this demonstration.
