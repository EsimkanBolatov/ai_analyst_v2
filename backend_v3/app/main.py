from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# Импортируем роутеры (создадим их позже)
# from app.api import upload_router, predict_router

app = FastAPI(title="AI-Analyst v3.0 Backend")

# Настройка CORS для взаимодействия с React (localhost:3000)
origins = [
    "http://localhost:3000",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "AI-Analyst Backend is running"}

# app.include_router(upload_router.router)