from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.assistant_message import AssistantMessage
from app.models.blacklist_entry import BlacklistEntry
from app.models.budget import UserBudget
from app.models.moderation_queue import ModerationQueue, ModerationStatus
from app.models.role import Role
from app.models.transaction import UserTransaction
from app.models.user import User

TEST_PASSWORD = "Test12345!"
TEST_USERS = {
    "user@ai-analyst.app": "User",
    "moderator@ai-analyst.app": "Moderator",
    "risk@ai-analyst.app": "RiskManager",
    "admin@ai-analyst.app": "Admin",
}


def _month_start(value: datetime | None = None) -> date:
    value = value or datetime.now(UTC)
    return date(value.year, value.month, 1)


def _get_role(db: Session, role_name: str) -> Role:
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        raise RuntimeError(f"Required role is not initialized: {role_name}")
    return role


def _upsert_test_user(db: Session, email: str, role_name: str) -> User:
    role = _get_role(db, role_name)
    user = db.query(User).filter(User.email == email).first()
    password_hash = get_password_hash(TEST_PASSWORD)
    if not user:
        user = User(email=email, hashed_password=password_hash, role_id=role.id)
        db.add(user)
        db.flush()
        return user

    user.role_id = role.id
    user.hashed_password = password_hash
    db.add(user)
    db.flush()
    return user


def _seed_user_finance(db: Session, user: User) -> None:
    current_month = _month_start()
    budget = (
        db.query(UserBudget)
        .filter(UserBudget.user_id == user.id, UserBudget.month == current_month)
        .first()
    )
    if not budget:
        budget = UserBudget(
            user_id=user.id,
            month=current_month,
            monthly_limit=350000,
            current_balance=350000,
        )
        db.add(budget)
        db.flush()

    if not db.query(UserTransaction).filter(UserTransaction.user_id == user.id).first():
        now = datetime.now(UTC)
        transactions = [
            UserTransaction(
                user_id=user.id,
                occurred_at=now - timedelta(days=1),
                amount=12500,
                category="Продукты",
                description="Супермаркет для недельных покупок",
                source_filename="seed_statement.csv",
            ),
            UserTransaction(
                user_id=user.id,
                occurred_at=now - timedelta(days=2),
                amount=3200,
                category="Транспорт",
                description="Такси до офиса",
                source_filename="seed_statement.csv",
            ),
            UserTransaction(
                user_id=user.id,
                occurred_at=now - timedelta(days=4),
                amount=5900,
                category="Подписки",
                description="Облачный сервис",
                source_filename="seed_statement.csv",
            ),
        ]
        db.add_all(transactions)

    if not db.query(AssistantMessage).filter(AssistantMessage.user_id == user.id).first():
        db.add_all(
            [
                AssistantMessage(
                    user_id=user.id,
                    role="user",
                    content="Поставь месячный лимит и помогай держать расходы под контролем.",
                ),
                AssistantMessage(
                    user_id=user.id,
                    role="assistant",
                    content="Лимит задан. Начинаем с контроля обязательных расходов и регулярных подписок.",
                ),
            ]
        )

    spent = (
        db.query(UserTransaction)
        .filter(
            UserTransaction.user_id == user.id,
            UserTransaction.occurred_at >= datetime.combine(current_month, datetime.min.time(), tzinfo=UTC),
        )
        .all()
    )
    budget.current_balance = float(budget.monthly_limit) - sum(float(item.amount) for item in spent)
    db.add(budget)


def _ensure_report(
    db: Session,
    *,
    reporter: User,
    data_type: str,
    value: str,
    user_comment: str,
    ai_category: str,
    ai_summary: str,
    status: str,
    resolver: User | None = None,
    moderator_comment: str | None = None,
) -> ModerationQueue:
    item = (
        db.query(ModerationQueue)
        .filter(
            ModerationQueue.user_id == reporter.id,
            ModerationQueue.data_type == data_type,
            ModerationQueue.value == value,
        )
        .first()
    )
    if item:
        return item

    item = ModerationQueue(
        user_id=reporter.id,
        data_type=data_type,
        value=value,
        user_comment=user_comment,
        ai_category=ai_category,
        ai_confidence=0.86,
        ai_summary=ai_summary,
        status=status,
        resolved_by_user_id=resolver.id if resolver else None,
        moderator_comment=moderator_comment,
        resolved_at=datetime.now(UTC) if resolver else None,
    )
    db.add(item)
    db.flush()
    return item


def _seed_fraud_data(db: Session, reporter: User, moderator: User) -> None:
    approved = _ensure_report(
        db,
        reporter=reporter,
        data_type="url",
        value="https://secure-bonus-wallet.example/login",
        user_comment="Просили срочно подтвердить карту и код из SMS.",
        ai_category="Фишинг",
        ai_summary="Ссылка содержит типичные фишинговые признаки: secure, bonus, wallet, login.",
        status=ModerationStatus.approved.value,
        resolver=moderator,
        moderator_comment="Seed: подтвержденный фишинговый URL.",
    )
    _ensure_report(
        db,
        reporter=reporter,
        data_type="phone",
        value="+7 777 000 11 22",
        user_comment="Представились службой безопасности и просили перевести деньги.",
        ai_category="Телефонный скам",
        ai_summary="Комментарий указывает на социальную инженерию и попытку финансового давления.",
        status=ModerationStatus.pending.value,
    )
    _ensure_report(
        db,
        reporter=reporter,
        data_type="email",
        value="support-confirm@example-risk.test",
        user_comment="Письмо просит подтвердить пароль от банка.",
        ai_category="Фишинговая почта",
        ai_summary="Письмо похоже на попытку выманить учетные данные.",
        status=ModerationStatus.rejected.value,
        resolver=moderator,
        moderator_comment="Seed: недостаточно данных для финального blacklist.",
    )

    blacklist = (
        db.query(BlacklistEntry)
        .filter(
            BlacklistEntry.data_type == "url",
            BlacklistEntry.value == "secure-bonus-wallet.example/login",
        )
        .first()
    )
    if not blacklist:
        db.add(
            BlacklistEntry(
                data_type="url",
                value="secure-bonus-wallet.example/login",
                category="Фишинг",
                source_report_id=approved.id,
                approved_by_user_id=moderator.id,
            )
        )


def seed_test_data(session_factory: Callable[[], Session]) -> None:
    with session_factory() as db:
        users = {
            email: _upsert_test_user(db, email, role_name)
            for email, role_name in TEST_USERS.items()
        }
        _seed_user_finance(db, users["user@ai-analyst.app"])
        _seed_fraud_data(db, users["user@ai-analyst.app"], users["moderator@ai-analyst.app"])
        db.commit()
