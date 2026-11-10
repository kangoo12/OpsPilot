from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Column, Enum, JSON
from sqlmodel import Field, SQLModel

from app.schemas import MAX_MESSAGE_LENGTH, Category, Priority, TicketStatus


class Ticket(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    message: str = Field(max_length=MAX_MESSAGE_LENGTH)
    category: Category = Field(sa_type=Enum(Category, native_enum=False, create_constraint=True), index=True)
    priority: Priority = Field(sa_type=Enum(Priority, native_enum=False, create_constraint=True), index=True)
    order_id: str | None = Field(default=None, max_length=64)
    customer_intent: str = Field(max_length=300)
    reason: str = Field(max_length=1000)
    status: TicketStatus = Field(default=TicketStatus.new, sa_type=Enum(TicketStatus, native_enum=False, create_constraint=True), index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)


class Order(SQLModel, table=True):
    id: str = Field(primary_key=True, max_length=64)
    product: str = Field(max_length=150)
    order_date: date
    delivery_status: str = Field(max_length=30)
    estimated_delivery_date: date | None = None
    return_eligibility: str = Field(max_length=30)
    warranty_eligibility: str = Field(max_length=30)
    snapshot_date: date
    is_synthetic: bool = True


class TicketOrderReference(SQLModel, table=True):
    ticket_id: UUID = Field(primary_key=True, foreign_key="ticket.id")
    order_id: str | None = Field(default=None, max_length=64)


class ReplyDraft(SQLModel, table=True):
    __table_args__ = (CheckConstraint("status = 'pending_review'"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    ticket_id: UUID = Field(foreign_key="ticket.id", index=True)
    reply_text: str = Field(max_length=4000)
    language: str = Field(max_length=2)
    status: str = Field(default="pending_review", max_length=30)
    model: str = "qwen3.5:9b"
    order_context: dict = Field(sa_column=Column(JSON, nullable=False))
    policy_version: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
