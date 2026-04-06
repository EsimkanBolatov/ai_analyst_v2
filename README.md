# AI-Analyst Platform

AI-Analyst Platform is a full-stack anti-fraud and personal finance control system built around:

- `Next.js App Router` frontend
- `FastAPI + PostgreSQL` backend API
- `Groq` powered AI accountant and fraud triage
- `Chromium Manifest V3` browser extension

The repository still contains the legacy Streamlit/ML prototype, but the current product contour is the new `backend_v3 + web_frontend + browser_extension` stack.

## Product Scope

The current release covers all five stages from the specification:

1. Auth foundation: JWT, roles, protected endpoints
2. AI accountant: budgets, transactions, statement import, persistent chat, voice input/output
3. Crowd moderation: user reports, AI categorization, moderator resolution, final blacklist
4. Browser extension: popup check, context menu, continuous page scanning
5. Polish and deploy: loading states, SEO metadata, responsive UI, Docker/Render configuration

## Active Architecture

Primary services:

- `backend_v3`
  FastAPI API for auth, assistant, moderation and blacklist operations
- `web_frontend`
  Next.js App Router client for end users and moderators
- `file_service`
  Shared file storage used for statement upload/import
- `db`
  PostgreSQL database
- `browser_extension`
  Unpacked Chromium extension for browser-side fraud checks

Legacy services kept in the repo:

- `frontend`
- `groq_service`
- `training_service`
- `prediction_service`
- `profiling_service`
- `fraud_check_service`

## Local Run

Create `.env` in the repository root using `.env.example`.

Required variables:

```env
GROQ_API_KEY=replace_with_your_groq_api_key
POSTGRES_USER=postgres
POSTGRES_PASSWORD=replace_with_strong_password
POSTGRES_DB=ai_analyst_db
POSTGRES_HOST=db
JWT_SECRET_KEY=replace_with_long_access_secret
JWT_REFRESH_SECRET_KEY=replace_with_long_refresh_secret
FILE_SERVICE_URL=http://file_service:8000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8010/api/v1
NEXT_PUBLIC_SITE_URL=http://localhost:3000
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:8501
```

Start the current product contour:

```bash
docker-compose up --build backend_api web_frontend file_service db
```

If you still need the legacy prototype too:

```bash
docker-compose up --build
```

Main local URLs:

- Next.js web app: `http://localhost:3000`
- FastAPI backend: `http://localhost:8010`
- FastAPI docs: `http://localhost:8010/docs`
- File service: `http://localhost:8000`
- Legacy Streamlit app: `http://localhost:8501`

## Main API Areas

Auth:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`

Assistant:

- `GET /api/v1/assistant/overview`
- `PUT /api/v1/assistant/budget`
- `POST /api/v1/assistant/chat`
- `POST /api/v1/assistant/import-transactions`

Fraud and moderation:

- `POST /api/v1/fraud/report`
- `GET /api/v1/fraud/reports/mine`
- `POST /api/v1/fraud/check`
- `POST /api/v1/fraud/check-batch`
- `GET /api/v1/fraud/moderation/queue`
- `POST /api/v1/fraud/moderation/resolve/{id}`

## Browser Extension

The Chromium extension is located in `browser_extension`.

Features:

- manual popup check
- right-click context menu for selected text
- continuous DOM scanning of links and phone numbers
- visual highlighting for blacklist matches

How to install:

1. Open `chrome://extensions` or `edge://extensions`
2. Enable `Developer mode`
3. Click `Load unpacked`
4. Select the `browser_extension` folder

The extension expects the backend API at:

- `http://localhost:8010/api/v1` locally
- or the configured Render URL from the popup settings

## Deployment

`render.yaml` now describes the current release contour:

- `ai-analyst-v3-file-service`
- `ai-analyst-v3-api`
- `ai-analyst-v3-web`

The new web client is already containerized in `web_frontend/Dockerfile`.

## Frontend Polish Included

The Next.js application includes:

- route metadata
- Open Graph metadata
- `robots.ts`
- `sitemap.ts`
- `manifest.ts`
- route-level loading skeletons
- responsive layouts for dashboard and moderation areas

## Verification Commands

Backend:

```bash
python -m compileall backend_v3/app
```

Frontend:

```bash
cd web_frontend
npm install
npm run build
```

Extension syntax checks:

```bash
node --check browser_extension/background.js
node --check browser_extension/content.js
node --check browser_extension/popup.js
```

## Notes

- The repository is intentionally transitional: the legacy prototype is still present, but the release-ready path is the Next.js/FastAPI stack.
- For production, set strong JWT secrets and a managed PostgreSQL database.
- For public deployment, update `NEXT_PUBLIC_SITE_URL`, `NEXT_PUBLIC_API_BASE_URL` and `ALLOWED_ORIGINS` to real domains.
