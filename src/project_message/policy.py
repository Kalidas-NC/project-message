"""Sender allowlist — stands in for Cloud API / OpenClaw allowFrom."""

DEFAULT_ALLOWLIST = ["+15551234567"]


def normalize_number(raw: str) -> str:
    compact = "".join(ch for ch in raw.strip() if ch.isalnum() or ch == "+")
    if not compact:
        return ""
    if not compact.startswith("+"):
        compact = f"+{compact}"
    return compact


def is_allowed(raw: str, allowlist: list[str] | None = None) -> bool:
    allowed = allowlist if allowlist is not None else DEFAULT_ALLOWLIST
    number = normalize_number(raw)
    if not number:
        return False
    normalized_allowlist = {normalize_number(entry) for entry in allowed}
    return number in normalized_allowlist
