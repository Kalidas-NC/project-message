"""WhatsApp agent: local commands plus a single-turn Gemini reply."""

from google import genai
from google.genai import types

from project_message.config import get_settings

HELP_TEXT = (
    "Commands:\n"
    "/help — list commands\n"
    "/status — check the WhatsApp webhook"
)

STATUS_TEXT = "WhatsApp webhook is up. Text this number and the agent replies."

SYSTEM_PROMPT = (
    "You are a helpful assistant chatting on WhatsApp. "
    "Answer in short, clear messages. Prefer plain text. "
    "Do not mention that you are an AI unless asked."
)

_MAX_REPLY = 4000
_FAIL = "I could not answer just now."


def _gemini_reply(text: str) -> str:
    settings = get_settings()
    if not settings.gemini_api_key:
        print("[agent] GEMINI_API_KEY unset", flush=True)
        return _FAIL
    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=text,
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        )
    except Exception as exc:
        print(f"[agent] Gemini failed: {exc}", flush=True)
        return _FAIL
    body = (response.text or "").strip()
    if not body:
        print("[agent] Gemini returned empty text", flush=True)
        return _FAIL
    if len(body) > _MAX_REPLY:
        return body[:_MAX_REPLY]
    return body


def reply(text: str) -> str | None:
    stripped = text.strip()
    if not stripped:
        return None

    command = stripped.lower()
    if command == "/help":
        return HELP_TEXT
    if command == "/status":
        return STATUS_TEXT

    return _gemini_reply(stripped)
