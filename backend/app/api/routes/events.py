from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Query, Request
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_buffer, get_event_repository
from app.observability.event_repository import EventRepository
from app.observability.events_buffer import EventBuffer, EventRecord


router = APIRouter(tags=["events"])


@router.get("/api/events", response_model=list[EventRecord])
def recent_events(
    limit: int = Query(default=100, ge=1, le=1000),
    buffer: EventBuffer = Depends(get_buffer),
) -> list[EventRecord]:
    return buffer.recent(limit=limit)


@router.get("/api/events/history", response_model=list[EventRecord])
async def event_history(
    limit: int = Query(default=100, ge=1, le=1000),
    repository: EventRepository = Depends(get_event_repository),
) -> list[EventRecord]:
    return await repository.recent(limit=limit)


@router.get("/api/events/stream")
async def stream_events(
    request: Request,
    buffer: EventBuffer = Depends(get_buffer),
) -> EventSourceResponse:
    queue = buffer.subscribe()

    async def event_generator() -> AsyncIterator[dict[str, str]]:
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    record = await asyncio.wait_for(queue.get(), timeout=15.0)
                except TimeoutError:
                    yield {"event": "ping", "data": "{}"}
                    continue
                yield {"event": "decision", "data": record.model_dump_json()}
        finally:
            buffer.unsubscribe(queue)

    return EventSourceResponse(event_generator())
