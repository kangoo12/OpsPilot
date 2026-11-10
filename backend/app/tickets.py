from typing import Annotated, Literal
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_
from sqlmodel import Session, select
from starlette.concurrency import run_in_threadpool

from app.classifier import ai_error, classify_message
from app.models import Ticket, TicketOrderReference
from app.orders import ticket_read
from app.workflow_common import audit
from app.workflow_models import TicketWorkflow
from app.schemas import Category, Priority, TicketCounts, TicketCreate, TicketPage, TicketRead, TicketStatus

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


def get_ollama_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.ollama_client


def save_ticket(engine, message, classification) -> TicketRead:
    with Session(engine) as session:
        ticket = Ticket(message=message, **classification.model_dump())
        session.add(ticket)
        session.flush()
        session.add(TicketWorkflow(ticket_id=ticket.id))
        audit(session, ticket.id, "ticket_created", data={"category": ticket.category, "priority": ticket.priority},
              dedupe_key=f"ticket_created:{ticket.id}")
        session.commit()
        session.refresh(ticket)
        return ticket_read(session, ticket)


@router.post("", response_model=TicketRead, status_code=201)
async def create_ticket(
    body: TicketCreate, request: Request,
    client: Annotated[httpx.AsyncClient, Depends(get_ollama_client)],
):
    lock = request.app.state.classification_lock
    if lock.locked():
        raise ai_error(429, "ai_busy", "Local AI is already processing a message. Wait for it to finish and try again.")
    async with lock:
        classification = await classify_message(body.message, client, request.app.state.settings)
        return await run_in_threadpool(save_ticket, request.app.state.engine, body.message, classification)


@router.get("", response_model=TicketPage)
def list_tickets(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: str | None = None,
    category: Category | Literal[""] | None = None,
    priority: Priority | Literal[""] | None = None,
    status: TicketStatus | Literal[""] | None = None,
):
    term = (search or "").strip()
    current_status = func.coalesce(TicketWorkflow.status, Ticket.status)
    conditions = []
    if category:
        conditions.append(Ticket.category == category)
    if priority:
        conditions.append(Ticket.priority == priority)
    if status:
        conditions.append(current_status == status)
    if term:
        conditions.append(or_(
            Ticket.message.icontains(term, autoescape=True),
            Ticket.order_id.icontains(term, autoescape=True),
            Ticket.customer_intent.icontains(term, autoescape=True),
            Ticket.id.in_(select(TicketOrderReference.ticket_id).where(
                TicketOrderReference.order_id.icontains(term, autoescape=True))),
        ))
    with Session(request.app.state.engine) as session:
        def count(*extra_conditions):
            return session.exec(select(func.count(Ticket.id)).outerjoin(TicketWorkflow, TicketWorkflow.ticket_id == Ticket.id).where(*conditions, *extra_conditions)).one()

        counts = TicketCounts(
            total=count(), new=count(current_status == TicketStatus.new),
            high=count(Ticket.priority == Priority.high), urgent=count(Ticket.priority == Priority.urgent),
        )
        tickets = session.exec(select(Ticket).outerjoin(TicketWorkflow, TicketWorkflow.ticket_id == Ticket.id).where(*conditions).order_by(Ticket.created_at.desc(), Ticket.id.desc()).offset(offset).limit(limit)).all()
        return TicketPage(items=[ticket_read(session, ticket) for ticket in tickets], counts=counts, limit=limit, offset=offset)


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket(ticket_id: UUID, request: Request):
    with Session(request.app.state.engine) as session:
        ticket = session.get(Ticket, ticket_id)
        if ticket is None:
            raise HTTPException(status_code=404, detail={"code": "ticket_not_found", "message": "Ticket not found."})
        return ticket_read(session, ticket)
