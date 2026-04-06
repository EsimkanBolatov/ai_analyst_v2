# API и модульная структура

## 1. Backend API

Базовый префикс:

```text
/api/v1
```

## 2. Auth API

### `POST /api/v1/auth/register`

Создает пользователя и сразу возвращает token pair.

Поля:

- `email`
- `password`

### `POST /api/v1/auth/login`

Логин пользователя и возврат access/refresh токенов.

### `POST /api/v1/auth/refresh`

Обновляет пару токенов по refresh token.

### `GET /api/v1/auth/me`

Возвращает профиль текущего пользователя.

## 3. Assistant API

### `GET /api/v1/assistant/overview`

Возвращает:

- текущий бюджет
- сумму расходов за месяц
- последние транзакции
- историю сообщений с ассистентом

### `PUT /api/v1/assistant/budget`

Обновляет месячный бюджет пользователя.

Поля:

- `monthly_limit`
- `month`

### `POST /api/v1/assistant/chat`

Отправляет сообщение ассистенту.

Backend:

- формирует ответ
- при необходимости извлекает транзакцию
- обновляет бюджет и историю сообщений

### `POST /api/v1/assistant/import-transactions`

Принимает `multipart/form-data` с файлом выписки.

Поддерживаемые форматы:

- `.csv`
- `.xlsx`
- `.xls`

Поддерживаются английские и русские названия колонок, например:

- `date` / `дата`
- `amount` / `сумма`
- `category` / `категория`
- `description` / `описание`

## 4. Fraud API

### `POST /api/v1/fraud/report`

Создает жалобу пользователя.

Поля:

- `data_type`: `phone | url | email | text`
- `value`
- `user_comment`

### `GET /api/v1/fraud/reports/mine`

Список жалоб текущего пользователя.

### `POST /api/v1/fraud/check`

Проверка одного значения против финального blacklist.

### `POST /api/v1/fraud/check-batch`

Пакетная проверка массива значений. Этот маршрут используется browser extension и позволяет не бить backend по одному значению.

### `GET /api/v1/fraud/moderation/queue`

Очередь модерации.

Доступ:

- `Admin`
- `Moderator`
- `RiskManager`

### `POST /api/v1/fraud/moderation/resolve/{report_id}`

Решение по жалобе:

- `approved`
- `rejected`

При `approved` запись добавляется в финальный blacklist.

## 5. Admin API

### `GET /api/v1/admin/summary`

Краткая сводка:

- количество пользователей
- количество транзакций
- количество moderation items

### `GET /api/v1/admin/users`

Список всех пользователей.

Доступ:

- только `Admin`

## 6. Health API

### `GET /api/v1/health/`

Базовый health-check backend.

## 7. File service

Основные функции:

- direct upload файла
- хранение выписок
- выдача файлов по имени

Backend `assistant/import-transactions` использует этот сервис как дополнительный канал хранения. Если file service недоступен, импорт транзакций не падает, а возвращает warning.

## 8. Frontend-модули

### `web_frontend/app`

- `page.tsx` — landing page
- `login/page.tsx` — логин
- `register/page.tsx` — регистрация
- `dashboard/page.tsx` — личный кабинет и AI-ассистент
- `moderation/page.tsx` — кабинет модератора

### `web_frontend/components`

- `auth-form.tsx`
- `assistant-workspace.tsx`
- `fraud-report-center.tsx`
- `moderation-board.tsx`
- `header.tsx`

### `web_frontend/lib`

- `api.ts` — HTTP клиент
- `types.ts` — клиентские типы
- `auth-store.ts` — client auth state
- `site.ts` — site metadata

## 9. Browser extension

Основные модули:

- `manifest.json`
- `background.js`
- `content.js`
- `popup.html`
- `popup.js`
- `popup.css`

Основные сценарии:

- ручная проверка значения из popup
- проверка выделенного текста через context menu
- непрерывный анализ страницы
- подсветка совпадений на странице
