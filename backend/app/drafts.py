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

router = APIRouter(tags=["reply drafts"])


def draft_read(draft: ReplyDraft, ticket) -> DraftRead:
    result = DraftRead.model_validate(draft)
    snapshot = result.order_context
    return result.model_copy(update={"snapshot_consistency": check_consistency(ticket.message, snapshot.order, snapshot.reference_order_id)})


def load_context(engine, ticket_id):
    with Session(engine) as session:
        ticket = require_ticket(session, ticket_id)
        return TicketRead.model_validate(ticket), ticket_order_context(session, ticket)


def save_draft(engine, ticket_id, context, text, language):
    with Session(engine) as session:
        # Never save a draft against an order reference changed during inference.
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        ticket = require_ticket(session, ticket_id)
        current = ticket_order_context(session, ticket)
        if current != context:
            raise ai_error(409, "order_changed", "Order details changed during generation. No draft was saved. Refresh and generate again.")
        draft = ReplyDraft(ticket_id=ticket_id, reply_text=text, language=language,
                           order_context=context.model_dump(mode="json"), policy_version=POLICY_VERSION)
        session.add(draft)
        session.commit()
        session.refresh(draft)
        return draft_read(draft, ticket)


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
        return DraftPage(items=[draft_read(draft, ticket) for draft in drafts], total=total)
