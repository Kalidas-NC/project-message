from fastapi import FastAPI

from project_message.api.router import api_router

app = FastAPI(title="WhatsApp agent")
app.include_router(api_router)
