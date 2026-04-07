# Эксплуатация и сопровождение

## 1. Операционная модель

Поддерживаемый production-контур:

- `web_frontend`
- `backend_v3`
- `file_service`
- `PostgreSQL`

Legacy-сервисы не должны считаться обязательной частью базового эксплуатационного контура без отдельного решения команды.

Исключение: если в production включается раздел `ML Lab`, то для него нужны `groq_service`, `profiling_service`, `training_service`, `prediction_service` и `fraud_check_service`. В таком режиме они становятся зависимостями конкретной функциональной зоны, а не всего продукта.

## 2. Health и доступность

### Backend health-check

```text
GET /api/v1/health/
```

### Что мониторить

- доступность backend API
- доступность PostgreSQL
- доступность file service
- ошибки аутентификации и refresh
- backlog очереди модерации
- скорость ответов assistant и fraud endpoints
- ошибки `/api/v1/legacy/*`, если используется `ML Lab`
- доступность legacy-сервисов, если включены перенесенные Streamlit-сценарии

## 3. Логи

Минимально стоит собирать:

- startup/shutdown backend
- ошибки DB connection
- ошибки Groq API
- ошибки upload/import
- ошибки moderation resolve
- ошибки browser extension batch-check, если backend фиксирует метрики

## 4. Резервное копирование

Основной актив для backup:

- PostgreSQL database

Дополнительно можно хранить:

- папку upload-хранилища file service
- snapshot env-конфигурации без секретов

Рекомендуется:

- ежедневный backup БД
- контроль успешности восстановления
- отдельное хранение backup-архива

## 5. Секреты и безопасность эксплуатации

- не хранить production secrets в git
- использовать отдельные секреты для dev/stage/prod
- регулярно ротировать JWT secrets при инцидентах
- ограничивать CORS только доверенными доменами
- не публиковать backend без HTTPS и reverse proxy

## 6. Роли и операционные зоны ответственности

### User

- работа с бюджетом
- загрузка выписок
- взаимодействие с AI-ассистентом
- подача fraud report

### Moderator

- просмотр очереди модерации
- approve/reject жалоб

### RiskManager

- контроль fraud-потока
- аудит модерации

### Admin

- системный доступ
- управление пользователями
- просмотр общей статистики

## 7. Типовой план диагностики

### Backend недоступен

1. Проверить процесс/контейнер backend
2. Проверить соединение с PostgreSQL
3. Проверить корректность `DATABASE_URL` или postgres env
4. Проверить JWT и CORS env

### Не работает импорт выписки

1. Проверить формат файла
2. Проверить наличие колонки суммы
3. Проверить доступность file service
4. Проверить backend warnings в ответе API

### Жалобы не попадают в blacklist

1. Проверить статус `moderation_queue`
2. Проверить, что модератор выполнил `approved`
3. Проверить запись в `blacklist_entries`

### Browser extension ничего не подсвечивает

1. Проверить API URL в popup settings
2. Проверить доступность `POST /api/v1/fraud/check-batch`
3. Проверить, не выключен ли `Continuous Protection`

### ML Lab возвращает ошибку legacy service unavailable

1. Проверить, что поднят соответствующий сервис: `groq_service`, `profiling_service`, `training_service`, `prediction_service` или `fraud_check_service`
2. Проверить env-переменные backend: `GROQ_SERVICE_URL`, `PROFILING_SERVICE_URL`, `TRAINING_SERVICE_URL`, `PREDICTION_SERVICE_URL`, `FRAUD_CHECK_SERVICE_URL`
3. Проверить, что сервис находится в той же Docker network, что и `backend_api`
4. Для AI Report проверить, задан ли `GROQ_API_KEY`

## 8. Рекомендации по развитию сопровождения

- добавить pytest smoke suite в репозиторий
- добавить CI pipeline для backend/frontend/extension
- включить централизованный logging и error tracking
- добавить DB migrations вместо `create_all`
- ввести health/readiness/liveness endpoints по сервисам
