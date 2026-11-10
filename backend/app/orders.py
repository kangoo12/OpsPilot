"""Fictional demo orders only. No customer identities, payments or external lookups."""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.dialects.sqlite import insert
from sqlmodel import Session, select

from app.models import Order, Ticket, TicketOrderReference
from app.consistency import check_consistency
from app.schemas import TicketRead
from app.support_schemas import OrderLookup, OrderRead, OrderReferenceUpdate, TicketOrderLookup

# Fixed snapshot: stable fixtures, never represented as live carrier data.
SNAPSHOT_DATE = date(2026, 11, 10)
SEED_ORDERS = [
    # Reserved for the original delivered, defective-smartphone scenario.
    ("7821", "Aster Nova smartphone", "2026-11-07", "delivered", None, "review_available", "review_available"),
    ("DEMO-LAMP-9001", "LumaLite desk lamp", "2026-11-06", "in_transit", "2026-11-14", "not_started", "review_available"),
    ("GR-1042", "Aster wireless headphones", "2026-11-01", "delayed", None, "not_started", "review_available"),
    ("7822", "Mira ceramic mug set", "2026-11-02", "delivered", None, "review_available", "review_available"),
    ("7823", "Cedar laptop stand", "2026-11-09", "processing", "2026-11-17", "not_started", "review_available"),
    ("7824", "Solstice cotton throw", "2026-10-01", "delivered", None, "not_eligible", "unknown"),
    ("7825", "Orbit mechanical keyboard", "2026-11-03", "in_transit", "2026-11-12", "not_started", "review_available"),
    ("7826", "Pebble notebook pack", "2026-10-28", "returned", None, "not_eligible", "not_eligible"),
    ("7827", "Willow canvas backpack", "2026-11-05", "cancelled", None, "not_eligible", "not_eligible"),
    ("7828", "Breeze compact fan", "2026-11-07", "processing", None, "not_started", "review_available"),
    ("7829", "Harbor insulated bottle", "2026-11-04", "delivered", None, "review_available", "review_available"),
    ("GR-1043", "Aster portable speaker", "2026-11-08", "in_transit", "2026-11-15", "not_started", "review_available"),
    ("GR-1044", "Nefeli reading light", "2026-10-25", "delivered", None, "review_available", "review_available"),
    ("GR-1045", "Kora yoga mat", "2026-11-02", "delayed", "2026-11-16", "not_started", "review_available"),
    ("GR-1046", "Helio USB hub", "2026-11-10", "processing", None, "not_started", "review_available"),
    ("GR-1047", "Thyme kitchen scale", "2026-09-12", "delivered", None, "not_eligible", "review_available"),
    ("GR-1048", "Mira storage jars", "2026-10-29", "returned", None, "not_eligible", "not_eligible"),
    ("GR-1049", "Cedar monitor riser", "2026-11-04", "cancelled", None, "not_eligible", "not_eligible"),
    ("GR-1050", "Orbit wireless mouse", "2026-11-06", "in_transit", "2026-11-13", "unknown", "unknown"),
]


def seed_orders(engine) -> None:
    with Session(engine) as session:
        for order_id, product, ordered, status, eta, returns, warranty in SEED_ORDERS:
            # Safe across restarts and simultaneous startup; never overwrite records.
            session.execute(insert(Order).values(
                id=order_id, product=product, order_date=date.fromisoformat(ordered),
                delivery_status=status, estimated_delivery_date=date.fromisoformat(eta) if eta else None,
                return_eligibility=returns, warranty_eligibility=warranty,
                snapshot_date=SNAPSHOT_DATE, is_synthetic=True,
            ).on_conflict_do_nothing(index_elements=["id"]))
        session.commit()


def require_ticket(session: Session, ticket_id: UUID) -> Ticket:
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(404, detail={"code": "ticket_not_found", "message": "Ticket not found."})
    return ticket


def lookup_order(session: Session, reference: str | None) -> OrderLookup:
    order = session.get(Order, reference.strip().removeprefix("#").upper()) if reference else None
    return OrderLookup(
        reference_order_id=reference,
        lookup_status="found" if order else "unknown" if reference else "not_provided",
        order=OrderRead.model_validate(order) if order else None,
    )


def ticket_order_context(session: Session, ticket: Ticket) -> TicketOrderLookup:
    manual = session.get(TicketOrderReference, ticket.id)
    reference = manual.order_id if manual else ticket.order_id
    lookup = lookup_order(session, reference)
    return TicketOrderLookup(
        **lookup.model_dump(), extracted_order_id=ticket.order_id,
        source="manual" if manual else "extracted",
        consistency=check_consistency(ticket.message, lookup.order, reference),
    )


def ticket_read(session: Session, ticket: Ticket) -> TicketRead:
    # Derived on read; never rewrites the ticket, its status or historical text.
    context = ticket_order_context(session, ticket)
    result = TicketRead.model_validate(ticket)
    return result.model_copy(update={"requires_human_review": context.consistency.requires_human_review,
                                     "consistency": context.consistency})


router = APIRouter(tags=["orders"])


@router.get("/api/orders", response_model=list[OrderRead])
def list_orders(request: Request):
    with Session(request.app.state.engine) as session:
        return [OrderRead.model_validate(order) for order in session.exec(select(Order).order_by(Order.id)).all()]


@router.get("/api/orders/{order_id}", response_model=OrderLookup)
def get_order(order_id: str, request: Request):
    try:
        reference = OrderReferenceUpdate(order_id=order_id).order_id
    except ValueError as exc:
        raise HTTPException(422, detail={"code": "invalid_order_id", "message": "Enter a valid order ID."}) from exc
    with Session(request.app.state.engine) as session:
        return lookup_order(session, reference)


@router.get("/api/tickets/{ticket_id}/order", response_model=TicketOrderLookup)
def get_ticket_order(ticket_id: UUID, request: Request):
    with Session(request.app.state.engine) as session:
        return ticket_order_context(session, require_ticket(session, ticket_id))


@router.put("/api/tickets/{ticket_id}/order", response_model=TicketOrderLookup)
def correct_ticket_order(ticket_id: UUID, body: OrderReferenceUpdate, request: Request):
    with Session(request.app.state.engine) as session:
        ticket = require_ticket(session, ticket_id)
        session.execute(insert(TicketOrderReference).values(ticket_id=ticket_id, order_id=body.order_id)
                        .on_conflict_do_update(index_elements=["ticket_id"], set_={"order_id": body.order_id}))
        session.commit()
        return ticket_order_context(session, ticket)
