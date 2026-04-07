# Техническая архитектура

## 1. Цель системы

AI-Analyst Platform предназначена для двух основных задач:

- контроль личного бюджета и расходов пользователя
- пользовательский antifraud-контур с жалобами, модерацией и browser-side проверкой ссылок и телефонов

Система построена как набор слабосвязанных сервисов, где основной продуктовый поток уже перенесен со старого Streamlit-прототипа на новый web-контур `FastAPI + Next.js`.

## 2. Актуальный системный контур

### Основные компоненты

- `backend_v3`
  Основной REST API. Отвечает за auth, роли, бюджет, транзакции, AI-ассистента, antifraud и модерацию.
- `web_frontend`
  Пользовательский и модераторский web-интерфейс на Next.js App Router.
- `file_service`
  Хранение загруженных выписок и отдача файлов по HTTP.
- `browser_extension`
  Chromium Manifest V3 extension для проверки ссылок и телефонов прямо в браузере.
- `db`
  PostgreSQL для основного продуктового контура.

### Legacy-контур

В репозитории сохранены старые сервисы:

- `frontend`
- `groq_service`
- `training_service`
- `prediction_service`
- `profiling_service`
- `fraud_check_service`

Они не являются основной точкой развития нового продукта, но остаются в репозитории как исторический и экспериментальный контур.

После переноса Streamlit-логики часть legacy-сервисов снова участвует в новом пользовательском интерфейсе через раздел `ML Lab`. Важно различать:

- `frontend` — старый Streamlit UI, сохранен как отдельный интерфейс.
- `groq_service`, `profiling_service`, `training_service`, `prediction_service`, `fraud_check_service` — старые микросервисы, к которым новый `backend_v3` обращается через `/api/v1/legacy/*`.
- `web_frontend/app/ml-lab` — новый Next.js UI для сценариев, которые раньше были доступны только в Streamlit.

## 3. Архитектурные принципы

- API-first: вся бизнес-логика вынесена в backend.
- Разделение ролей: пользователь, модератор, risk manager, администратор.
- Изоляция UI: web-клиент и browser extension работают поверх HTTP API.
- Graceful degradation: при отсутствии `GROQ_API_KEY` backend не падает, а использует fallback-эвристики.
- Контейнеризация: основной запуск ориентирован на `docker compose`.

## 4. Backend-архитектура

### Слои backend

- `app/api/routes`
  HTTP endpoints и валидация входа/выхода.
- `app/schemas`
  Pydantic-схемы запросов и ответов.
- `app/services`
  Бизнес-логика и orchestration.
- `app/models`
  SQLAlchemy ORM модели.
- `app/core`
  Конфигурация, БД, security, инициализация приложения.

### Ключевые backend-модули

- `auth`
  Регистрация, логин, refresh-token, профиль текущего пользователя.
- `assistant`
  Бюджет, обзор расходов, импорт выписок, чат с AI-ассистентом.
- `fraud`
  Жалобы пользователей, AI/fallback классификация, очередь модерации, финальный blacklist.
- `admin`
  Сводная аналитика и список пользователей.
- `legacy`
  Authenticated bridge к старым ML/AI/fraud микросервисам для раздела `ML Lab`: файлы, profile-отчеты, AI report, обучение моделей, prediction и legacy fraud-check.

## 5. Модель данных

### Основные таблицы

- `roles`
  Справочник ролей `User`, `Moderator`, `RiskManager`, `Admin`.
- `users`
  Пользователи, email, hashed password, роль.
- `budgets`
  Месячный бюджет пользователя.
- `transactions`
  Импортированные или вручную зафиксированные траты.
- `assistant_messages`
  История чата пользователя с AI-ассистентом.
- `moderation_queue`
  Очередь пользовательских жалоб до решения модератора.
- `blacklist_entries`
  Финальный проверенный blacklist.

### Связи

- `users -> roles`: many-to-one
- `users -> budgets`: one-to-many
- `users -> transactions`: one-to-many
- `users -> assistant_messages`: one-to-many
- `users -> moderation_queue (reporter/resolver)`: one-to-many по двум ролям связи
- `moderation_queue -> blacklist_entries`: one-to-one после approve

## 6. Основные бизнес-потоки

### 6.1 Авторизация

1. Пользователь регистрируется или логинится
2. Backend выдает `access_token` и `refresh_token`
3. Frontend хранит сессию в client auth-store
4. Защищенные маршруты читают bearer token и текущую роль пользователя

### 6.2 Бюджет и AI-ассистент

1. Пользователь задает месячный лимит
2. Импортирует выписку или отправляет сообщение в чат
3. Backend обновляет транзакции и пересчитывает баланс бюджета
4. AI-ассистент отвечает через Groq или fallback-эвристику

### 6.3 Модерация antifraud

1. Пользователь отправляет жалобу
2. Жалоба попадает в `moderation_queue`
3. Background-классификация проставляет предварительную категорию
4. Модератор принимает решение
5. При `approved` запись переносится в `blacklist_entries`

### 6.4 Браузерное расширение

1. Content script собирает ссылки и телефоны со страницы
2. Background/popup отправляет batch-check в backend
3. Совпадения подсвечиваются в UI страницы и popup

### 6.5 ML Lab и перенесенная Streamlit-логика

1. Пользователь открывает защищенный раздел `/ml-lab`
2. Next.js вызывает `/api/v1/legacy/*` с JWT access token
3. `backend_v3` проксирует запрос в нужный legacy-сервис
4. Legacy-сервис выполняет старую бизнес-логику: profiling, Groq-анализ, обучение, prediction или risk scoring
5. Результат возвращается в новый UI без запуска Streamlit-страницы

## 7. Безопасность

- Пароли хранятся только в виде hash
- Используется JWT с разделением access/refresh
- Role-based access control на критичных маршрутах
- Нормализация `url`, `email`, `phone` перед занесением в blacklist
- CORS управляется через `ALLOWED_ORIGINS`

## 8. Технические риски и ограничения

- Продакшн-контур зависит от доступности PostgreSQL
- AI-ветка зависит от Groq, но умеет деградировать в fallback
- Browser extension требует корректный API URL и доступность backend
- Legacy и новый контур живут параллельно, поэтому важно явно документировать, какой стек является основным
