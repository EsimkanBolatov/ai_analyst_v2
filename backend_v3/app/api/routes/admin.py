from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.moderation_queue import ModerationQueue
from app.models.transaction import UserTransaction
from app.models.user import User
from app.schemas.common import AdminSummary
from app.schemas.user import UserRead

router = APIRouter()


@router.get("/summary", response_model=AdminSummary)
def admin_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Moderator", "RiskManager")),
) -> AdminSummary:
    return AdminSummary(
        users=db.query(User).count(),
        transactions=db.query(UserTransaction).count(),
        moderation_items=db.query(ModerationQueue).count(),
    )


@router.get("/users", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin")),
) -> list[UserRead]:
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [UserRead.model_validate(user) for user in users]
