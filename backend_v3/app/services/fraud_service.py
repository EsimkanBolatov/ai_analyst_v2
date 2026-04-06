import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse

from groq import Groq, GroqError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.blacklist_entry import BlacklistEntry
from app.models.moderation_queue import ModerationQueue, ModerationStatus
from app.models.user import User
from app.schemas.fraud import BlacklistBatchCheckItem, ModerationAction, ModerationFilterStatus


@dataclass
class FraudClassification:
    category: str
    confidence: float
    summary: str


PHONE_PATTERN = re.compile(r"\D+")
ALREADY_BLACKLISTED_SUMMARY = "Совпадение с уже утвержденным blacklist."
URL_SCAM_KEYWORDS = [
    "secure",
    "verify",
    "bank",
    "bonus",
    "wallet",
    "cashback",
    "gift",
    "login",
    "support",
]
TEXT_SCAM_KEYWORDS = [
    "код",
    "пароль",
    "переведите",
    "срочно",
    "безопасн",
    "служба безопасности",
    "подарок",
    "выигрыш",
    "подтвердите",
]


def normalize_value(data_type: str, value: str) -> str:
    cleaned = value.strip()
    if data_type == "phone":
        return PHONE_PATTERN.sub("", cleaned)
    if data_type == "email":
        return cleaned.lower()
    if data_type == "url":
        parsed = urlparse(cleaned if "://" in cleaned else f"https://{cleaned}")
        hostname = (parsed.netloc or parsed.path).lower()
        path = parsed.path if parsed.netloc else ""
        return f"{hostname}{path}".rstrip("/")
    return cleaned.lower()


def _fallback_classification(data_type: str, value: str, comment: str | None) -> FraudClassification:
    normalized = normalize_value(data_type, value)
    source_text = f"{value} {comment or ''}".lower()

    if data_type == "url":
        hits = sum(1 for keyword in URL_SCAM_KEYWORDS if keyword in normalized)
        if hits >= 2:
            return FraudClassification(
                category="Фишинг",
                confidence=0.82,
                summary="Ссылка содержит несколько типичных фишинговых паттернов и требует ручной проверки.",
            )
        return FraudClassification(
            category="Подозрительная ссылка",
            confidence=0.58,
            summary="Ссылка выглядит нетипично, но без подтверждения модератора автоматически блокировать ее нельзя.",
        )

    if data_type == "phone":
        if any(keyword in source_text for keyword in ["банк", "код", "служба безопасности", "перевод"]):
            return FraudClassification(
                category="Телефонный скам",
                confidence=0.78,
                summary="Комментарий указывает на социальную инженерию и попытку выманить код или деньги.",
            )
        return FraudClassification(
            category="Телефонный спам",
            confidence=0.55,
            summary="Номер требует проверки модератором, но явных признаков тяжелого скама пока недостаточно.",
        )

    if data_type == "email":
        if any(keyword in source_text for keyword in ["пароль", "вход", "банк", "подтвердите"]):
            return FraudClassification(
                category="Фишинговая почта",
                confidence=0.77,
                summary="Сообщение похоже на попытку выманить логин, пароль или платежные данные.",
            )
        return FraudClassification(
            category="Подозрительная почта",
            confidence=0.56,
            summary="Адрес или комментарий выглядят сомнительно, но нужен ручной разбор модератора.",
        )

    if any(keyword in source_text for keyword in TEXT_SCAM_KEYWORDS):
        return FraudClassification(
            category="Социальная инженерия",
            confidence=0.74,
            summary="Текст содержит типичные триггеры давления и выманивания кодов или переводов.",
        )
    return FraudClassification(
        category="Недостаточно данных",
        confidence=0.4,
        summary="Автоматике не хватило сигнала. Решение должен принять модератор.",
    )


def _get_groq_client() -> Groq | None:
    if not settings.groq_api_key:
        return None
    return Groq(api_key=settings.groq_api_key)


