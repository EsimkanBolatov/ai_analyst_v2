from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantMessageRead,
    AssistantOverview,
    BudgetRead,
    BudgetUpsertRequest,
    TransactionImportResponse,
    TransactionRead,
)
from app.services.assistant_service import get_assistant_overview, handle_assistant_message
from app.services.budget_service import build_budget_read, month_start, upsert_budget
from app.services.transaction_import_service import import_transactions_from_statement

router = APIRouter()


@router.get("/overview", response_model=AssistantOverview)
def read_assistant_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssistantOverview:
    payload = get_assistant_overview(db, current_user)
    return AssistantOverview(
        budget=payload["budget"],
        current_month_spent=payload["current_month_spent"],
        recent_transactions=[
            TransactionRead.model_validate(transaction) for transaction in payload["recent_transactions"]
        ],
        messages=[AssistantMessageRead.model_validate(message) for message in payload["messages"]],
    )


@router.put("/budget", response_model=BudgetRead)
def save_budget(
    payload: BudgetUpsertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BudgetRead:
    budget = upsert_budget(
        db,
        user_id=current_user.id,
        month=month_start(payload.month),
        monthly_limit=payload.monthly_limit,
    )
    return build_budget_read(db, budget)


@router.post("/import-transactions", response_model=TransactionImportResponse)
def import_transactions(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionImportResponse:
    result = import_transactions_from_statement(db, user=current_user, file=file)
    overview = get_assistant_overview(db, current_user)
    return TransactionImportResponse(
        stored_filename=result.stored_filename,
        imported_count=result.imported_count,
        skipped_count=result.skipped_count,
        warnings=result.warnings,
        detected_columns=result.detected_columns,
        budget=overview["budget"],
        current_month_spent=overview["current_month_spent"],
        recent_transactions=[
            TransactionRead.model_validate(transaction) for transaction in overview["recent_transactions"]
        ],
    )


@router.post("/chat", response_model=AssistantChatResponse)
def chat_with_assistant(
    payload: AssistantChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssistantChatResponse:
    result = handle_assistant_message(db, current_user, payload.message)
    return AssistantChatResponse(
        assistant_message=AssistantMessageRead.model_validate(result["assistant_message"]),
        captured_transaction=(
            TransactionRead.model_validate(result["captured_transaction"])
            if result["captured_transaction"]
            else None
        ),
        budget=result["budget"],
        current_month_spent=result["current_month_spent"],
        recent_transactions=[
            TransactionRead.model_validate(transaction) for transaction in result["recent_transactions"]
        ],
    )
