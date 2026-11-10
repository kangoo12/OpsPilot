from typing import Annotated, Literal
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func
from sqlmodel import Session, select
from starlette.concurrency import run_in_threadpool

from app.models import ReplyDraft
from app.classifier import ai_error
from app.reply_generator import generate_reply
from app.tickets import get_ollama_client
from app.schemas import TicketRead
from app.orders import require_ticket, ticket_order_context, ticket_read
from app.workflow_common import LOCAL_OPERATOR, TRANSITIONS, approval_blockers, audit, conflict, current_resolution, ensure_review, fingerprint, iso_time, revision
from app.workflow_models import AuditEvent, DiscrepancyResolution, DraftReview, DraftRevision, TicketWorkflow, now

router = APIRouter(tags=["human workflow"])
ContextHash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    @field_validator("confirmed", mode="before", check_fields=False)
    @classmethod
    def explicit_confirmation(cls, value):
        if value is not True:
            raise ValueError("Explicit confirmation is required")
        return value


class VersionRequest(RequestModel):
    expected_version: int = Field(ge=1)


class EditRequest(VersionRequest):
    context_fingerprint: ContextHash
    reply_text: str = Field(min_length=1, max_length=4000)


class DecisionRequest(VersionRequest):
    context_fingerprint: ContextHash
    confirmed: Literal[True]


class RejectRequest(DecisionRequest):
    reason: str = Field(min_length=5, max_length=1000)


class ResolutionRequest(RequestModel):
    context_fingerprint: ContextHash
    reason: str = Field(min_length=10, max_length=1000)
    confirmed: Literal[True]


class StatusRequest(VersionRequest):
    status: Literal["new", "in_progress", "waiting_for_customer", "resolved"]
    confirmed: Literal[True]


def require_draft(session, ticket_id, draft_id):
    ticket = require_ticket(session, ticket_id)
    draft = session.get(ReplyDraft, draft_id)
    if not draft or draft.ticket_id != ticket_id:
        raise HTTPException(404, detail={"code": "draft_not_found", "message": "Draft not found for this ticket."})
    return ticket, draft


def check_version(current, expected):
    if current.version != expected:
        conflict("This record changed in another request. Refresh before applying your changes.")


def check_context(context, expected):
    if fingerprint(context) != expected:
        conflict("Order information changed. Refresh and review the current details.", "order_changed")


def workflow_view(session, ticket):
    context = ticket_order_context(session, ticket)
    state = session.get(TicketWorkflow, ticket.id)
    status = state.status if state else str(ticket.status)
    resolution = current_resolution(session, ticket.id, context)
    return {"status": status, "version": state.version if state else 1,
            "allowed_transitions": TRANSITIONS[status], "context_fingerprint": fingerprint(context),
            "consistency": context.consistency.model_dump(), "operator": LOCAL_OPERATOR,
            "identity_is_authenticated": False,
            "resolution": {"id": str(resolution.id), "reason": resolution.reason, "actor": resolution.actor,
                           "created_at": iso_time(resolution.created_at), "context_fingerprint": resolution.context_fingerprint} if resolution else None}


@router.get("/api/tickets/{ticket_id}/workflow")
def get_workflow(ticket_id: UUID, request: Request):
    with Session(request.app.state.engine) as session:
        return workflow_view(session, require_ticket(session, ticket_id))


@router.patch("/api/tickets/{ticket_id}/status")
def change_status(ticket_id: UUID, body: StatusRequest, request: Request):
    with Session(request.app.state.engine) as session:
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        ticket = require_ticket(session, ticket_id)
        state = session.get(TicketWorkflow, ticket_id)
        if not state:
            state = TicketWorkflow(ticket_id=ticket_id, status=str(ticket.status))
            session.add(state)
        check_version(state, body.expected_version)
        if body.status not in TRANSITIONS[state.status]:
            conflict(f"Transition from {state.status} to {body.status} is not allowed.", "invalid_transition")
        previous = state.status
        state.status = body.status; state.version += 1; state.updated_at = now()
        audit(session, ticket_id, "ticket_status_changed", data={"previous": previous, "new": body.status, "version": state.version})
        session.commit()
        return ticket_read(session, ticket)


