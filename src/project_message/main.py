from contextlib import asynccontextmanager

from fastapi import FastAPI

from project_message.api.router import api_router
from project_message.core.config import get_settings
from project_message.services.inbound import deliver
from project_message.services.session import SessionManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    manager = SessionManager(
        debounce_seconds=settings.inbound_debounce_seconds,
        send=lambda to_number, body: deliver(settings, to_number, body),
    )
    app.state.sessions = manager
    yield
    await manager.shutdown()


app = FastAPI(title="WhatsApp agent", lifespan=lifespan)
app.include_router(api_router)
