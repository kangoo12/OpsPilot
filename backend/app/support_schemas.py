from datetime import date, datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.consistency import ConsistencyCheck


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    product: str
    order_date: date
    delivery_status: Literal["processing", "in_transit", "delayed", "delivered", "cancelled", "returned"]
    estimated_delivery_date: date | None
    return_eligibility: Literal["review_available", "not_eligible", "not_started", "unknown"]
    warranty_eligibility: Literal["review_available", "not_eligible", "unknown"]
    snapshot_date: date
    is_synthetic: Literal[True]


class OrderLookup(BaseModel):
    reference_order_id: str | None
    lookup_status: Literal["found", "unknown", "not_provided"]
    order: OrderRead | None


class TicketOrderLookup(OrderLookup):
    extracted_order_id: str | None
    source: Literal["extracted", "manual"]
    consistency: ConsistencyCheck = Field(default_factory=ConsistencyCheck)


class OrderReferenceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    order_id: str | None = Field(max_length=65)

    @field_validator("order_id")
    @classmethod
    def normalize_reference(cls, value: str | None) -> str | None:
        if value is None:
            return None
        import re
        value = value.strip().removeprefix("#").upper()
        if not re.fullmatch(r"[\w][\w/-]{0,63}", value):
            raise ValueError("Use an order ID of 1–64 letters, numbers, hyphens or slashes")
        return value


class DraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    ticket_id: UUID
    reply_text: str
    language: Literal["en", "el"]
    status: Literal["pending_review"]
    model: Literal["qwen3.5:9b"]
    order_context: TicketOrderLookup
    policy_version: str
    created_at: datetime
    snapshot_consistency: ConsistencyCheck = Field(default_factory=ConsistencyCheck)

    @field_validator("created_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class DraftPage(BaseModel):
    items: list[DraftRead]
    total: int
