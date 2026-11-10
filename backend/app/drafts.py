from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func
from sqlmodel import Session, select
from starlette.concurrency import run_in_threadpool

from app.classifier import ai_error
from app.consistency import check_consistency
from app.models import ReplyDraft
from app.orders import require_ticket, ticket_order_context
from app.reply_generator import POLICIES, POLICY_VERSION, generate_reply
from app.schemas import TicketRead
from app.support_schemas import DraftPage, DraftRead
from app.tickets import get_ollama_client
from app.workflow_common import approval_blockers, audit, ensure_review, normalized_snapshot
from app.workflow_models import DraftReview, DraftRevision

router = APIRouter(tags=["reply drafts"])


def draft_read(draft: ReplyDraft, ticket, session: Session) -> DraftRead:
    result = DraftRead.model_validate(draft)
    snapshot = result.order_context
    review = session.get(DraftReview, draft.id) or DraftReview(draft_id=draft.id, content=draft.reply_text,
                  updated_at=draft.created_at, review_context=normalized_snapshot(ticket, draft.order_context).model_dump(mode="json"))
    context = ticket_order_context(session, ticket)
    count = session.exec(select(func.count(DraftRevision.id)).where(DraftRevision.draft_id == draft.id)).one()
    return DraftRead.model_validate({**result.model_dump(),
        "snapshot_consistency": check_consistency(ticket.message, snapshot.order, snapshot.reference_order_id),
        "original_content": draft.reply_text, "reply_text": review.content, "status": review.status,
        "version": review.version, "updated_at": review.updated_at, "approved_at": review.approved_at,
        "rejected_at": review.rejected_at, "reviewer": review.reviewer, "rejection_reason": review.rejection_reason,
        "parent_draft_id": review.parent_draft_id, "origin": review.origin, "revision_count": count or 1,
        "review_context": review.review_context,
        "approval_blockers": approval_blockers(session, ticket, draft, review, context),
    })


def load_context(engine, ticket_id):
    with Session(engine) as session:
        ticket = require_ticket(session, ticket_id)
        return TicketRead.model_validate(ticket), ticket_order_context(session, ticket)


def save_draft(engine, ticket_id, context, text, language, parent_id=None, expected_parent_version=None):
    with Session(engine) as session:
        # Never save a draft against an order reference changed during inference.
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        ticket = require_ticket(session, ticket_id)
        current = ticket_order_context(session, ticket)
        if current != context:
            raise ai_error(409, "order_changed", "Order details changed during generation. No draft was saved. Refresh and generate again.")
        if parent_id:
            from app.workflow import require_draft, check_version
            _, parent = require_draft(session, ticket_id, parent_id)
            parent_review = ensure_review(session, parent, ticket)
            check_version(parent_review, expected_parent_version)
        draft = ReplyDraft(ticket_id=ticket_id, reply_text=text, language=language,
                           order_context=context.model_dump(mode="json"), policy_version=POLICY_VERSION)
        session.add(draft)
        session.flush()
        ensure_review(session, draft, ticket, actor="Local AI", parent=parent_id)
        if parent_id:
            audit(session, ticket_id, "draft_regenerated", data={"parent_draft_id": str(parent_id), "draft_id": str(draft.id)})
        session.commit()
        session.refresh(draft)
        return draft_read(draft, ticket, session)


@router.get("/api/support-policies")
def support_policies():
    return {"version": POLICY_VERSION, "is_fictional": True, "policies": POLICIES}


@router.post("/api/tickets/{ticket_id}/drafts", response_model=DraftRead, status_code=201)
async def create_draft(ticket_id: UUID, request: Request,
                       client: Annotated[httpx.AsyncClient, Depends(get_ollama_client)]):
    ticket, context = await run_in_threadpool(load_context, request.app.state.engine, ticket_id)
    lock = request.app.state.classification_lock
    if lock.locked():
        raise ai_error(429, "ai_busy", "Local AI is processing another request. Wait for it to finish and try again.")
    async with lock:
        text, language = await generate_reply(ticket, context, client, request.app.state.settings)
        return await run_in_threadpool(save_draft, request.app.state.engine, ticket_id, context, text, language)


@router.get("/api/tickets/{ticket_id}/drafts", response_model=DraftPage)
def list_drafts(ticket_id: UUID, request: Request,
                limit: Annotated[int, Query(ge=1, le=50)] = 20,
                offset: Annotated[int, Query(ge=0)] = 0):
    with Session(request.app.state.engine) as session:
        ticket = require_ticket(session, ticket_id)
        drafts = session.exec(select(ReplyDraft).where(ReplyDraft.ticket_id == ticket_id)
                              .order_by(ReplyDraft.created_at.desc(), ReplyDraft.id.desc()).offset(offset).limit(limit)).all()
        total = session.exec(select(func.count(ReplyDraft.id)).where(ReplyDraft.ticket_id == ticket_id)).one()
        return DraftPage(items=[draft_read(draft, ticket, session) for draft in drafts], total=total)
