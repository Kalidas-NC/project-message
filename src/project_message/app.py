"""HTTP server: receive a message, print it here, reply to the client."""

from fastapi import FastAPI
from pydantic import BaseModel, Field

from project_message.agent import reply as agent_reply
from project_message.policy import is_allowed, normalize_number

app = FastAPI(title="Agent mock server")


class InboundMessage(BaseModel):
    from_: str = Field(alias="from")
    text: str

    model_config = {"populate_by_name": True}


class OutboundReply(BaseModel):
    text: str


class MessageResponse(BaseModel):
    ok: bool
    replies: list[OutboundReply] = Field(default_factory=list)
    reason: str | None = None


def handle_inbound(from_number: str, text: str) -> MessageResponse:
    number = normalize_number(from_number)
    stripped = text.strip()
    print(f"[server] received from={number} text={stripped!r}", flush=True)

    if not is_allowed(number):
        print(f"[server] denied {number}", flush=True)
        return MessageResponse(ok=False, reason="not_allowed")

    if not stripped:
        print("[server] empty message, ignored", flush=True)
        return MessageResponse(ok=True, replies=[])

    reply_text = agent_reply(stripped)
    if reply_text is None:
        print("[server] no reply", flush=True)
        return MessageResponse(ok=True, replies=[])

    print(f"[server] sending {reply_text!r}", flush=True)
    return MessageResponse(ok=True, replies=[OutboundReply(text=reply_text)])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/messages", response_model=MessageResponse)
def post_message(inbound: InboundMessage) -> MessageResponse:
    return handle_inbound(inbound.from_, inbound.text)
