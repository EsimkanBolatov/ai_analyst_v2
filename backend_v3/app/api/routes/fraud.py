from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.user import User
from app.schemas.fraud import (
    BlacklistBatchCheckRequest,
    BlacklistBatchCheckResponse,
    BlacklistBatchCheckResult,
    BlacklistCheckRequest,
    BlacklistCheckResponse,
    BlacklistEntryRead,
    FraudReportCreate,
    FraudReportResponse,
    ModerationFilterStatus,
    ModerationItemRead,
    ModerationQueueResponse,
    ModerationResolveRequest,
    ModerationResolveResponse,
)
from app.services.fraud_service import (
    categorize_report_job,
    check_blacklist_batch,
    check_blacklist,
    create_report,
    list_moderation_queue,
    list_user_reports,
    moderation_queue_summary,
    resolve_moderation_item,
)

router = APIRouter()


@router.post("/report", response_model=FraudReportResponse, status_code=status.HTTP_201_CREATED)
def submit_fraud_report(
    payload: FraudReportCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FraudReportResponse:
    item, already_blacklisted = create_report(
        db,
        user=current_user,
        data_type=payload.data_type,
        value=payload.value,
        user_comment=payload.user_comment,
    )
    if not already_blacklisted:
        background_tasks.add_task(categorize_report_job, item.id)
    db.refresh(item)
    return FraudReportResponse(
        item=ModerationItemRead.model_validate(item),
        already_blacklisted=already_blacklisted,
    )


@router.get("/reports/mine", response_model=list[ModerationItemRead])
def read_my_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ModerationItemRead]:
    items = list_user_reports(db, current_user.id)
    return [ModerationItemRead.model_validate(item) for item in items]


@router.post("/check", response_model=BlacklistCheckResponse)
def check_fraud_value(
    payload: BlacklistCheckRequest,
    db: Session = Depends(get_db),
) -> BlacklistCheckResponse:
    matched = check_blacklist(db, payload.data_type, payload.value)
    return BlacklistCheckResponse(
        is_blacklisted=matched is not None,
        matched_entry=BlacklistEntryRead.model_validate(matched) if matched else None,
    )


@router.post("/check-batch", response_model=BlacklistBatchCheckResponse)
def check_fraud_values_batch(
    payload: BlacklistBatchCheckRequest,
    db: Session = Depends(get_db),
) -> BlacklistBatchCheckResponse:
    results = check_blacklist_batch(db, payload.items)
    return BlacklistBatchCheckResponse(
        results=[
            BlacklistBatchCheckResult(
                data_type=item.data_type,
                value=item.value,
                is_blacklisted=matched is not None,
                matched_entry=BlacklistEntryRead.model_validate(matched) if matched else None,
            )
            for item, matched in results
        ]
    )


@router.get("/moderation/queue", response_model=ModerationQueueResponse)
def read_moderation_queue(
    status_filter: ModerationFilterStatus = Query(default="pending", alias="status"),
    data_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Moderator", "RiskManager")),
) -> ModerationQueueResponse:
    items = list_moderation_queue(db, status_filter=status_filter, data_type=data_type)
    summary = moderation_queue_summary(db)
    return ModerationQueueResponse(
        items=[ModerationItemRead.model_validate(item) for item in items],
        **summary,
    )


@router.post("/moderation/resolve/{report_id}", response_model=ModerationResolveResponse)
def resolve_report(
    report_id: int,
    payload: ModerationResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "Moderator", "RiskManager")),
) -> ModerationResolveResponse:
    try:
        item, blacklist_entry = resolve_moderation_item(
            db,
            report_id=report_id,
            moderator=current_user,
            action=payload.action,
            moderator_comment=payload.moderator_comment,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ModerationResolveResponse(
        item=ModerationItemRead.model_validate(item),
        blacklist_entry=BlacklistEntryRead.model_validate(blacklist_entry) if blacklist_entry else None,
    )
