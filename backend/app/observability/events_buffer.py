from __future__ import annotations

import asyncio
import datetime as dt
import itertools
from collections import deque

from pydantic import BaseModel, Field


class EventRecord(BaseModel):
    seq: int
    ts: str
    source_ip: str
    source_port: int
    size_bytes: int
    parsed: bool
    parse_error: str | None = None
    action: str
    matched_rule_id: str | None = None
    reason: str
    destination: str | None = None
    fields: dict[str, str] = Field(default_factory=dict)
    raw_preview: str = ""


class EventBuffer:
    def __init__(self, maxlen: int) -> None:
        self._buffer: deque[EventRecord] = deque(maxlen=maxlen)
        self._subscribers: set[asyncio.Queue[EventRecord]] = set()
        self._counter = itertools.count(1)

    def next_seq(self) -> int:
        return next(self._counter)

    @staticmethod
    def now_iso() -> str:
        return dt.datetime.now(tz=dt.UTC).isoformat()

    def add(self, record: EventRecord) -> None:
        self._buffer.append(record)
        for queue in self._subscribers:
            try:
                queue.put_nowait(record)
            except asyncio.QueueFull:
                pass

    def recent(self, limit: int = 100) -> list[EventRecord]:
        items = list(self._buffer)
        return items[-limit:][::-1]

    def subscribe(self) -> asyncio.Queue[EventRecord]:
        queue: asyncio.Queue[EventRecord] = asyncio.Queue(maxsize=200)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[EventRecord]) -> None:
        self._subscribers.discard(queue)
