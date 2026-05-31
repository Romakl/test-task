from __future__ import annotations

import asyncio
import contextlib

from app.core.config import Settings
from app.core.logging import get_logger
from app.observability.event_repository import EventRepository
from app.observability.events_buffer import EventRecord
from app.observability.metrics import Metrics


logger = get_logger("cefproxy.eventwriter")


class EventWriter:
    def __init__(
        self, *, repository: EventRepository, metrics: Metrics, settings: Settings
    ) -> None:
        self._repository = repository
        self._metrics = metrics
        self._batch = settings.EVENT_WRITE_BATCH
        self._queue: asyncio.Queue[EventRecord] = asyncio.Queue(
            maxsize=settings.EVENT_WRITE_QUEUE_MAXSIZE
        )
        self._task: asyncio.Task[None] | None = None

    def enqueue(self, record: EventRecord) -> None:
        try:
            self._queue.put_nowait(record)
        except asyncio.QueueFull:
            self._metrics.event_persist_dropped += 1

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="event-writer")

    async def _run(self) -> None:
        while True:
            batch = [await self._queue.get()]
            while len(batch) < self._batch:
                try:
                    batch.append(self._queue.get_nowait())
                except asyncio.QueueEmpty:
                    break
            await self._flush(batch)
            for _ in batch:
                self._queue.task_done()

    async def _flush(self, batch: list[EventRecord]) -> None:
        try:
            await self._repository.add_many(batch)
            self._metrics.events_persisted += len(batch)
        except Exception:
            logger.exception("failed to persist %d event(s)", len(batch))

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        leftover: list[EventRecord] = []
        while not self._queue.empty():
            leftover.append(self._queue.get_nowait())
        if leftover:
            await self._flush(leftover)
