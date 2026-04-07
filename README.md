# AI-Analyst Platform

AI-Analyst Platform это full-stack платформа для контроля личных финансов и пользовательского antifraud-мониторинга. Актуальный рабочий контур проекта построен на `FastAPI + PostgreSQL + Next.js + Chromium Extension`.

Репозиторий все еще содержит старый Streamlit/ML-прототип, но основной поддерживаемый путь сейчас это:

- `backend_v3` — основной API
- `web_frontend` — новый web-клиент
- `file_service` — сервис хранения и отдачи файлов
- `groq_service`, `profiling_service`, `training_service`, `prediction_service`, `fraud_check_service` — старые ML/AI/fraud сервисы, подключенные к новому UI через раздел `ML Lab`
- `browser_extension` — браузерное расширение Chromium Manifest V3

## Что уже реализовано

Текущий контур закрывает этапы 1-5 из ТЗ:

1. Авторизация, роли, JWT, защищенные API
2. AI-ассистент по бюджету, импорт банковских выписок, чат, voice UX
3. Жалобы пользователей, очередь модерации, финальный blacklist
4. Браузерное расширение для проверки ссылок и телефонов
5. Полировка UI, metadata, deploy-конфиги и release-ready документация
6. Перенос логики старых Streamlit-страниц в новый Next.js UI без удаления старого Streamlit-контура

## Структура репозитория

```text
backend_v3/         FastAPI API, бизнес-логика, модели, схемы
web_frontend/       Next.js App Router frontend
file_service/       FastAPI сервис загрузки и выдачи файлов
groq_service/       legacy AI Analyst service для отчетов и чата по датасету
profiling_service/  legacy ydata-profiling service для HTML-отчетов
training_service/   legacy ML training service
prediction_service/ legacy scoring/prediction service
fraud_check_service/ legacy risk-scoring service
browser_extension/  Chromium MV3 extension
frontend/           legacy Streamlit prototype
docs/               русскоязычная техническая и эксплуатационная документация
docker-compose.yml  основной compose-файл
render.yaml         cloud deployment template
```

## Быстрый запуск через Docker

### Предварительные требования

- Windows/macOS/Linux
- Docker Desktop или Docker Engine + Docker Compose
- Git

Важно: перед запуском контейнеров Docker daemon должен быть поднят. В ходе проверки проекта `docker compose config` проходил успешно, но `docker info` показывал, что локальный `dockerDesktopLinuxEngine` был не запущен.

### 1. Подготовьте `.env`

Скопируйте пример:

```powershell
Copy-Item .env.example .env
```

Минимально проверьте и заполните:

```env
GROQ_API_KEY=replace_with_your_groq_api_key
POSTGRES_USER=postgres
POSTGRES_PASSWORD=replace_with_strong_password
POSTGRES_DB=ai_analyst_db
POSTGRES_HOST=db
JWT_SECRET_KEY=replace_with_long_access_secret
JWT_REFRESH_SECRET_KEY=replace_with_long_refresh_secret
FILE_SERVICE_URL=http://file_service:8000
GROQ_SERVICE_URL=http://groq_service:8000
PROFILING_SERVICE_URL=http://profiling_service:8000
TRAINING_SERVICE_URL=http://training_service:8000
PREDICTION_SERVICE_URL=http://prediction_service:8000
FRAUD_CHECK_SERVICE_URL=http://fraud_check_service:8000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8010/api/v1
NEXT_PUBLIC_SITE_URL=http://localhost:3000
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:8501
SEED_TEST_DATA=true
```

`SEED_TEST_DATA=true` включает локальные тестовые аккаунты и демонстрационные данные. В production эту переменную нужно выключить или не задавать.

Тестовые аккаунты для локального стенда:

```text
user@ai-analyst.app       / Test12345!  / User
moderator@ai-analyst.app  / Test12345!  / Moderator
risk@ai-analyst.app       / Test12345!  / RiskManager
admin@ai-analyst.app      / Test12345!  / Admin
```

Seed также создает тестовый бюджет, несколько транзакций, историю ассистента, жалобы в модерации и одну запись в blacklist.

### 2. Запустите основной контур

```powershell
docker compose up --build backend_api web_frontend file_service db
```

Если нужен новый `ML Lab` с перенесенной логикой старых Streamlit-страниц, поднимите также legacy ML/AI/fraud сервисы:

```powershell
docker compose up --build backend_api web_frontend file_service db groq_service profiling_service training_service prediction_service fraud_check_service
```

Если нужен вообще весь стек, включая старый Streamlit UI:

```powershell
docker compose up --build
```

### 3. Откройте сервисы

