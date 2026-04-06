from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.budget import UserBudget
from app.models.transaction import UserTransaction
from app.schemas.assistant import BudgetRead


def month_start(value: date | datetime | None = None) -> date:
    if value is None:
        value = datetime.now(UTC).date()
    if isinstance(value, datetime):
        value = value.date()
    return date(value.year, value.month, 1)


def next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def get_budget(db: Session, user_id: int, month: date) -> UserBudget | None:
    return (
        db.query(UserBudget)
        .filter(UserBudget.user_id == user_id, UserBudget.month == month)
        .first()
    )


def get_spent_amount(db: Session, user_id: int, month: date) -> float:
    month_end = next_month(month)
    total = (
        db.query(func.coalesce(func.sum(UserTransaction.amount), 0))
        .filter(
            UserTransaction.user_id == user_id,
            UserTransaction.occurred_at >= datetime.combine(month, datetime.min.time(), tzinfo=UTC),
            UserTransaction.occurred_at < datetime.combine(month_end, datetime.min.time(), tzinfo=UTC),
        )
        .scalar()
    )
    if isinstance(total, Decimal):
        return float(total)
    return float(total or 0)


def sync_budget_balance(db: Session, budget: UserBudget) -> UserBudget:
    spent_amount = get_spent_amount(db, budget.user_id, budget.month)
    budget.current_balance = float(budget.monthly_limit) - spent_amount
    db.add(budget)
    return budget


def upsert_budget(db: Session, user_id: int, month: date, monthly_limit: float) -> UserBudget:
    budget = get_budget(db, user_id, month)
    if not budget:
        budget = UserBudget(
            user_id=user_id,
            month=month,
            monthly_limit=monthly_limit,
            current_balance=monthly_limit,
        )
        db.add(budget)
        db.flush()

    budget.monthly_limit = monthly_limit
    sync_budget_balance(db, budget)
    db.commit()
    db.refresh(budget)
    return budget


def build_budget_read(db: Session, budget: UserBudget | None) -> BudgetRead | None:
    if not budget:
        return None
    spent_amount = get_spent_amount(db, budget.user_id, budget.month)
    return BudgetRead(
        id=budget.id,
        month=budget.month,
        monthly_limit=float(budget.monthly_limit),
        current_balance=float(budget.current_balance),
        spent_amount=spent_amount,
    )
