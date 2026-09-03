"""Per-number pending buffer: one job waits 2s, then runs the agent and sends."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from pydantic_ai import ModelMessage

from project_message.adapters.whatsapp import digits_only
from project_message.services.agent import run_turn

SendFn = Callable[[str, str], None]


@dataclass(frozen=True)
class PendingInbound:
    message_id: str
    text: str
    received_at: float


@dataclass
class Session:
    key: str
    from_number: str
    history: list[ModelMessage] = field(default_factory=list)
    pending: list[PendingInbound] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    job: asyncio.Task[None] | None = None


class SessionManager:
    def __init__(self, debounce_seconds: float, send: SendFn) -> None:
        self._debounce_seconds = debounce_seconds
        self._send = send
        self._sessions: dict[str, Session] = {}

    def _key(self, from_number: str) -> str:
        return digits_only(from_number) or from_number

    def _session_for(self, from_number: str) -> Session:
        key = self._key(from_number)
        session = self._sessions.get(key)
        if session is None:
            session = Session(key=key, from_number=from_number)
            self._sessions[key] = session
        else:
            session.from_number = from_number
        return session

    async def ingest(self, from_number: str, message_id: str, text: str) -> None:
        stripped = text.strip()
        if not stripped:
            return
        session = self._session_for(from_number)
        async with session.lock:
            session.pending.append(
                PendingInbound(
                    message_id=message_id,
                    text=stripped,
                    received_at=time.monotonic(),
                )
            )
            if session.job is not None and not session.job.done():
                session.job.cancel()
            session.job = asyncio.create_task(
                self._job(session),
                name=f"session:{session.key}",
            )
            print(
                f"[session] queued from={from_number} pending={len(session.pending)} "
                f"window={self._debounce_seconds}s",
                flush=True,
            )

    async def reset(self, from_number: str) -> None:
        session = self._session_for(from_number)
        async with session.lock:
            if session.job is not None and not session.job.done():
                session.job.cancel()
            session.job = None
            session.pending.clear()
            session.history.clear()

    async def shutdown(self) -> None:
        jobs: list[asyncio.Task[None]] = []
        for session in self._sessions.values():
            if session.job is not None and not session.job.done():
                session.job.cancel()
                jobs.append(session.job)
            session.job = None
        if jobs:
            await asyncio.gather(*jobs, return_exceptions=True)

    async def _job(self, session: Session) -> None:
        try:
            await asyncio.sleep(self._debounce_seconds)
            joined = "\n".join(item.text for item in session.pending)
            history = list(session.history)
            from_number = session.from_number
            print(
                f"[session] window elapsed from={from_number} "
                f"pending={len(session.pending)}",
                flush=True,
            )
            reply, new_history = await run_turn(joined, history, session.key)
            if session.job is not asyncio.current_task():
                return
            print(f"[server] sending {reply!r}", flush=True)
            self._send(from_number, reply)
            async with session.lock:
                if session.job is not asyncio.current_task():
                    return
                if new_history is not None:
                    session.history = new_history
                session.pending.clear()
                print(f"[session] committed from={from_number}", flush=True)
        except asyncio.CancelledError:
            return
