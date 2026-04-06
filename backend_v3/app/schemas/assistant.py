from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class BudgetUpsertRequest(BaseModel):
    monthly_limit: float = Field(ge=0)
    month: date | None = None


class BudgetRead(BaseModel):
    id: int
    month: date
    monthly_limit: float
    current_balance: float
    spent_amount: float


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    occurred_at: datetime
    amount: float
    category: str | None = None
    description: str | None = None
    source_filename: str | None = None
    created_at: datetime


class AssistantMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    created_at: datetime


class AssistantOverview(BaseModel):
    budget: BudgetRead | None = None
    current_month_spent: float
    recent_transactions: list[TransactionRead]
    messages: list[AssistantMessageRead]


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class AssistantChatResponse(BaseModel):
    assistant_message: AssistantMessageRead
    captured_transaction: TransactionRead | None = None
    budget: BudgetRead | None = None
    current_month_spent: float
    recent_transactions: list[TransactionRead]


class TransactionImportResponse(BaseModel):
    stored_filename: str | None = None
    imported_count: int
    skipped_count: int
    warnings: list[str]
    detected_columns: dict[str, str | None]
    budget: BudgetRead | None = None
    current_month_spent: float
    recent_transactions: list[TransactionRead]