@router.post("/api/tickets/{ticket_id}/discrepancy-resolutions", status_code=201)
def document_discrepancy(ticket_id: UUID, body: ResolutionRequest, request: Request):
    with Session(request.app.state.engine) as session:
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        ticket = require_ticket(session, ticket_id)
        context = ticket_order_context(session, ticket)
        check_context(context, body.context_fingerprint)
        if not context.consistency.requires_human_review:
            raise HTTPException(422, detail={"code": "no_discrepancy", "message": "There is no current discrepancy or missing order information to document."})
        if current_resolution(session, ticket_id, context):
            conflict("This context already has a documented human review. It remains in the activity history.", "already_documented")
        resolution = DiscrepancyResolution(ticket_id=ticket_id, context_fingerprint=fingerprint(context), reason=body.reason,
                                          actor=LOCAL_OPERATOR, context=context.model_dump(mode="json"))
        session.add(resolution); session.flush()
        audit(session, ticket_id, "discrepancy_documented", data={"resolution_id": str(resolution.id), "reason": body.reason,
                                                                "context_fingerprint": resolution.context_fingerprint})
        session.commit()
        return workflow_view(session, ticket)


@router.patch("/api/tickets/{ticket_id}/drafts/{draft_id}")
def edit_draft(ticket_id: UUID, draft_id: UUID, body: EditRequest, request: Request):
    from app.drafts import draft_read
    with Session(request.app.state.engine) as session:
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        ticket, source = require_draft(session, ticket_id, draft_id)
        review = ensure_review(session, source, ticket)
        check_version(review, body.expected_version)
        context = ticket_order_context(session, ticket)
        check_context(context, body.context_fingerprint)
        if body.reply_text == review.content:
            conflict("The content is unchanged. Edit it or regenerate a draft before saving.", "unchanged_content")
        if review.status != "pending_review":
            draft = ReplyDraft(ticket_id=ticket_id, reply_text=body.reply_text, language=source.language,
                               order_context=context.model_dump(mode="json"), policy_version=source.policy_version)
            session.add(draft); session.flush()
            child = ensure_review(session, draft, ticket, actor=LOCAL_OPERATOR, parent=source.id, origin="human_revision")
            audit(session, ticket_id, "draft_edited", data={"draft_id": str(draft.id), "parent_draft_id": str(source.id),
                                                          "previous_status": review.status, "new_status": "pending_review"})
        else:
            draft = source
            previous_version = review.version
            review.content = body.reply_text; review.version += 1; review.updated_at = now(); review.reviewer = LOCAL_OPERATOR
            review.review_context = context.model_dump(mode="json")
            revision(session, review, "edited")
            audit(session, ticket_id, "draft_edited", data={"draft_id": str(source.id), "previous_version": previous_version,
                                                          "new_version": review.version, "context_fingerprint": fingerprint(context)})
        session.commit()
        return draft_read(draft, ticket, session)


def decide(ticket_id, draft_id, body, request, approve):
    from app.drafts import draft_read
    with Session(request.app.state.engine) as session:
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        ticket, draft = require_draft(session, ticket_id, draft_id)
        review = ensure_review(session, draft, ticket)
        check_version(review, body.expected_version)
        context = ticket_order_context(session, ticket)
        check_context(context, body.context_fingerprint)
        if review.status != "pending_review":
            conflict("This draft has already been reviewed. Create a new pending revision to change it.", "already_reviewed")
        if approve:
            blockers = approval_blockers(session, ticket, draft, review, context)
            if blockers:
                conflict(" ".join(blockers), "approval_blocked")
        review.status = "approved" if approve else "rejected"
        review.updated_at = now(); review.version += 1; review.reviewer = LOCAL_OPERATOR
        if approve:
            review.approved_at = review.updated_at
        else:
            review.rejected_at = review.updated_at; review.rejection_reason = body.reason
        revision(session, review, review.status, reason=None if approve else body.reason)
        audit(session, ticket_id, f"draft_{review.status}", data={"draft_id": str(draft_id), "version": review.version,
                                                               "reason": None if approve else body.reason, "message_sent": False},
              dedupe_key=f"draft_{review.status}:{draft_id}")
        session.commit()
        return draft_read(draft, ticket, session)


