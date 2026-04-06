from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


FraudDataType = Literal["phone", "url", "email", "text"]
ModerationAction = Literal["approved", "rejected"]
ModerationFilterStatus = Literal["all", "pending", "approved", "rejected"]


class FraudQueueUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str


class FraudReportCreate(BaseModel):
    data_type: FraudDataType
    value: str = Field(min_length=3, max_length=512)
    user_comment: str | None = Field(default=None, max_length=2000)


class ModerationResolveRequest(BaseModel):
    action: ModerationAction
    moderator_comment: str | None = Field(default=None, max_length=2000)


class BlacklistEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    data_type: str
    value: str
    category: str | None = None
    source_report_id: int | None = None
    approved_by_user_id: int | None = None
    created_at: datetime


class ModerationItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    data_type: str
    value: str
    user_comment: str | None = None
    ai_category: str | None = None
    ai_confidence: float | None = None
    ai_summary: str | None = None
    status: str
    moderator_comment: str | None = None
    resolved_by_user_id: int | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    reporter: FraudQueueUserRead
    resolver: FraudQueueUserRead | None = None
    blacklist_entry: BlacklistEntryRead | None = None


class FraudReportResponse(BaseModel):
    item: ModerationItemRead
    already_blacklisted: bool


class ModerationQueueResponse(BaseModel):
    items: list[ModerationItemRead]
    total_count: int
    pending_count: int
    approved_count: int
    rejected_count: int
    blacklist_count: int


class ModerationResolveResponse(BaseModel):
    item: ModerationItemRead
    blacklist_entry: BlacklistEntryRead | None = None


class BlacklistCheckRequest(BaseModel):
    data_type: FraudDataType
    value: str = Field(min_length=3, max_length=512)


class BlacklistCheckResponse(BaseModel):
    is_blacklisted: bool
    matched_entry: BlacklistEntryRead | None = None
