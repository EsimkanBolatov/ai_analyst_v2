import os
import json
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr, ValidationError
import phonenumbers
import validators
import spacy
from typing import List, Dict, Any, Generator
import logging
import traceback

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Новые импорты для БД ---
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import time

app = FastAPI(title="Fraud Check Service", version="2.2-db")

DB_USER = os.getenv("POSTGRES_USER", "user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_HOST = os.getenv("POSTGRES_HOST", "db")
DB_NAME = os.getenv("POSTGRES_DB", "ai_analyst")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class BlacklistPhone(Base):
    __tablename__ = "blacklist_phones"
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True, nullable=False)

class BlacklistEmail(Base):
    __tablename__ = "blacklist_emails"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)

class BlacklistDomain(Base):
    __tablename__ = "blacklist_domains"
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, unique=True, index=True, nullable=False)


# --- Ивент для создания таблиц при старте ---
@app.on_event("startup")
def on_startup():
    retries = 5
    while retries > 0:
        try:
            with engine.connect() as connection:
                logger.info("Соединение с БД установлено успешно!")
            Base.metadata.create_all(bind=engine)
            logger.info("Таблицы БД успешно созданы/проверены.")
            break
        except Exception as e:
            logger.error(f"Ошибка при создании таблиц БД: {e}")
            retries -= 1
            logger.warning(f"Не удалось подключиться к БД. Попытка через 3 секунды... (Осталось {retries})")
            time.sleep(3)

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Загрузка NLP ---
nlp = None
try:
    nlp = spacy.load("ru_core_news_sm")
    logger.info("NLP-модель 'ru_core_news_sm' успешно загружена.")
except IOError:
    logger.critical("КРИТИЧЕСКАЯ ОШИБКА: Модель 'ru_core_news_sm' не найдена.")

# --- Константы Скоринга ---
FRAUD_KEYWORDS = ["пароль", "банк", "карта", "срочно", "выигрыш", "приз", "перевод", "безопасность", "служба", "логин", "штраф", "полиция", "подтвердить", "отменить", "заблокировать", "перезвонить"]
SCORE_BLACKLIST = 10
SCORE_EXTERNAL_API_BLOCK = 8
SCORE_KEYWORD_MEDIUM = 3
SCORE_KEYWORD_HIGH = 5
SCORE_NER_COMBO = 5

# --- Pydantic Модели ---
class CheckRequest(BaseModel):
    data_type: str
    value: str

class CheckResponse(BaseModel):
    input_value: str
    risk_level: str
    explanation: str
    risk_score: int

# --- Эндпоинт проверки  ---
@app.post("/check/", response_model=CheckResponse)
async def check_data(request: CheckRequest, db: Session = Depends(get_db)):
    risk_score = 0
    explanations = []
    logger.info(f"Получен запрос на проверку: Тип={request.data_type}, Значение={request.value[:50]}...")

    try:
        if request.data_type == "phone":
            try:
                parsed_phone = phonenumbers.parse(request.value, None)
                normalized_phone = phonenumbers.format_number(parsed_phone, phonenumbers.PhoneNumberFormat.E164)
                if db.query(BlacklistPhone).filter(BlacklistPhone.phone == normalized_phone).first():
                    risk_score += SCORE_BLACKLIST
                    explanations.append("Номер телефона найден в черном списке.")
            except phonenumbers.phonenumberutil.NumberParseException:
                 explanations.append("Невалидный формат номера телефона.")

        elif request.data_type == "email":
            logger.info("Начинаем проверку email...")
            try:
                # --- Используем Pydantic валидацию при присваивании ---
                logger.info("Шаг 1: Валидация Email через присваивание...")
                valid_email: EmailStr = request.value
                logger.info(f"Email валиден: {valid_email}")

                logger.info("Шаг 2: Извлечение домена...")
                domain = str(valid_email).split('@')[-1]
                logger.info(f"Домен: {domain}")

                logger.info("Шаг 3: Запрос к таблице BlacklistEmail...")
                email_found = db.query(BlacklistEmail).filter(BlacklistEmail.email == str(valid_email)).first()
                logger.info(f"Email найден в ЧС: {bool(email_found)}")

                logger.info("Шаг 4: Запрос к таблице BlacklistDomain...")
                domain_found = db.query(BlacklistDomain).filter(BlacklistDomain.domain == domain).first()
                logger.info(f"Домен найден в ЧС: {bool(domain_found)}")

                if email_found or domain_found:
                    risk_score += SCORE_BLACKLIST
                    explanations.append("Email или его домен найден в черном списке.")
                logger.info("Проверка email завершена успешно.")

            except (ValueError, ValidationError) as ve:
                 logger.warning(f"Невалидный формат email: {ve}")
                 explanations.append("Невалидный формат email.")
            except Exception as email_exc:
                 logger.exception("НЕОЖИДАННАЯ ОШИБКА при проверке email!")
                 raise HTTPException(status_code=500, detail="Внутренняя ошибка при проверке email.")

        elif request.data_type == "url":
             if not validators.url(request.value):
                explanations.append("Невалидный формат URL.")
             else:
                if "bad-site-example.com" in request.value:
                    risk_score += SCORE_EXTERNAL_API_BLOCK
                    explanations.append("URL помечен как фишинговый (симуляция).")

        elif request.data_type == "text":
            if nlp:
                doc = nlp(request.value.lower())
                found_keywords = []
                found_entities = {"PER": 0, "ORG": 0, "MONEY": 0}
                for token in doc:
                    if token.lemma_ in FRAUD_KEYWORDS:
                        found_keywords.append(token.lemma_)
                for ent in doc.ents:
                    if ent.label_ in found_entities:
                        found_entities[ent.label_] += 1
                if len(found_keywords) >= 2: risk_score += SCORE_KEYWORD_MEDIUM; explanations.append(f"Найдены подозрительные слова: {', '.join(set(found_keywords))}")
                if len(found_keywords) >= 4: risk_score += SCORE_KEYWORD_HIGH
                if found_entities["PER"] > 0 and found_entities["ORG"] > 0: risk_score += SCORE_NER_COMBO; explanations.append("В тексте одновременно упоминаются ФИО и Организация.")
            else:
                explanations.append("NLP-модель не загружена, анализ текста не выполнен.")

        # --- Определение итогового уровня риска ---
        risk_level = "Низкий"
        if 3 <= risk_score <= 7: risk_level = "Средний"
        elif risk_score >= 8: risk_level = "Высокий"
        if not explanations and risk_level == "Низкий": explanations.append("Проверка не выявила очевидных угроз.")

        logger.info(f"Проверка завершена. Уровень риска: {risk_level}, Оценка: {risk_score}")
        return CheckResponse(
            input_value=request.value,
            risk_level=risk_level,
            explanation=" | ".join(explanations),
            risk_score=risk_score
        )

    except Exception as e:
        logger.exception("Критическая ошибка в эндпоинте /check/!")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервиса: {e}")


