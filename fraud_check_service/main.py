from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Literal
import re # Для поиска стоп-слов

from validation_utils import is_valid_phone, is_valid_email, is_valid_url
from blacklist_utils import check_phone_blacklist, check_email_blacklist, check_url_blacklist

app = FastAPI(title="Fraud Check Service")

# --- Модели данных ---
class CheckRequest(BaseModel):
    data_type: Literal['phone', 'email', 'url', 'text']
    value: str = Field(..., min_length=1)

class CheckResponse(BaseModel):
    input_value: str
    risk_level: Literal['Низкий', 'Средний', 'Высокий', 'Ошибка']
    explanation: str

# --- Простой NLP: список стоп-слов ---
FRAUD_KEYWORDS = [
    "пароль", "логин", "банк", "карта", "счет", "заблокирован", "срочно",
    "выигрыш", "приз", "лотерея", "перевод", "подтвердите", "безопасность",
    "cvv", "код", "смс", "служба безопасности"
]
KEYWORD_THRESHOLD = 2 # Сколько слов должно найтись для повышения риска

@app.post("/check/", response_model=CheckResponse)
async def check_data(request: CheckRequest):
    data_type = request.data_type
    value = request.value.strip() # Убираем пробелы по краям
    risk = "Низкий" # Уровень риска по умолчанию
    explanations = [] # Список найденных проблем

    # --- 1. Валидация ---
    is_valid = False
    if data_type == 'phone':
        is_valid = is_valid_phone(value)
    elif data_type == 'email':
        is_valid = is_valid_email(value)
    elif data_type == 'url':
        is_valid = is_valid_url(value)
    elif data_type == 'text':
        is_valid = True # Текст не требует особой валидации формата

    if not is_valid:
        return CheckResponse(
            input_value=value,
            risk_level="Ошибка",
            explanation=f"Неверный формат для типа данных '{data_type}'."
        )

    # --- 2. Проверка по черным спискам --- [cite: 114, 150]
    in_blacklist = False
    if data_type == 'phone':
        in_blacklist = check_phone_blacklist(value)
        if in_blacklist: explanations.append("Номер найден во внутреннем черном списке.")
    elif data_type == 'email':
        in_blacklist = check_email_blacklist(value)
        if in_blacklist: explanations.append("Email найден во внутреннем черном списке.")
    elif data_type == 'url':
        in_blacklist = check_url_blacklist(value)
        if in_blacklist: explanations.append("Домен URL найден во внутреннем черном списке.")

    if in_blacklist:
        risk = "Высокий"

    # --- 3. Проверка по внешним API (Симуляция) --- [cite: 116, 151]
    # Здесь можно добавить логику вызова внешних сервисов
    # Например, для URL можно симулировать ответ от Google Safe Browsing
    if data_type == 'url' and not in_blacklist:
        # Симуляция: некоторые домены считаем опасными
        if "login" in value or "secure" in value or ".xyz" in value:
            risk = "Средний" # Или Высокий, в зависимости от логики
            explanations.append("Симуляция: Внешний сервис пометил URL как потенциально опасный.")

    # --- 4. Анализ текста --- [cite: 118, 152]
    if data_type == 'text':
        found_keywords = []
        text_lower = value.lower()
        for keyword in FRAUD_KEYWORDS:
            if keyword in text_lower:
                found_keywords.append(keyword)

        if len(found_keywords) >= KEYWORD_THRESHOLD:
            risk = "Средний" if risk == "Низкий" else risk # Повышаем риск, если еще не высокий
            explanations.append(f"Текст содержит подозрительные слова: {', '.join(found_keywords)}.")
        elif len(found_keywords) > 0:
             explanations.append(f"Текст содержит потенциально подозрительные слова: {', '.join(found_keywords)}.")

    # --- 5. Формирование ответа --- [cite: 122]
    if not explanations and risk == "Низкий":
        explanation = "Проверка не выявила явных угроз."
    else:
        explanation = " ".join(explanations)

    return CheckResponse(
        input_value=value,
        risk_level=risk,
        explanation=explanation
    )