"""Local commands plus a Pydantic AI turn. Sessions live in session.py."""

from __future__ import annotations

from pydantic_ai import Agent, ModelMessage
from pydantic_ai.capabilities import ReinjectSystemPrompt
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from project_message.core.config import get_settings
#TODO global variable for the agent removal
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

_COMMANDS = {
    "/help": HELP_TEXT,
    "/status": STATUS_TEXT,
    "/reset": RESET_TEXT,
}


def command_name(text: str) -> str | None:
    stripped = text.strip().lower()
    if stripped in _COMMANDS:
        return stripped
    return None


def command_reply(name: str) -> str:
    return _COMMANDS[name]


async def run_turn(
    text: str,
    history: list[ModelMessage],
    conversation_id: str,
) -> tuple[str, list[ModelMessage] | None]:
    """One agent turn. CancelledError propagates. On failure, history is None."""
    settings = get_settings()
    if not settings.gemini_api_key:
        print("[agent] GEMINI_API_KEY unset", flush=True)
        return _FAIL, None

    try:
        agent = Agent(
            GoogleModel(
                settings.gemini_model,
                provider=GoogleProvider(api_key=settings.gemini_api_key),
            ),
            instructions=SYSTEM_PROMPT,
            capabilities=[ReinjectSystemPrompt()],
        )
        result = await agent.run(
            text,
            message_history=history,
            conversation_id=conversation_id,
        )
    except Exception as exc:
        print(f"[agent] Gemini failed: {exc}", flush=True)
        return _FAIL, None

    output = result.output
    if isinstance(output, str):
        body = output.strip()
    else:
        body = str(output or "").strip()
    if not body:
        print("[agent] Gemini returned empty text", flush=True)
        return _FAIL, None

    return body, result.all_messages()
