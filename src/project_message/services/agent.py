"""WhatsApp agent: local commands plus a Pydantic AI reply with per-number history."""

from __future__ import annotations

import threading

from pydantic_ai import Agent, ModelMessage
from pydantic_ai.capabilities import ReinjectSystemPrompt
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from project_message.adapters.whatsapp import digits_only
from project_message.core.config import get_settings

HELP_TEXT = (
    "Commands:\n"
    "/help — list commands\n"
    "/status — check the WhatsApp webhook\n"
    "/reset — forget this chat"
)

STATUS_TEXT = "WhatsApp webhook is up. Text this number and the agent replies."

RESET_TEXT = "Forgot this chat. Next message starts a new conversation."

SYSTEM_PROMPT = (
    "You are a helpful assistant chatting on WhatsApp. "
    "Answer in short, clear messages. Prefer plain text. "
    "Do not mention that you are an AI unless asked."
)

_FAIL = "I could not answer just now."

_lock = threading.Lock()
_sessions: dict[str, list[ModelMessage]] = {}
_agent: Agent | None = None


def _session_key(from_number: str) -> str:
    return digits_only(from_number) or from_number


def _get_agent() -> Agent:
    global _agent
    if _agent is None:
        settings = get_settings()
        provider = GoogleProvider(api_key=settings.gemini_api_key)
        model = GoogleModel(settings.gemini_model, provider=provider)
        _agent = Agent(
            model,
            instructions=SYSTEM_PROMPT,
            capabilities=[ReinjectSystemPrompt()],
        )
    return _agent


def _llm_reply(from_number: str, text: str) -> str:
    settings = get_settings()
    if not settings.gemini_api_key:
        print("[agent] GEMINI_API_KEY unset", flush=True)
        return _FAIL

    key = _session_key(from_number)
    with _lock:
        history = list(_sessions.get(key, []))

    try:
        result = _get_agent().run_sync(
            text,
            message_history=history,
            conversation_id=key,
        )
    except Exception as exc:
        print(f"[agent] Gemini failed: {exc}", flush=True)
        return _FAIL

    output = result.output
    if isinstance(output, str):
        body = output.strip()
    else:
        body = str(output or "").strip()
    if not body:
        print("[agent] Gemini returned empty text", flush=True)
        return _FAIL

    with _lock:
        _sessions[key] = result.all_messages()
    return body


def reply(from_number: str, text: str) -> str | None:
    stripped = text.strip()
    if not stripped:
        return None

    command = stripped.lower()
    if command == "/help":
        return HELP_TEXT
    if command == "/status":
        return STATUS_TEXT
    if command == "/reset":
        key = _session_key(from_number)
        with _lock:
            _sessions.pop(key, None)
        return RESET_TEXT

    return _llm_reply(from_number, stripped)
