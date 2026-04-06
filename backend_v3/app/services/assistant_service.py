import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from groq import Groq, GroqError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.assistant_message import AssistantMessage
from app.models.user import User
from app.services.budget_service import (
    build_budget_read,
    get_budget,
    get_spent_amount,
    month_start,
    sync_budget_balance,
)
from app.services.transaction_service import create_transaction, list_recent_transactions

SPEND_KEYWORDS = [
    "купил",
    "купила",
    "потратил",
    "потратила",
    "оплатил",
    "оплатила",
    "заказал",
    "заказала",
    "списали",
    "заплатил",
    "заплатила",
    "снял",
    "сняла",
    "взял такси",
]
NON_TRANSACTION_HINTS = ["бюджет", "лимит", "остаток", "сколько", "совет", "план"]
CATEGORY_KEYWORDS = {
    "Кофе": ["кофе", "латте", "капучино"],
    "Транспорт": ["такси", "метро", "автобус", "бензин", "азс"],
    "Продукты": ["продукты", "магазин", "супермаркет", "еда"],
    "Подписки": ["подписка", "netflix", "spotify", "youtube"],
    "Развлечения": ["кино", "бар", "кафе", "ресторан", "игра"],
    "Дом": ["аренда", "квартира", "коммун", "ремонт"],
    "Здоровье": ["аптека", "лекар", "врач", "медицина"],
}


@dataclass
class AssistantDecision:
    reply: str
    should_record_transaction: bool
    transaction: dict[str, Any] | None


def _get_groq_client() -> Groq | None:
    if not settings.groq_api_key:
        return None
    return Groq(api_key=settings.groq_api_key)


def _serialize_transactions_for_prompt(user_id: int, db: Session) -> str:
    transactions = list_recent_transactions(db, user_id, limit=6)
    if not transactions:
        return "No recent transactions."
    return "\n".join(
        f"- {tx.occurred_at.isoformat()} | {float(tx.amount):.2f} | {tx.category or 'Без категории'} | {tx.description or 'Без описания'}"
        for tx in transactions
    )


def _serialize_history(messages: list[AssistantMessage]) -> str:
    if not messages:
        return "Conversation is empty."
    return "\n".join(f"{message.role}: {message.content}" for message in messages[-8:])


def _extract_amount(text: str) -> float | None:
    match = re.search(r"(\d[\d\s.,]{0,20})", text)
    if not match:
        return None
    raw = match.group(1).replace(" ", "").replace("\xa0", "").replace(",", ".")
    if raw.count(".") > 1:
        head, tail = raw[:-3], raw[-3:]
        raw = head.replace(".", "") + tail
    try:
        return round(abs(float(raw)), 2)
    except ValueError:
        return None


def _detect_category(text: str) -> str:
    lowered = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return "Прочее"


def _build_fallback_reply(message: str, balance: float | None, limit: float | None) -> AssistantDecision:
    lowered = message.lower()
    amount = _extract_amount(message)
    should_record = bool(amount and any(keyword in lowered for keyword in SPEND_KEYWORDS))
    if any(keyword in lowered for keyword in NON_TRANSACTION_HINTS):
        should_record = False

    if should_record and amount is not None:
        category = _detect_category(message)
        if balance is not None and limit is not None and limit > 0:
            ratio = balance / limit
            if ratio < 0.2:
                tone = "Остаток бюджета уже критически низкий. Трату фиксирую, но дальше нужны жесткие ограничения."
            elif ratio < 0.4:
                tone = "Трата записана. Пора сокращать необязательные расходы."
            else:
                tone = "Трату записал. Пока вы держитесь в рамках лимита, но расслабляться рано."
        else:
            tone = "Трату записал. Теперь задайте месячный лимит, иначе контроля бюджета не будет."

        return AssistantDecision(
            reply=f"{tone} Сумма: {amount:.2f}. Категория: {category}.",
            should_record_transaction=True,
            transaction={
                "amount": amount,
                "category": category,
                "description": message.strip(),
                "occurred_at": datetime.now(UTC).isoformat(),
            },
        )

    if balance is not None and limit is not None:
        return AssistantDecision(
            reply=(
                f"По текущему месяцу остаток {balance:.2f} из лимита {limit:.2f}. "
                "Если нужен совет по экономии, задайте конкретный вопрос."
            ),
            should_record_transaction=False,
            transaction=None,
        )

    return AssistantDecision(
        reply=(
            "Лимит бюджета еще не задан. Сначала установите месячный бюджет, "
            "затем фиксируйте траты или импортируйте выписку."
        ),
        should_record_transaction=False,
        transaction=None,
    )


