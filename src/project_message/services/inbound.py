"""Inbound WhatsApp messages: commands now, other texts through the session window."""

from __future__ import annotations

from project_message.adapters.whatsapp import (
    parse_text_messages,
    send_text,
    take_if_new,
)
from project_message.core.config import Settings
from project_message.services.agent import command_name, command_reply
from project_message.services.session import SessionManager


def deliver(settings: Settings, to_number: str, body: str) -> None:
    if not settings.can_send():
        print(
            "[whatsapp] WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID unset; "
            "not sending to Graph",
            flush=True,
        )
        return
    send_text(settings, to_number, body)


async def handle_inbound(
    from_number: str,
    message_id: str,
    text: str,
    sessions: SessionManager,
) -> str | None:
    stripped = text.strip()
    print(f"[server] received from={from_number} text={stripped!r}", flush=True)

    if not stripped:
        print("[server] empty message, ignored", flush=True)
        return None

    name = command_name(stripped)
    if name == "/reset":
        await sessions.reset(from_number)
        print(f"[server] sending {command_reply(name)!r}", flush=True)
        return command_reply(name)
    if name is not None:
        print(f"[server] sending {command_reply(name)!r}", flush=True)
        return command_reply(name)

    await sessions.ingest(from_number, message_id, stripped)
    return None


async def process_whatsapp_payload(
    payload: dict,
    settings: Settings,
    sessions: SessionManager,
) -> None:
    for inbound in parse_text_messages(payload):
        if not take_if_new(inbound.message_id):
            print(f"[whatsapp] duplicate {inbound.message_id}", flush=True)
            continue
        reply = await handle_inbound(
            inbound.from_number,
            inbound.message_id,
            inbound.text,
            sessions,
        )
        if reply is None:
            continue
        deliver(settings, inbound.from_number, reply)
