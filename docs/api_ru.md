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

## 5. Legacy ML Lab API

Все маршруты legacy bridge требуют JWT авторизацию и используются новым разделом `/ml-lab`.

### `GET /api/v1/legacy/files`

Возвращает список файлов из `file_service`.

### `POST /api/v1/legacy/upload`

Принимает `multipart/form-data` с файлом и сохраняет его через `file_service`.

### `GET /api/v1/legacy/columns/{filename}`

Возвращает список колонок выбранного файла.

### `POST /api/v1/legacy/profile`

Создает HTML profile-отчет через `profiling_service`.

Поля:

- `filename`

### `GET /api/v1/legacy/profile-report/{report_filename}`

Возвращает HTML profile-отчета для отображения в новом frontend.

### `POST /api/v1/legacy/ai/analyze`

Запускает AI-анализ датасета через `groq_service`.

Поля:

- `filename`

### `POST /api/v1/legacy/ai/chat`

Чат по датасету через `groq_service`.

Поля:

- `filename`
- `chat_history`

### `GET /api/v1/legacy/models`

Возвращает список моделей из `training_service`.

### `GET /api/v1/legacy/models/{model_name}/config`

Возвращает конфиг модели для динамической формы prediction.

### `POST /api/v1/legacy/train-anomaly-detector`

Запускает обучение anomaly detector через `training_service`.

Поля:

- `filename`
- `model_name`
- `model_type`
- `numerical_features`
- `categorical_features`
- `date_features`
- `enable_feature_engineering`
- `card_id_column`
- `timestamp_column`
- `amount_column`

### `POST /api/v1/legacy/score-file`

Запускает batch scoring файла через `prediction_service`.

Поля:

- `model_name`
- `filename`

### `POST /api/v1/legacy/predict-or-score`

Запускает ручной predict/score по одной строке.

Поля:

- `model_name`
- `features`

### `POST /api/v1/legacy/fraud-check`

Проверяет телефон, email, URL или текст через `fraud_check_service`.

Поля:

- `data_type`: `phone | email | url | text`
- `value`

### `POST /api/v1/legacy/fraud-blacklist`

Добавляет phone/email/domain в blacklist legacy fraud service.

Поля:

- `data_type`: `phone | email | domain`
- `value`

## 6. Admin API

### `GET /api/v1/admin/summary`

Краткая сводка:

- количество пользователей
- количество транзакций
- количество moderation items

### `GET /api/v1/admin/users`

Список всех пользователей.

Доступ:

- только `Admin`

## 7. Health API

### `GET /api/v1/health/`

Базовый health-check backend.

## 8. File service

Основные функции:

- direct upload файла
- хранение выписок
- выдача файлов по имени

Backend `assistant/import-transactions` использует этот сервис как дополнительный канал хранения. Если file service недоступен, импорт транзакций не падает, а возвращает warning.

## 9. Frontend-модули

### `web_frontend/app`

- `page.tsx` — landing page
- `login/page.tsx` — логин
- `register/page.tsx` — регистрация
- `dashboard/page.tsx` — личный кабинет и AI-ассистент
- `moderation/page.tsx` — кабинет модератора
- `ml-lab/page.tsx` — перенесенные Streamlit-сценарии в новом UI
- `ml-lab/profile/page.tsx` — просмотр ydata-profiling HTML-отчета
- `ml-lab/ai-report/page.tsx` — AI report и чат по датасету
- `ml-lab/train/page.tsx` — обучение anomaly detector
- `ml-lab/prediction/page.tsx` — batch score и ручной predict
- `ml-lab/fraud-check/page.tsx` — legacy fraud risk scoring

### `web_frontend/components`

- `auth-form.tsx`
- `assistant-workspace.tsx`
- `fraud-report-center.tsx`
- `moderation-board.tsx`
- `header.tsx`
- `legacy/*`

### `web_frontend/lib`

- `api.ts` — HTTP клиент
- `types.ts` — клиентские типы
- `auth-store.ts` — client auth state
- `site.ts` — site metadata
- `legacy-api.ts` — HTTP-клиент для `/api/v1/legacy/*`
- `legacy-types.ts` — клиентские типы ML Lab
- `use-session-context.ts` — общий JWT session context для client components

## 10. Browser extension

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
