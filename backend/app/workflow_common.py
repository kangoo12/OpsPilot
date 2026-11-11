import hashlib
import json
import re
from datetime import timezone

from fastapi import HTTPException
from sqlmodel import select

from app.consistency import check_consistency, delivery_claims, normalize, products_in
from app.support_schemas import TicketOrderLookup
from app.workflow_models import AuditEvent, DiscrepancyResolution, DraftReview, DraftRevision, now

LOCAL_OPERATOR = "Local Operator"
TRANSITIONS = {
    "new": ["in_progress"],
    "in_progress": ["waiting_for_customer", "resolved"],
    "waiting_for_customer": ["in_progress", "resolved"],
    "resolved": ["in_progress"],
}


def iso_time(value):
    return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value).isoformat()


def conflict(message, code="stale_update"):
    raise HTTPException(409, detail={"code": code, "message": message})


def fingerprint(context) -> str:
    values = context.model_dump(mode="json", exclude={"context_fingerprint"})
    return hashlib.sha256(json.dumps(values, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def normalized_snapshot(ticket, values) -> TicketOrderLookup:
    snapshot = TicketOrderLookup.model_validate(values)
    snapshot.consistency = check_consistency(ticket.message, snapshot.order, snapshot.reference_order_id)
    return snapshot


def audit(session, ticket_id, event_type, actor=LOCAL_OPERATOR, data=None, timestamp=None, dedupe_key=None):
    session.add(AuditEvent(ticket_id=ticket_id, event_type=event_type, actor=actor,
                           data=data or {}, created_at=timestamp or now(), dedupe_key=dedupe_key))


def revision(session, review, action, actor=LOCAL_OPERATOR, reason=None):
    session.add(DraftRevision(draft_id=review.draft_id, version=review.version, content=review.content,
                             status=review.status, actor=actor, action=action, reason=reason,
                             created_at=review.updated_at, review_context=review.review_context))


def ensure_review(session, draft, ticket, *, actor="Historical import", parent=None, origin="ai"):
    review = session.get(DraftReview, draft.id)
    if review:
        return review
    context = normalized_snapshot(ticket, draft.order_context)
    review = DraftReview(draft_id=draft.id, content=draft.reply_text, updated_at=draft.created_at,
                         review_context=context.model_dump(mode="json"), parent_draft_id=parent, origin=origin)
    session.add(review)
    session.flush()
    revision(session, review, "created", actor)
    audit(session, ticket.id, "draft_generated" if origin == "ai" else "draft_revision_created", actor,
          {"draft_id": str(draft.id), "parent_draft_id": str(parent) if parent else None,
           "origin": origin, "historical_import": actor == "Historical import"}, draft.created_at,
          f"draft_created:{draft.id}")
    return review


def current_resolution(session, ticket_id, context):
    return session.exec(select(DiscrepancyResolution).where(
        DiscrepancyResolution.ticket_id == ticket_id,
        DiscrepancyResolution.context_fingerprint == fingerprint(context),
    ).order_by(DiscrepancyResolution.created_at.desc())).first()


def content_blockers(content: str, context) -> list[str]:
    """Deterministic checks complement, but cannot replace, human semantic review."""
    blockers = []
    text = normalize(content)
    for match in re.finditer(r"\b(?:refund(?:ed| (?:is |has been )?approved)|guarantee(?:d)?|escalated|cancelled|canceled|αποζημιωθηκε|εγκριθηκε|εγγυημεν\w*)\b", text):
        before = re.split(r"[.;!\n]", text[max(0, match.start() - 65):match.start()])[-1]
        # Ordinary policy discussions ('a refund', 'refund review') are allowed;
        # assertions of approvals/actions/guarantees are not.
        token = match[0]
        if token == "refund" or token in {"cancelled", "canceled"} and context.order and context.order.delivery_status == "cancelled":
            continue
        if not re.search(r"\b(?:not|no|never|without|δεν|μη|χωρις)\b", before):
            blockers.append("The reply asserts an unperformed action, approval or delivery guarantee. Remove that claim.")
            break
    if re.search(r"\b(?:we|i)\s+(?:have\s+|already\s+|will\s+)?(?:issue[ds]?|process(?:ed)?|send|sent|approv(?:e|ed)|refund(?:ed)?|cancel(?:led|ed)?|contact(?:ed)?|escalat(?:e|ed)|ship(?:ped)?)\b|\b(?:εχουμε\s+(?:επιστρεψει|στειλει|εγκρινει|ακυρωσει)|επιστρεψαμε|στειλαμε|εγκριναμε|ακυρωσαμε|θα επιστρεψουμε)\b", text):
        blockers.append("The application has not sent messages, issued refunds or performed external actions.")
    if re.search(r"\b(?:will arrive|delivery|παραδοση)\s+(?:is\s+)?(?:today|tomorrow|σημερα|αυριο)\b", text):
        blockers.append("Use verified calendar dates only, without promising an unverified delivery day.")
    dates = set(re.findall(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b", content))
    material = context.consistency.status == "discrepancy"
    if material or not context.order:
        if products_in(content) or delivery_claims(content) or dates:
            blockers.append("Unverified or conflicting order information must be omitted. Ask for clarification instead.")
    else:
        order = context.order
        allowed_dates = {str(order.snapshot_date), str(order.order_date), str(order.estimated_delivery_date)}
        if dates - allowed_dates:
            blockers.append("The draft contains a date not present in the verified order record.")
        checked = check_consistency(content, order, context.reference_order_id)
        if checked.status == "discrepancy":
            blockers.append("The draft's product or delivery statements conflict with the verified order record.")
    # Documenting missing/disputed facts never authorizes an unrelated reference.
    # The supplied ID may still be repeated to ask for clarification.
    from app.classifier import order_candidates
    allowed_references = {context.reference_order_id}
    if context.order:
        allowed_references.add(context.order.id)
    if set(order_candidates(content)) - allowed_references:
        blockers.append("The reply refers to an order ID outside the verified context.")
    return list(dict.fromkeys(blockers))


def approval_blockers(session, ticket, draft, review, context):
    if review.status != "pending_review":
        return ["Only a pending draft can be approved."]
    blockers = []
    basis = normalized_snapshot(ticket, review.review_context)
    if fingerprint(basis) != fingerprint(context):
        blockers.append("Order context changed. Regenerate the draft or save an edited revision against the current context.")
    if context.consistency.requires_human_review and not current_resolution(session, ticket.id, context):
        blockers.append("Document the current order discrepancy or missing information with a reason before approval.")
    blockers.extend(content_blockers(review.content, context))
    return list(dict.fromkeys(blockers))
