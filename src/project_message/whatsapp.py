"""WhatsApp Cloud API adapter: webhook verify/parse and Graph send."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass

import httpx

from project_message.config import Settings

GRAPH_VERSION = "v23.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"

_seen_ids: set[str] = set()
_SEEN_CAP = 2048


@dataclass(frozen=True)
class InboundText:
    from_number: str
    message_id: str
    text: str


def verify_subscribe(mode: str | None, token: str | None, expected: str) -> bool:
    if not expected:
        return False
    if mode != "subscribe" or token is None:
        return False
    return hmac.compare_digest(token, expected)


def verify_signature(app_secret: str, raw_body: bytes, header: str | None) -> bool:
    if not app_secret:
        print(
            "[whatsapp] WHATSAPP_APP_SECRET unset; skipping signature check",
            flush=True,
        )
        return True
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    received = header.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)


def parse_text_messages(payload: dict) -> list[InboundText]:
    messages: list[InboundText] = []
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            for msg in value.get("messages") or []:
                if msg.get("type") != "text":
                    continue
                body = (msg.get("text") or {}).get("body")
                from_number = msg.get("from")
                message_id = msg.get("id")
                if from_number and message_id and isinstance(body, str):
                    messages.append(
                        InboundText(
                            from_number=from_number,
                            message_id=message_id,
                            text=body,
                        )
                    )
    return messages


def take_if_new(message_id: str) -> bool:
    if message_id in _seen_ids:
        return False
    _seen_ids.add(message_id)
    if len(_seen_ids) > _SEEN_CAP:
        _seen_ids.clear()
        _seen_ids.add(message_id)
    return True


def digits_only(number: str) -> str:
    return "".join(ch for ch in number if ch.isdigit())


def send_text(settings: Settings, to_number: str, body: str) -> None:
    url = f"{GRAPH_BASE}/{settings.whatsapp_phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": digits_only(to_number),
        "type": "text",
        "text": {"body": body},
    }
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"[whatsapp] Graph send failed: {exc}", flush=True)
        if isinstance(exc, httpx.HTTPStatusError):
            print(f"[whatsapp] Graph body {exc.response.text!r}", flush=True)
        return
    print(f"[whatsapp] Graph accepted {response.text}", flush=True)


def loads_payload(raw_body: bytes) -> dict:
    if not raw_body:
        return {}
    data = json.loads(raw_body.decode())
    if not isinstance(data, dict):
        raise ValueError("webhook payload must be an object")
    return data
