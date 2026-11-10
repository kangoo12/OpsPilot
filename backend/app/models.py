from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Enum
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
