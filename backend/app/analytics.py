"""Read-only metrics for the configured database, never other database files."""
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Query, Request
from sqlalchemy import case, func
from sqlmodel import Session, select

from app.consistency import check_consistency
from app.models import Order, Ticket, TicketOrderReference
from app.schemas import Category, Priority, TicketStatus
from app.workflow_models import AuditEvent, DraftReview, TicketWorkflow

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("")
def analytics(request: Request, days: Annotated[int, Query(ge=1, le=366)] = 30):
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)
    end = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    status = func.coalesce(TicketWorkflow.status, Ticket.status)
    with Session(request.app.state.engine) as session:
        def breakdown(column, values, workflow=False):
            query = select(column, func.count(Ticket.id)).select_from(Ticket)
            if workflow:
                query = query.outerjoin(TicketWorkflow, TicketWorkflow.ticket_id == Ticket.id)
            result = dict(session.exec(query.group_by(column)).all())
            return {str(value): result.get(value, 0) for value in values}

        categories = breakdown(Ticket.category, Category)
        priorities = breakdown(Ticket.priority, Priority)
        statuses = breakdown(status, TicketStatus, True)
        decisions = dict(session.exec(select(DraftReview.status, func.count(DraftReview.draft_id)).group_by(DraftReview.status)).all())
        volume = dict(session.exec(select(func.date(Ticket.created_at), func.count(Ticket.id)).where(
            Ticket.created_at >= start, Ticket.created_at < end,
        ).group_by(func.date(Ticket.created_at))).all())
        # Human review is derived from the same current-reference checks as ticket reads.
        # Stream only message/reference/order columns; do not load drafts or all Ticket models.
        reference = case((TicketOrderReference.ticket_id.is_not(None), TicketOrderReference.order_id), else_=Ticket.order_id)
        query = select(Ticket.message, reference, Order).select_from(Ticket).outerjoin(
            TicketOrderReference, TicketOrderReference.ticket_id == Ticket.id,
        ).outerjoin(Order, Order.id == func.upper(func.ltrim(func.trim(reference), '#')))
        review_count = sum(check_consistency(message, order, ref).requires_human_review
                           for message, ref, order in session.exec(query.execution_options(yield_per=100)))
        resolutions = select(AuditEvent.ticket_id.label('ticket_id'), func.max(AuditEvent.created_at).label('resolved_at')).where(
            AuditEvent.event_type == 'ticket_status_changed', AuditEvent.data['new'].as_string() == 'resolved',
        ).group_by(AuditEvent.ticket_id).subquery()
        elapsed = (func.julianday(resolutions.c.resolved_at) - func.julianday(Ticket.created_at)) * 86400
        measured, average = session.exec(select(func.count(Ticket.id), func.avg(elapsed)).select_from(Ticket).outerjoin(
            TicketWorkflow, TicketWorkflow.ticket_id == Ticket.id,
        ).join(resolutions, resolutions.c.ticket_id == Ticket.id).where(
            status == 'resolved', elapsed >= 0, resolutions.c.resolved_at <= now,
        )).one()
        return {
            'generated_at': now.isoformat(), 'total_tickets': sum(categories.values()),
            'by_category': categories, 'by_priority': priorities, 'by_status': statuses,
            'human_review_tickets': review_count,
            'draft_decisions': {'approved': decisions.get('approved', 0), 'rejected': decisions.get('rejected', 0)},
            'volume': [{'date': (start + timedelta(days=index)).date().isoformat(),
                        'count': volume.get((start + timedelta(days=index)).date().isoformat(), 0)} for index in range(days)],
            'resolution_time': {'average_seconds': round(average, 2) if average is not None else None,
                                'measured_tickets': measured, 'unavailable_tickets': statuses['resolved'] - measured},
        }
