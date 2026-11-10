from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.consistency import ConsistencyCheck

MAX_MESSAGE_LENGTH = 5000


class Category(StrEnum):
    delivery = "delivery"
    returns = "returns"
    payments = "payments"
    technical_support = "technical_support"
    other = "other"


class Priority(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class TicketStatus(StrEnum):
    new = "new"


class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)

    @field_validator("message")
    @classmethod
    def require_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Enter a customer message")
        return value  # Preserve the original customer message, including whitespace.


class Classification(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    category: Category
    priority: Priority
    order_id: str | None = Field(description="Exact referenced order ID, or null", max_length=64)
    customer_intent: str = Field(min_length=1, max_length=300)
    reason: str = Field(min_length=1, max_length=1000)


class TicketRead(Classification):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=False)
    id: UUID
    message: str
    status: TicketStatus
    created_at: datetime
    requires_human_review: bool = False
    consistency: ConsistencyCheck = Field(default_factory=ConsistencyCheck)

    @field_validator("created_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        # SQLite stores datetime without timezone information; all writes use UTC.
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class TicketCounts(BaseModel):
    total: int
    new: int
    high: int
    urgent: int


class TicketPage(BaseModel):
    items: list[TicketRead]
    counts: TicketCounts
    limit: int
    offset: int
