"""Inbound WhatsApp messages: agent reply, then Graph send."""

from __future__ import annotations

from project_message.adapters.whatsapp import (
    parse_text_messages,
    send_text,
    take_if_new,
)
from project_message.core.config import Settings
from project_message.services.agent import reply as agent_reply


def handle_inbound(from_number: str, text: str) -> list[str]:
    stripped = text.strip()
    print(f"[server] received from={from_number} text={stripped!r}", flush=True)

    if not stripped:
        print("[server] empty message, ignored", flush=True)
        return []

    reply_text = agent_reply(from_number, stripped)
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
