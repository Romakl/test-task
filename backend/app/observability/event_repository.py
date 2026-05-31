from __future__ import annotations

import datetime as dt
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import EventRow
from app.observability.events_buffer import EventRecord


class EventRepository(Protocol):
    async def add_many(self, records: list[EventRecord]) -> None: ...

    async def recent(self, limit: int = 100) -> list[EventRecord]: ...


class InMemoryEventRepository:
    def __init__(self) -> None:
        self._events: list[EventRecord] = []

    async def add_many(self, records: list[EventRecord]) -> None:
        self._events.extend(records)

    async def recent(self, limit: int = 100) -> list[EventRecord]:
        return self._events[-limit:][::-1]


class SqlEventRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def add_many(self, records: list[EventRecord]) -> None:
        if not records:
            return
        async with self._session_factory() as session, session.begin():
            session.add_all([_to_row(record) for record in records])

    async def recent(self, limit: int = 100) -> list[EventRecord]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(EventRow).order_by(EventRow.id.desc()).limit(limit)
            )
            return [_to_record(row) for row in result.scalars().all()]


def _parse_ts(value: str) -> dt.datetime:
    try:
        return dt.datetime.fromisoformat(value)
    except ValueError:
        return dt.datetime.now(tz=dt.UTC)


def _to_row(record: EventRecord) -> EventRow:
    return EventRow(
        seq=record.seq,
        ts=_parse_ts(record.ts),
        source_ip=record.source_ip,
        source_port=record.source_port,
        size_bytes=record.size_bytes,
        parsed=record.parsed,
        parse_error=record.parse_error,
        action=record.action,
        matched_rule_id=record.matched_rule_id,
        reason=record.reason,
        destination=record.destination,
        name=record.fields.get("name"),
        severity=record.fields.get("severity"),
        fields=record.fields,
        raw_preview=record.raw_preview,
    )


def _to_record(row: EventRow) -> EventRecord:
    return EventRecord(
        seq=row.seq,
        ts=row.ts.isoformat(),
        source_ip=row.source_ip,
        source_port=row.source_port,
        size_bytes=row.size_bytes,
        parsed=row.parsed,
        parse_error=row.parse_error,
        action=row.action,
        matched_rule_id=row.matched_rule_id,
        reason=row.reason,
        destination=row.destination,
        fields=row.fields or {},
        raw_preview=row.raw_preview,
    )
