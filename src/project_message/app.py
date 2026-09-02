"""HTTP server: WhatsApp Cloud API webhook in, Graph API replies out."""

from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from project_message.agent import reply as agent_reply
from project_message.config import Settings, get_settings
from project_message.whatsapp import (
    loads_payload,
    parse_text_messages,
    send_text,
    take_if_new,
    verify_signature,
    verify_subscribe,
)

app = FastAPI(title="WhatsApp agent")


def handle_inbound(from_number: str, text: str) -> list[str]:
    stripped = text.strip()
    print(f"[server] received from={from_number} text={stripped!r}", flush=True)

    if not stripped:
        print("[server] empty message, ignored", flush=True)
        return []

    reply_text = agent_reply(stripped)
    if reply_text is None:
        print("[server] no reply", flush=True)
        return []

    print(f"[server] sending {reply_text!r}", flush=True)
    return [reply_text]


def process_whatsapp_payload(payload: dict, settings: Settings) -> None:
    for inbound in parse_text_messages(payload):
        if not take_if_new(inbound.message_id):
            print(f"[whatsapp] duplicate {inbound.message_id}", flush=True)
            continue
        replies = handle_inbound(inbound.from_number, inbound.text)
        if not replies:
            continue
        if not settings.can_send():
            print(
                "[whatsapp] WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID unset; "
                "not sending to Graph",
                flush=True,
            )
            continue
        for reply in replies:
            send_text(settings, inbound.from_number, reply)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/webhook")
def verify_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> PlainTextResponse:
    settings = get_settings()
    if not verify_subscribe(hub_mode, hub_verify_token, settings.whatsapp_verify_token):
        raise HTTPException(status_code=403, detail="verification failed")
    return PlainTextResponse(hub_challenge or "")


@app.post("/webhook")
async def receive_webhook(
    request: Request, background_tasks: BackgroundTasks
) -> dict[str, str]:
    raw = await request.body()
    settings = get_settings()
    signature = request.headers.get("x-hub-signature-256")
    if not verify_signature(settings.whatsapp_app_secret, raw, signature):
        raise HTTPException(status_code=403, detail="invalid signature")
    try:
        payload = loads_payload(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="invalid json") from exc
    background_tasks.add_task(process_whatsapp_payload, payload, settings)
    return {"status": "ok"}
