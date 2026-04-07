# Развертывание и запуск

## 1. Рекомендуемый способ запуска

Основной режим запуска проекта это `docker compose`.

Запускаемые сервисы:

- `db`
- `file_service`
- `backend_api`
- `web_frontend`

Legacy-сервисы можно поднимать только при необходимости.

Для нового раздела `ML Lab` legacy-сервисы уже являются runtime-зависимостью конкретных страниц. Если нужен только бюджет, assistant, moderation и browser extension, достаточно основного набора. Если нужны перенесенные Streamlit-сценарии, нужно поднять также `groq_service`, `profiling_service`, `training_service`, `prediction_service`, `fraud_check_service`.

## 2. Обязательные зависимости

- Docker Desktop или Docker Engine
- Docker Compose v2
- Node.js 20+ для локального frontend режима
- Python 3.12 для локального backend режима

## 3. Конфигурация окружения

Проект читает переменные из корневого `.env`.

Ключевые переменные:

- `GROQ_API_KEY` — ключ AI-провайдера
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `POSTGRES_HOST`
- `JWT_SECRET_KEY`
- `JWT_REFRESH_SECRET_KEY`
- `FILE_SERVICE_URL`
- `GROQ_SERVICE_URL`
- `PROFILING_SERVICE_URL`
- `TRAINING_SERVICE_URL`
- `PREDICTION_SERVICE_URL`
- `FRAUD_CHECK_SERVICE_URL`
- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_SITE_URL`
- `ALLOWED_ORIGINS`
- `SEED_TEST_DATA` — включает локальные тестовые аккаунты и демонстрационные данные
- `DATABASE_URL` — опционально для cloud/managed DB

Для локального Docker-стенда `SEED_TEST_DATA` включен по умолчанию через `docker-compose.yml`. Для production эта переменная должна быть выключена.

Тестовые аккаунты:

```text
user@ai-analyst.app       / Test12345!  / User
moderator@ai-analyst.app  / Test12345!  / Moderator
risk@ai-analyst.app       / Test12345!  / RiskManager
admin@ai-analyst.app      / Test12345!  / Admin
```

## 4. Запуск через Docker

### Шаг 1. Подготовка env

```powershell
Copy-Item .env.example .env
```

### Шаг 2. Проверка Docker daemon

```powershell
docker info
```

Если server section недоступен, сначала запустите Docker Desktop.

### Шаг 3. Старт сервисов

```powershell
docker compose up --build backend_api web_frontend file_service db
```

Для запуска нового UI вместе с `ML Lab`:

```powershell
docker compose up --build backend_api web_frontend file_service db groq_service profiling_service training_service prediction_service fraud_check_service
```

Для запуска всего стека, включая старый Streamlit:

```powershell
docker compose up --build
```

### Шаг 4. Проверка доступности

```powershell
curl http://localhost:8010/api/v1/health/
```

Или откройте:

- `http://localhost:3000`
- `http://localhost:8010/docs`

## 5. Локальный запуск по сервисам

### Backend

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

## 6. Render deployment

В репозитории присутствует `render.yaml` с новым контуром:

- `ai-analyst-v3-file-service`
- `ai-analyst-v3-api`
- `ai-analyst-v3-web`

Перед cloud deploy необходимо:

- задать реальные секреты JWT
- привязать production PostgreSQL
- указать production URL в `NEXT_PUBLIC_SITE_URL`
- актуализировать `NEXT_PUBLIC_API_BASE_URL`
- настроить `ALLOWED_ORIGINS`

## 7. Рекомендации по production

- использовать managed PostgreSQL
- хранить секреты только через secret store провайдера
- включить ротацию JWT secret при изменении security-политики
- завести регулярные backups БД
- добавить reverse proxy и HTTPS termination

## 8. Частые проблемы запуска

### Docker установлен, но контейнеры не стартуют

Причина: Docker daemon не поднят.

Проверка:

```powershell
docker info
```

### Backend не поднимается из локального Python

Причина: может конфликтовать глобальный пакет `app`.

Решение:

- запускать из каталога `backend_v3`
- использовать `..\venv\Scripts\python`

### Frontend build пишет warning по SWC

В проверенной Windows-среде нативный `@next/swc-win32-x64-msvc` не загружался, но `next build` успешно завершался через wasm fallback.