# --- Эндпоинты добавления ---
class BlacklistEntry(BaseModel):
    data_type: str
    value: str

@app.post("/add-blacklist/", status_code=201)
async def add_to_blacklist(entry: BlacklistEntry, db: Session = Depends(get_db)):
    db_item = None
    try:
        if entry.data_type == "phone":
            parsed_phone = phonenumbers.parse(entry.value, None)
            normalized_phone = phonenumbers.format_number(parsed_phone, phonenumbers.PhoneNumberFormat.E164)
            db_item = BlacklistPhone(phone=normalized_phone)

        elif entry.data_type == "email":
            try:
                valid_email_str: EmailStr = entry.value
                db_item = BlacklistEmail(email=str(valid_email_str)) # Сохраняем строку
            except (ValueError, ValidationError):
                 raise HTTPException(status_code=400, detail="Невалидный формат email.")

        elif entry.data_type == "domain":
            db_item = BlacklistDomain(domain=entry.value)

        else:
            raise HTTPException(status_code=400, detail="Неверный data_type.")

        db.add(db_item)
        db.commit()
        return {"message": f"Запись '{entry.value}' добавлена в черный список."}

    except Exception as e:
        db.rollback()
        logger.warning(f"Не удалось добавить запись '{entry.value}' (возможно, уже существует): {e}")
        # (Комментарий): Лучше вернуть более конкретную ошибку, если это ошибка БД
        if "unique constraint" in str(e).lower():
            raise HTTPException(status_code=400, detail=f"Запись '{entry.value}' уже существует.")
        raise HTTPException(status_code=400, detail=f"Не удалось добавить запись: {e}")


@app.post("/test-data/", status_code=201)
async def add_test_data(db: Session = Depends(get_db)):
    test_phones = [BlacklistPhone(phone="+79991234567"), BlacklistPhone(phone="+18005551234")]
    test_emails = [BlacklistEmail(email="fraud@example.com")]
    test_domains = [BlacklistDomain(domain="bad-site-example.com")]
    try:
        # Проверка на существование перед добавлением (чтобы избежать лишних откатов)
        existing_phones = {p.phone for p in db.query(BlacklistPhone.phone).all()}
        existing_emails = {e.email for e in db.query(BlacklistEmail.email).all()}
        existing_domains = {d.domain for d in db.query(BlacklistDomain.domain).all()}

        items_to_add = []
        items_to_add.extend(p for p in test_phones if p.phone not in existing_phones)
        items_to_add.extend(e for e in test_emails if e.email not in existing_emails)
        items_to_add.extend(d for d in test_domains if d.domain not in existing_domains)

        if items_to_add:
            db.add_all(items_to_add)
            db.commit()
            logger.info(f"Добавлено {len(items_to_add)} тестовых записей.")
            return {"message": f"Добавлено {len(items_to_add)} тестовых записей."}
        else:
             logger.info("Тестовые данные уже существуют.")
             return {"message": "Тестовые данные уже существуют."}

    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при добавлении тестовых данных: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при добавлении тестовых данных.")