def classify_report(data_type: str, value: str, comment: str | None) -> FraudClassification:
    client = _get_groq_client()
    if client is None:
        return _fallback_classification(data_type, value, comment)

    prompt = f"""
Ты аналитик antifraud. Твоя задача: предварительно классифицировать пользовательскую жалобу.

Тип данных: {data_type}
Значение: {value}
Комментарий пользователя: {comment or "нет"}

Категории на выбор:
- Фишинг
- Телефонный спам
- Телефонный скам
- Фишинговая почта
- Социальная инженерия
- Подозрительная ссылка
- Подозрительная почта
- Недостаточно данных

Верни строго JSON:
{{
  "category": "string",
  "confidence": 0.0,
  "summary": "краткое объяснение для модератора"
}}
"""
    try:
        completion = client.chat.completions.create(
            model=settings.groq_model,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        payload = json.loads(completion.choices[0].message.content)
        return FraudClassification(
            category=str(payload.get("category") or "Недостаточно данных").strip(),
            confidence=max(0.0, min(1.0, float(payload.get("confidence") or 0.4))),
            summary=str(payload.get("summary") or "AI-категоризация не дала уверенного вывода.").strip(),
        )
    except (GroqError, ValueError, TypeError, json.JSONDecodeError):
        return _fallback_classification(data_type, value, comment)


def _already_blacklisted(db: Session, data_type: str, value: str) -> BlacklistEntry | None:
    normalized = normalize_value(data_type, value)
    return (
        db.query(BlacklistEntry)
        .filter(BlacklistEntry.data_type == data_type, BlacklistEntry.value == normalized)
        .first()
    )


def create_report(db: Session, user: User, data_type: str, value: str, user_comment: str | None) -> tuple[ModerationQueue, bool]:
    existing_blacklist = _already_blacklisted(db, data_type, value)
    item = ModerationQueue(
        user_id=user.id,
        data_type=data_type,
        value=value.strip(),
        user_comment=user_comment.strip() if user_comment else None,
        ai_category=existing_blacklist.category if existing_blacklist else None,
        ai_confidence=1.0 if existing_blacklist else None,
        ai_summary=ALREADY_BLACKLISTED_SUMMARY if existing_blacklist else None,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item, existing_blacklist is not None


def categorize_report_job(report_id: int) -> None:
    with SessionLocal() as db:
        item = db.query(ModerationQueue).filter(ModerationQueue.id == report_id).first()
        if not item or item.ai_summary == ALREADY_BLACKLISTED_SUMMARY:
            return
        classification = classify_report(item.data_type, item.value, item.user_comment)
        item.ai_category = classification.category
        item.ai_confidence = classification.confidence
        item.ai_summary = classification.summary
        db.add(item)
        db.commit()


def list_user_reports(db: Session, user_id: int) -> list[ModerationQueue]:
    return (
        db.query(ModerationQueue)
        .filter(ModerationQueue.user_id == user_id)
        .order_by(ModerationQueue.created_at.desc(), ModerationQueue.id.desc())
        .limit(20)
        .all()
    )


def moderation_queue_summary(db: Session) -> dict[str, int]:
    return {
        "total_count": db.query(ModerationQueue).count(),
        "pending_count": db.query(ModerationQueue).filter(ModerationQueue.status == ModerationStatus.pending.value).count(),
        "approved_count": db.query(ModerationQueue).filter(ModerationQueue.status == ModerationStatus.approved.value).count(),
        "rejected_count": db.query(ModerationQueue).filter(ModerationQueue.status == ModerationStatus.rejected.value).count(),
        "blacklist_count": db.query(BlacklistEntry).count(),
    }


def list_moderation_queue(
    db: Session,
    *,
    status_filter: ModerationFilterStatus,
    data_type: str | None = None,
) -> list[ModerationQueue]:
    query = db.query(ModerationQueue).order_by(
        ModerationQueue.status.asc(),
        ModerationQueue.created_at.desc(),
        ModerationQueue.id.desc(),
    )
    if status_filter != "all":
        query = query.filter(ModerationQueue.status == status_filter)
    if data_type:
        query = query.filter(ModerationQueue.data_type == data_type)
    return query.all()


def resolve_moderation_item(
    db: Session,
    *,
    report_id: int,
    moderator: User,
    action: ModerationAction,
    moderator_comment: str | None,
) -> tuple[ModerationQueue, BlacklistEntry | None]:
    item = db.query(ModerationQueue).filter(ModerationQueue.id == report_id).first()
    if not item:
        raise ValueError("Moderation item not found.")

    blacklist_entry = None
    item.status = action
    item.resolved_by_user_id = moderator.id
    item.moderator_comment = moderator_comment.strip() if moderator_comment else None
    item.resolved_at = datetime.now(UTC)

    if action == ModerationStatus.approved.value:
        normalized_value = normalize_value(item.data_type, item.value)
        blacklist_entry = (
            db.query(BlacklistEntry)
            .filter(BlacklistEntry.data_type == item.data_type, BlacklistEntry.value == normalized_value)
            .first()
        )
        if not blacklist_entry:
            blacklist_entry = BlacklistEntry(
                data_type=item.data_type,
                value=normalized_value,
                category=item.ai_category,
                source_report_id=item.id,
                approved_by_user_id=moderator.id,
            )
            db.add(blacklist_entry)
            db.flush()

    db.add(item)
    db.commit()
    db.refresh(item)
    if blacklist_entry:
        db.refresh(blacklist_entry)
    return item, blacklist_entry


def check_blacklist(db: Session, data_type: str, value: str) -> BlacklistEntry | None:
    normalized_value = normalize_value(data_type, value)
    return (
        db.query(BlacklistEntry)
        .filter(BlacklistEntry.data_type == data_type, BlacklistEntry.value == normalized_value)
        .first()
    )


def check_blacklist_batch(
    db: Session,
    items: list[BlacklistBatchCheckItem],
) -> list[tuple[BlacklistBatchCheckItem, BlacklistEntry | None]]:
    results: list[tuple[BlacklistBatchCheckItem, BlacklistEntry | None]] = []
    for item in items:
        results.append((item, check_blacklist(db, item.data_type, item.value)))
    return results
