from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from project_message.adapters.whatsapp import (
    loads_payload,
    verify_signature,
    verify_subscribe,
)
from project_message.api.deps import SettingsDep
from project_message.services.inbound import process_whatsapp_payload

router = APIRouter()


@router.get("/webhook")
def verify_webhook(
    settings: SettingsDep,
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> PlainTextResponse:
    if not verify_subscribe(hub_mode, hub_verify_token, settings.whatsapp_verify_token):
        raise HTTPException(status_code=403, detail="verification failed")
    return PlainTextResponse(hub_challenge or "")


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    settings: SettingsDep,
) -> dict[str, str]:
    raw = await request.body()
    signature = request.headers.get("x-hub-signature-256")
    if not verify_signature(settings.whatsapp_app_secret, raw, signature):
        raise HTTPException(status_code=403, detail="invalid signature")
    try:
        payload = loads_payload(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="invalid json") from exc
    background_tasks.add_task(process_whatsapp_payload, payload, settings)
    return {"status": "ok"}
