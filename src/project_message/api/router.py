from fastapi import APIRouter

from project_message.api.routes import health, webhook

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(webhook.router)
