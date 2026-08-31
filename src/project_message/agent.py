"""Stub agent — no LLM, no tools. Swap this module later without touching the UI."""

HELP_TEXT = (
    "Commands:\n"
    "/help — list commands\n"
    "/status — check the mock linked session"
)

STATUS_TEXT = (
    "Linked session is up. This is a local mock — nothing is connected to WhatsApp."
)


def reply(text: str) -> str | None:
    stripped = text.strip()
    if not stripped:
        return None

    command = stripped.lower()
    if command == "/help":
        return HELP_TEXT
    if command == "/status":
        return STATUS_TEXT

    return f"Got it: {stripped}"
