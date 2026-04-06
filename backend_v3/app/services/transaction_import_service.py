from dataclasses import dataclass
from datetime import UTC, date, datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.budget_service import get_budget, month_start, sync_budget_balance
from app.services.file_bridge import store_file_via_file_service
from app.services.transaction_service import create_transaction

DATE_COLUMN_CANDIDATES = [
    "date",
    "transaction_date",
    "occurred_at",
    "transaction_dttm",
    "timestamp",
    "datetime",
    "дата",
    "дата операции",
]
AMOUNT_COLUMN_CANDIDATES = [
    "expense",
    "debit",
    "outgoing",
    "sum",
    "amount",
    "transaction_amount_kzt",
    "сумма",
    "сумма операции",
]
CATEGORY_COLUMN_CANDIDATES = [
    "category",
    "mcc_category",
    "merchant_category",
    "категория",
]
DESCRIPTION_COLUMN_CANDIDATES = [
    "description",
    "details",
    "merchant",
    "comment",
    "описание",
    "назначение",
]


@dataclass
class TransactionImportResult:
    stored_filename: str | None
    imported_count: int
    skipped_count: int
    warnings: list[str]
    detected_columns: dict[str, str | None]


def _read_dataframe(filename: str, content: bytes) -> pd.DataFrame:
    extension = Path(filename).suffix.lower()
    if extension == ".csv":
        for encoding in ("utf-8", "utf-8-sig", "cp1251", "latin1"):
            try:
                return pd.read_csv(BytesIO(content), sep=None, engine="python", encoding=encoding)
            except Exception:
                continue
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not parse CSV statement.",
        )

    if extension in {".xlsx", ".xls"}:
        return pd.read_excel(BytesIO(content))

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Only CSV and Excel statements are supported.",
    )


def _normalize_column_name(column_name: str) -> str:
    return str(column_name).strip().lower().replace("_", " ")


def _find_column(columns: list[str], candidates: list[str]) -> str | None:
    normalized = {_normalize_column_name(column): column for column in columns}
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]

    for candidate in candidates:
        for normalized_name, original in normalized.items():
            if candidate in normalized_name:
                return original
    return None


def _to_amount(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None

    raw = str(value).strip().replace(" ", "").replace("\xa0", "")
    raw = raw.replace(",", ".")
    if raw.count(".") > 1:
        head, tail = raw[:-3], raw[-3:]
        raw = head.replace(".", "") + tail

    try:
        amount = float(raw)
    except ValueError:
        return None

    if amount == 0:
        return None
    return abs(amount)


def _to_datetime(value: object) -> datetime | None:
    if value is None or pd.isna(value):
        return None
    try:
        parsed = pd.to_datetime(value, utc=True, dayfirst=True, errors="coerce")
    except Exception:
        return None

    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()


def import_transactions_from_statement(
    db: Session,
    *,
    user: User,
    file: UploadFile,
) -> TransactionImportResult:
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    dataframe = _read_dataframe(file.filename or "statement.csv", content)
    if dataframe.empty:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Statement contains no rows.")

    columns = list(dataframe.columns)
    date_column = _find_column(columns, DATE_COLUMN_CANDIDATES)
    amount_column = _find_column(columns, AMOUNT_COLUMN_CANDIDATES)
    category_column = _find_column(columns, CATEGORY_COLUMN_CANDIDATES)
    description_column = _find_column(columns, DESCRIPTION_COLUMN_CANDIDATES)

    if not amount_column:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not detect amount column in statement.",
        )

    stored_filename, warnings = store_file_via_file_service(file.filename or "statement.csv", content)

    imported_count = 0
    skipped_count = 0
    touched_months: set[date] = set()

    for _, row in dataframe.iterrows():
        amount = _to_amount(row.get(amount_column))
        occurred_at = _to_datetime(row.get(date_column)) if date_column else None

        if amount is None:
            skipped_count += 1
            continue

        if occurred_at is None:
            occurred_at = datetime.now(UTC)

        category = None
        if category_column:
            raw_category = row.get(category_column)
            if raw_category is not None and not pd.isna(raw_category):
                category = str(raw_category).strip() or None

        description = None
        if description_column:
            raw_description = row.get(description_column)
            if raw_description is not None and not pd.isna(raw_description):
                description = str(raw_description).strip() or None

        create_transaction(
            db,
            user_id=user.id,
            occurred_at=occurred_at,
            amount=amount,
            category=category,
            description=description,
            source_filename=stored_filename or file.filename,
        )
        imported_count += 1
        touched_months.add(month_start(occurred_at))

    for touched_month in touched_months:
        budget = get_budget(db, user.id, touched_month)
        if budget:
            sync_budget_balance(db, budget)

    db.commit()

    return TransactionImportResult(
        stored_filename=stored_filename,
        imported_count=imported_count,
        skipped_count=skipped_count,
        warnings=warnings,
        detected_columns={
            "date": date_column,
            "amount": amount_column,
            "category": category_column,
            "description": description_column,
        },
    )
