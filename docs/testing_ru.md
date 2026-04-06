# Тестирование и контроль качества

## 1. Подход к тестированию

Для проекта использовались три уровня проверки:

- статические и синтаксические проверки
- сборка frontend и extension
- прикладной backend smoke-test на `FastAPI TestClient`

Полноценный `docker compose up` интеграционный прогон в этой среде не был выполнен из-за отсутствия запущенного Docker daemon, но compose-конфиг был успешно провален через `docker compose config`.

## 2. Выполненные команды

### Backend

```powershell
python -m compileall backend_v3\app file_service
cd backend_v3
..\venv\Scripts\python -c "from app.main import app; print(app.title)"
```

### Frontend

```powershell
cd web_frontend
npm run build
```

### Browser extension

```powershell
node --check browser_extension\background.js
node --check browser_extension\content.js
node --check browser_extension\popup.js
```

### Docker config

```powershell
docker compose --env-file .env.example config
docker info
```

## 3. Прикладной backend smoke-test

Smoke-test прогонялся через временную SQLite-базу и `FastAPI TestClient`, чтобы проверить бизнес-критичные маршруты без Docker.

Проверенные сценарии:

1. `GET /api/v1/health/`
2. `POST /api/v1/auth/register`
3. `POST /api/v1/auth/login`
4. `POST /api/v1/auth/refresh`
5. `GET /api/v1/auth/me`
6. `PUT /api/v1/assistant/budget`
7. `POST /api/v1/assistant/chat`
8. `POST /api/v1/assistant/import-transactions`
9. `GET /api/v1/assistant/overview`
10. `POST /api/v1/fraud/report`
11. `GET /api/v1/fraud/reports/mine`
12. `GET /api/v1/fraud/moderation/queue`
13. `POST /api/v1/fraud/moderation/resolve/{id}`
14. `POST /api/v1/fraud/check`
15. `POST /api/v1/fraud/check-batch`
16. `GET /api/v1/admin/summary`
17. role-based access check для `GET /api/v1/admin/users`

## 4. Результат smoke-test

Результат: `SMOKE_TEST_OK`

Ключевые подтвержденные эффекты:

- регистрация и логин работают
- refresh token работает
- русская фраза `Потратил 1200 на такси до офиса` создает транзакцию категории `Транспорт`
- импорт CSV с русскими колонками работает
- бюджет и месячные расходы корректно пересчитываются
- moderation approval переносит запись в blacklist
- role-based access работает корректно

## 5. Найденные дефекты и исправления

### Дефект 1. `ALLOWED_ORIGINS` ломал запуск через env

Симптом:

- backend падал при парсинге `ALLOWED_ORIGINS=http://localhost:3000,...`

Причина:

- `pydantic-settings` пытался парсить `list[str]` как JSON раньше кастомного split.

Исправление:

- поле переведено на `Annotated[list[str], NoDecode]`

### Дефект 2. Несовместимость `passlib` и `bcrypt`

Симптом:

- регистрация и логин падали во время хеширования пароля

Причина:

- текущая версия `bcrypt` в окружении не была совместима с выбранной конфигурацией `passlib`

Исправление:

- в `backend_v3/requirements.txt` добавлен `bcrypt==3.2.2`

### Дефект 3. Битые русские строки в assistant/fraud сервисах

Симптом:

- fallback-эвристики не распознавали русские пользовательские сообщения

Причина:

- строковые литералы были повреждены по кодировке

Исправление:

- сервисы `assistant_service.py`, `fraud_service.py`, `transaction_import_service.py` нормализованы в UTF-8

### Дефект 4. Неверный разбор ISO-дат в банковской выписке

Симптом:

- `2026-04-02` разбиралось как февраль или март при `dayfirst=True`

Причина:

- единый `dayfirst=True` применялся даже к ISO-like датам `YYYY-MM-DD`

Исправление:

- добавлена эвристика: для ISO-like дат `dayfirst=False`, для остальных форматов сохраняется day-first parsing

## 6. Наблюдения, не блокирующие релиз

### `next build` warning по SWC

Сборка проходит успешно, но на проверенной Windows-машине нативный `@next/swc-win32-x64-msvc` не загружается и Next.js переключается на wasm fallback.

### File service warning в isolated smoke-test

Во время `TestClient` smoke-test file service намеренно не поднимался, поэтому `assistant/import-transactions` возвращал warning о недоступности file service. Это корректное поведение деградации, а не ошибка бизнес-логики.

## 7. Что еще желательно проверить вручную

- e2e вход через реальный браузер
- загрузку реальной банковской выписки `.xlsx`
- voice input/output в браузере
- работу browser extension на нескольких тестовых доменах
- сценарии с реальным Groq API key
- сценарии с PostgreSQL внутри поднятого Docker-контура