- Web UI: `http://localhost:3000`
- ML Lab в новом UI: `http://localhost:3000/ml-lab`
- Backend API: `http://localhost:8010`
- Swagger/OpenAPI: `http://localhost:8010/docs`
- File service: `http://localhost:8000`
- Legacy Streamlit: `http://localhost:8501`

## Локальный запуск без Docker

Этот режим полезен, если Docker недоступен или нужно дебажить сервисы по отдельности.

### Backend API

```powershell
cd backend_v3
..\venv\Scripts\python -m pip install -r requirements.txt
$env:DATABASE_URL="postgresql+psycopg2://postgres:password@localhost:5433/ai_analyst_db"
$env:JWT_SECRET_KEY="dev-access-secret"
$env:JWT_REFRESH_SECRET_KEY="dev-refresh-secret"
$env:FILE_SERVICE_URL="http://localhost:8000"
$env:GROQ_SERVICE_URL="http://localhost:8008"
$env:PROFILING_SERVICE_URL="http://localhost:8004"
$env:TRAINING_SERVICE_URL="http://localhost:8001"
$env:PREDICTION_SERVICE_URL="http://localhost:8003"
$env:FRAUD_CHECK_SERVICE_URL="http://localhost:8005"
$env:ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
..\venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
```

Примечание: для Python-команд используйте проектный `venv`. В этом окружении глобальный `python` конфликтовал со сторонним пакетом `app`, поэтому запуск из `backend_v3` через `..\venv\Scripts\python` является правильным вариантом.

### File service

```powershell
cd file_service
..\venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```powershell
cd web_frontend
npm install
$env:NEXT_PUBLIC_API_BASE_URL="http://localhost:8010/api/v1"
$env:NEXT_PUBLIC_SITE_URL="http://localhost:3000"
npm run dev
```

## Браузерное расширение

1. Откройте `chrome://extensions` или `edge://extensions`
2. Включите `Developer mode`
3. Нажмите `Load unpacked`
4. Выберите папку `browser_extension`

Расширение ожидает API по адресу `http://localhost:8010/api/v1`, либо по URL, который пользователь задаст в popup-настройках.

## Проверки и тесты

Команды, которые стоит прогонять перед релизом:

```powershell
python -m compileall backend_v3\app file_service
cd web_frontend; npm run build
cd ..; node --check browser_extension\background.js
node --check browser_extension\content.js
node --check browser_extension\popup.js
docker compose --env-file .env.example config
docker compose build backend_api
docker compose build web_frontend
```

Дополнительно в проекте выполнен прикладной backend smoke-test через `FastAPI TestClient` с проверкой:

- health endpoint
- register / login / refresh / me
- budget update
- assistant chat с автоматической фиксацией транзакции
- импорт CSV с русскими колонками
- fraud report / moderation / blacklist
- admin summary / role-based access

Подробности вынесены в [docs/testing_ru.md](docs/testing_ru.md).

## Документация

- [Архитектура](docs/architecture_ru.md)
- [API и модули](docs/api_ru.md)
- [Развертывание](docs/deployment_ru.md)
- [Тестирование и контроль качества](docs/testing_ru.md)
- [Эксплуатация и сопровождение](docs/operations_ru.md)
- [Браузерное расширение](docs/browser_extension_ru.md)
- [Перенос Streamlit-логики в ML Lab](docs/legacy_migration_ru.md)

## Известные особенности среды

- Если `docker info` не видит server section, сначала запустите Docker Desktop.
- На текущей Windows-среде `Next.js build` предупреждает о проблеме с нативным `@next/swc-win32-x64-msvc`, но сборка успешно завершается через wasm fallback.
- Если `GROQ_API_KEY` не задан, AI-ответы backend продолжают работать через fallback-эвристики.
- Раздел `ML Lab` использует старые микросервисы. Если запущены только `backend_api web_frontend file_service db`, страницы `Data Profile`, `AI Report`, `Train Model`, `Prediction` и legacy `Fraud Check` будут возвращать ошибку недоступности соответствующего legacy-сервиса.

## Актуальные изменения после технической проверки

В ходе тестирования были найдены и исправлены следующие дефекты:

1. Исправлен парсинг `ALLOWED_ORIGINS` из `.env` и Docker env.
2. Зафиксирована совместимая версия `bcrypt` для работы регистрации и логина.
3. Исправлены битые русские строки в assistant/fraud сервисах.
4. Исправлен разбор ISO-дат при импорте банковских выписок.

## Следующий практический шаг

После запуска через Docker стоит пройти ручной e2e smoke:

1. Регистрация пользователя в web UI
2. Настройка бюджета
3. Импорт реальной банковской выписки
4. Создание жалобы и модерация
5. Проверка браузерного расширения на тестовой странице
