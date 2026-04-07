# Перенос Streamlit-логики в ML Lab

## 1. Цель

Старый Streamlit frontend сохранен в папке `frontend`, но его ключевые пользовательские сценарии теперь доступны в новом Next.js интерфейсе в разделе `ML Lab`.

Новый путь для пользователя:

```text
http://localhost:3000/ml-lab
```

## 2. Что перенесено

Перенесены сценарии старых страниц:

- `frontend/src/app.py`
  Загрузка датасетов, список загруженных файлов, запуск profile-отчета и AI-анализа.
- `frontend/src/pages/0_Data_Profile.py`
  Просмотр HTML-отчета `ydata-profiling`.
- `frontend/src/pages/1_AI_Analyst_Report.py`
  AI-отчет по датасету, аномалии, идеи feature engineering, рекомендации и чат по файлу.
- `frontend/src/pages/2_Train_Model.py`
  Обучение `IsolationForest`, `LocalOutlierFactor`, `OneClassSVM`, выбор признаков и feature engineering.
- `frontend/src/pages/3_Prediction.py`
  Batch scoring файла и ручной predict/score по конфигу модели.
- `frontend/src/pages/4_Fraud_Check.py`
  Проверка телефона, email, URL или текста через legacy fraud scoring service и добавление в blacklist.

## 3. Архитектурное решение

Новый frontend не ходит напрямую в legacy-сервисы. Между ним и старыми микросервисами добавлен bridge в `backend_v3`:

```text
web_frontend -> backend_v3 /api/v1/legacy/* -> legacy services
```

Причины такого решения:

- единая авторизация через JWT;
- браузеру не нужно знать внутренние Docker DNS-имена сервисов;
- меньше CORS-настроек;
- ошибки старых сервисов возвращаются через один API-контракт;
- старый Streamlit можно оставить без изменений.

## 4. Backend bridge

Основные файлы:

- `backend_v3/app/api/routes/legacy.py`
- `backend_v3/app/services/legacy_bridge.py`
- `backend_v3/app/schemas/legacy.py`
- `backend_v3/app/core/config.py`

Маршруты:

```text
GET  /api/v1/legacy/files
POST /api/v1/legacy/upload
GET  /api/v1/legacy/columns/{filename}
POST /api/v1/legacy/profile
GET  /api/v1/legacy/profile-report/{report_filename}
POST /api/v1/legacy/ai/analyze
POST /api/v1/legacy/ai/chat
GET  /api/v1/legacy/models
GET  /api/v1/legacy/models/{model_name}/config
POST /api/v1/legacy/train-anomaly-detector
POST /api/v1/legacy/score-file
POST /api/v1/legacy/predict-or-score
POST /api/v1/legacy/fraud-check
POST /api/v1/legacy/fraud-blacklist
```

Все маршруты требуют авторизации.

## 5. Frontend pages

Новые страницы:

```text
/ml-lab
/ml-lab/profile
/ml-lab/ai-report
/ml-lab/train
/ml-lab/prediction
/ml-lab/fraud-check
```

Основные файлы:

- `web_frontend/app/ml-lab/*`
- `web_frontend/components/legacy/*`
- `web_frontend/lib/legacy-api.ts`
- `web_frontend/lib/legacy-types.ts`
- `web_frontend/lib/use-session-context.ts`

## 6. Запуск

Минимальный новый контур без ML Lab:

```powershell
docker compose up --build backend_api web_frontend file_service db
```

Новый UI с перенесенной Streamlit-логикой:

```powershell
docker compose up --build backend_api web_frontend file_service db groq_service profiling_service training_service prediction_service fraud_check_service
```

Весь стек, включая старый Streamlit:

```powershell
docker compose up --build
```

## 7. Переменные окружения

Для `backend_v3` нужны адреса legacy-сервисов:

```env
FILE_SERVICE_URL=http://file_service:8000
GROQ_SERVICE_URL=http://groq_service:8000
PROFILING_SERVICE_URL=http://profiling_service:8000
TRAINING_SERVICE_URL=http://training_service:8000
PREDICTION_SERVICE_URL=http://prediction_service:8000
FRAUD_CHECK_SERVICE_URL=http://fraud_check_service:8000
```

Для локального запуска без Docker используйте внешние порты:

```powershell
$env:FILE_SERVICE_URL="http://localhost:8000"
$env:GROQ_SERVICE_URL="http://localhost:8008"
$env:PROFILING_SERVICE_URL="http://localhost:8004"
$env:TRAINING_SERVICE_URL="http://localhost:8001"
$env:PREDICTION_SERVICE_URL="http://localhost:8003"
$env:FRAUD_CHECK_SERVICE_URL="http://localhost:8005"
```

## 8. Ограничения

`ML Lab` сохраняет старую ML/AI бизнес-логику. Это означает, что качество работы отдельных сценариев зависит от состояния legacy-сервисов:

- AI Report и чат требуют `groq_service` и `GROQ_API_KEY`;
- Data Profile требует `profiling_service`;
- Train Model требует `training_service`;
- Prediction требует предварительно обученную модель и `prediction_service`;
- legacy Fraud Check требует `fraud_check_service` и PostgreSQL.

Если соответствующий сервис не запущен, новый backend вернет `502` с описанием недоступного сервиса.
