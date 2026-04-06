from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.transaction import UserTransaction
from app.schemas.assistant import TransactionRead


def create_transaction(
    db: Session,
    *,
    user_id: int,
    occurred_at: datetime,
    amount: float,
    category: str | None,
    description: str | None,
    source_filename: str | None = None,
) -> UserTransaction:
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=UTC)

    transaction = UserTransaction(
        user_id=user_id,
        occurred_at=occurred_at,
        amount=round(float(amount), 2),
        category=category,
        description=description,
        source_filename=source_filename,
    )
    db.add(transaction)
    db.flush()
    return transaction


def list_recent_transactions(db: Session, user_id: int, limit: int = 8) -> list[UserTransaction]:
    return (
        db.query(UserTransaction)
        .filter(UserTransaction.user_id == user_id)
        .order_by(UserTransaction.occurred_at.desc(), UserTransaction.id.desc())
        .limit(limit)
        .all()
    )


def to_transaction_read(transaction: UserTransaction) -> TransactionRead:
    return TransactionRead.model_validate(transaction)
