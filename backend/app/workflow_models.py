"""Additive workflow storage. Original tickets and AI draft snapshots stay intact."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Column, JSON, UniqueConstraint
from sqlmodel import Field, SQLModel


def now():
    return datetime.now(timezone.utc)


class SchemaMigration(SQLModel, table=True):
    version: int = Field(primary_key=True)
    name: str
    applied_at: datetime = Field(default_factory=now)


class TicketWorkflow(SQLModel, table=True):
    __table_args__ = (CheckConstraint("status IN ('new','in_progress','waiting_for_customer','resolved')"),)
    ticket_id: UUID = Field(primary_key=True, foreign_key="ticket.id")
    status: str = "new"
    version: int = 1
    updated_at: datetime = Field(default_factory=now)


class DraftReview(SQLModel, table=True):
    __table_args__ = (
        CheckConstraint("status IN ('pending_review','approved','rejected')"),
        CheckConstraint("version >= 1"),
        CheckConstraint("(status = 'approved' AND approved_at IS NOT NULL AND reviewer IS NOT NULL) OR (status != 'approved' AND approved_at IS NULL)"),
        CheckConstraint("(status = 'rejected' AND rejected_at IS NOT NULL AND rejection_reason IS NOT NULL AND reviewer IS NOT NULL) OR (status != 'rejected' AND rejected_at IS NULL)"),
    )
    draft_id: UUID = Field(primary_key=True, foreign_key="replydraft.id")
    content: str
    status: str = "pending_review"
    version: int = 1
    updated_at: datetime = Field(default_factory=now)
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    reviewer: str | None = None
    rejection_reason: str | None = None
    parent_draft_id: UUID | None = Field(default=None, foreign_key="replydraft.id", index=True)
    origin: str = "ai"
    review_context: dict = Field(sa_column=Column(JSON, nullable=False))


class DraftRevision(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("draft_id", "version"),)
    id: int | None = Field(default=None, primary_key=True)
    draft_id: UUID = Field(foreign_key="replydraft.id", index=True)
    version: int
    content: str
    status: str
    actor: str
    action: str
    reason: str | None = None
    created_at: datetime = Field(default_factory=now)
    review_context: dict = Field(sa_column=Column(JSON, nullable=False))


class AuditEvent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    ticket_id: UUID = Field(foreign_key="ticket.id", index=True)
    event_type: str = Field(index=True)
    actor: str
    created_at: datetime = Field(default_factory=now)
    data: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    dedupe_key: str | None = Field(default=None, unique=True)


class DiscrepancyResolution(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    ticket_id: UUID = Field(foreign_key="ticket.id", index=True)
    context_fingerprint: str = Field(index=True)
    reason: str
    actor: str
    created_at: datetime = Field(default_factory=now)
    context: dict = Field(sa_column=Column(JSON, nullable=False))
