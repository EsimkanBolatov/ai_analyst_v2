from fastapi import APIRouter

from app.api.routes import admin, assistant, auth, fraud, health

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(assistant.router, prefix="/assistant", tags=["assistant"])
api_router.include_router(fraud.router, prefix="/fraud", tags=["fraud"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