@router.post("/api/tickets/{ticket_id}/drafts/{draft_id}/approve")
def approve_draft(ticket_id: UUID, draft_id: UUID, body: DecisionRequest, request: Request):
    return decide(ticket_id, draft_id, body, request, True)


@router.post("/api/tickets/{ticket_id}/drafts/{draft_id}/reject")
def reject_draft(ticket_id: UUID, draft_id: UUID, body: RejectRequest, request: Request):
    return decide(ticket_id, draft_id, body, request, False)


@router.get("/api/tickets/{ticket_id}/drafts/{draft_id}/revisions")
def get_revisions(ticket_id: UUID, draft_id: UUID, request: Request):
    with Session(request.app.state.engine) as session:
        ticket, draft = require_draft(session, ticket_id, draft_id)
        items = session.exec(select(DraftRevision).where(DraftRevision.draft_id == draft_id).order_by(DraftRevision.version)).all()
        if not items:
            return [{"draft_id": str(draft.id), "version": 1, "content": draft.reply_text, "status": "pending_review",
                     "actor": "Historical import", "action": "created", "created_at": iso_time(draft.created_at), "reason": None}]
        return [{"draft_id": str(item.draft_id), "version": item.version, "content": item.content, "status": item.status,
                 "actor": item.actor, "action": item.action, "created_at": iso_time(item.created_at), "reason": item.reason} for item in items]


@router.get("/api/tickets/{ticket_id}/activity")
def get_activity(ticket_id: UUID, request: Request, limit: Annotated[int, Query(ge=1, le=100)] = 30,
                 offset: Annotated[int, Query(ge=0)] = 0):
    with Session(request.app.state.engine) as session:
        require_ticket(session, ticket_id)
        items = session.exec(select(AuditEvent).where(AuditEvent.ticket_id == ticket_id).order_by(AuditEvent.id.desc()).offset(offset).limit(limit)).all()
        total = session.exec(select(func.count(AuditEvent.id)).where(AuditEvent.ticket_id == ticket_id)).one()
        return {"items": [{"id": item.id, "event_type": item.event_type, "ticket_id": str(item.ticket_id), "actor": item.actor,
                           "created_at": iso_time(item.created_at), "data": item.data} for item in items], "total": total}


def load_regeneration(engine, ticket_id, draft_id, body):
    with Session(engine) as session:
        ticket, draft = require_draft(session, ticket_id, draft_id)
        review = session.get(DraftReview, draft.id)
        if (review.version if review else 1) != body.expected_version:
            conflict("This draft changed. Refresh before regenerating it.")
        context = ticket_order_context(session, ticket)
        check_context(context, body.context_fingerprint)
        return TicketRead.model_validate(ticket), context


@router.post("/api/tickets/{ticket_id}/drafts/{draft_id}/regenerate", status_code=201)
async def regenerate_draft(ticket_id: UUID, draft_id: UUID, body: DecisionRequest, request: Request,
                           client: Annotated[httpx.AsyncClient, Depends(get_ollama_client)]):
    from app.drafts import save_draft
    ticket, context = await run_in_threadpool(load_regeneration, request.app.state.engine, ticket_id, draft_id, body)
    lock = request.app.state.classification_lock
    if lock.locked():
        raise ai_error(429, "ai_busy", "Local AI is processing another request. Please try again shortly.")
    async with lock:
        content, language = await generate_reply(ticket, context, client, request.app.state.settings)
        return await run_in_threadpool(save_draft, request.app.state.engine, ticket_id, context, content, language, draft_id, body.expected_version)