def _run_groq_assistant(
    *,
    user: User,
    db: Session,
    user_message: str,
    current_budget_limit: float | None,
    current_budget_balance: float | None,
    current_month_spent: float,
    recent_messages: list[AssistantMessage],
) -> AssistantDecision:
    client = _get_groq_client()
    if client is None:
        return _build_fallback_reply(user_message, current_budget_balance, current_budget_limit)

    prompt = f"""
Ты строгий личный финансовый ассистент. Отвечай по-русски, коротко, по делу, с дисциплиной, но без оскорблений.

ПРОФИЛЬ:
- Пользователь: {user.email}
- Месячный лимит: {current_budget_limit if current_budget_limit is not None else "не задан"}
- Текущий остаток: {current_budget_balance if current_budget_balance is not None else "не определен"}
- Уже потрачено в текущем месяце: {current_month_spent:.2f}

ПОСЛЕДНИЕ ТРАТЫ:
{_serialize_transactions_for_prompt(user.id, db)}

ИСТОРИЯ ДИАЛОГА:
{_serialize_history(recent_messages)}

СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ:
{user_message}

ЗАДАЧА:
1. Ответь как строгий личный финансовый ассистент.
2. Определи, описывает ли пользователь новую трату.
3. Если да, извлеки одну транзакцию с amount, category, description, occurred_at в формате ISO 8601. Если дата не указана, поставь null.
4. Если уверенности нет, верни should_record_transaction=false.

ВЕРНИ СТРОГО JSON:
{{
  "reply": "string",
  "should_record_transaction": true,
  "transaction": {{
    "amount": 0,
    "category": "string",
    "description": "string",
    "occurred_at": "2026-04-06T10:00:00Z"
  }}
}}
Если транзакции нет, transaction должен быть null.
"""

    try:
        completion = client.chat.completions.create(
            model=settings.groq_model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        payload = json.loads(completion.choices[0].message.content)
        return AssistantDecision(
            reply=str(payload.get("reply") or "").strip(),
            should_record_transaction=bool(payload.get("should_record_transaction")),
            transaction=payload.get("transaction"),
        )
    except (GroqError, ValueError, KeyError, json.JSONDecodeError):
        return _build_fallback_reply(user_message, current_budget_balance, current_budget_limit)


def get_assistant_overview(db: Session, user: User) -> dict[str, Any]:
    current_month = month_start()
    budget = get_budget(db, user.id, current_month)
    if budget:
        sync_budget_balance(db, budget)
        db.commit()
        db.refresh(budget)

    recent_transactions = list_recent_transactions(db, user.id)
    messages = (
        db.query(AssistantMessage)
        .filter(AssistantMessage.user_id == user.id)
        .order_by(AssistantMessage.created_at.asc(), AssistantMessage.id.asc())
        .limit(30)
        .all()
    )

    return {
        "budget": build_budget_read(db, budget),
        "current_month_spent": get_spent_amount(db, user.id, current_month),
        "recent_transactions": recent_transactions,
        "messages": messages,
    }


def handle_assistant_message(db: Session, user: User, message: str) -> dict[str, Any]:
    current_month = month_start()
    budget = get_budget(db, user.id, current_month)
    current_budget_limit = float(budget.monthly_limit) if budget else None
    current_budget_balance = float(budget.current_balance) if budget else None
    recent_messages = (
        db.query(AssistantMessage)
        .filter(AssistantMessage.user_id == user.id)
        .order_by(AssistantMessage.created_at.asc(), AssistantMessage.id.asc())
        .all()
    )
    current_month_spent = get_spent_amount(db, user.id, current_month)

    decision = _run_groq_assistant(
        user=user,
        db=db,
        user_message=message,
        current_budget_limit=current_budget_limit,
        current_budget_balance=current_budget_balance,
        current_month_spent=current_month_spent,
        recent_messages=recent_messages,
    )

    user_entry = AssistantMessage(user_id=user.id, role="user", content=message.strip())
    db.add(user_entry)
    db.flush()

    captured_transaction = None
    if decision.should_record_transaction and decision.transaction:
        raw_transaction = decision.transaction
        amount = raw_transaction.get("amount")
        if amount is not None:
            occurred_at = raw_transaction.get("occurred_at")
            parsed_occurred_at = datetime.now(UTC)
            if occurred_at:
                try:
                    parsed_occurred_at = datetime.fromisoformat(str(occurred_at).replace("Z", "+00:00"))
                except ValueError:
                    parsed_occurred_at = datetime.now(UTC)

            captured_transaction = create_transaction(
                db,
                user_id=user.id,
                occurred_at=parsed_occurred_at,
                amount=float(amount),
                category=str(raw_transaction.get("category") or _detect_category(message)),
                description=str(raw_transaction.get("description") or message.strip()),
                source_filename=None,
            )

    assistant_text = decision.reply or "Не удалось сформировать ответ. Повторите запрос точнее."
    assistant_entry = AssistantMessage(user_id=user.id, role="assistant", content=assistant_text)
    db.add(assistant_entry)

    budget = get_budget(db, user.id, current_month)
    if budget:
        sync_budget_balance(db, budget)

    db.commit()
    db.refresh(assistant_entry)
    if captured_transaction:
        db.refresh(captured_transaction)
    if budget:
        db.refresh(budget)

    return {
        "assistant_message": assistant_entry,
        "captured_transaction": captured_transaction,
        "budget": build_budget_read(db, budget),
        "current_month_spent": get_spent_amount(db, user.id, current_month),
        "recent_transactions": list_recent_transactions(db, user.id),
    }
