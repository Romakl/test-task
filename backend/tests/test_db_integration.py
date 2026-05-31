from __future__ import annotations

import os

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.db.base import Base
from app.db.session import create_session_factory
from app.observability.event_repository import SqlEventRepository
from app.observability.events_buffer import EventRecord
from app.rules.models import Action, Condition, Match, Operator, Rule, RuleSet
from app.rules.repository import SqlRuleRepository


pytestmark = pytest.mark.integration

DB_URL = os.environ.get("TEST_DATABASE_URL")
_REASON = "set TEST_DATABASE_URL to run the Postgres integration tests"


async def _fresh_engine() -> AsyncEngine:
    engine = create_async_engine(DB_URL or "")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    return engine


@pytest.mark.skipif(not DB_URL, reason=_REASON)
async def test_sql_rule_repository_roundtrip():
    engine = await _fresh_engine()
    try:
        repo = SqlRuleRepository(create_session_factory(engine))
        ruleset = RuleSet(
            default_policy=Action.DROP,
            rules=[
                Rule(
                    id="a",
                    match=Match(
                        conditions=[
                            Condition(field="severity", op=Operator.GE, value=7)
                        ]
                    ),
                    action=Action.FORWARD,
                )
            ],
        )
        await repo.save_ruleset(ruleset)
        loaded = await repo.load_ruleset()
        assert loaded.default_policy is Action.DROP
        assert [r.id for r in loaded.rules] == ["a"]

        await repo.add_audit("rule.added", "a", "action=forward")
        entries = await repo.list_audit()
        assert entries[0].action == "rule.added"
    finally:
        await engine.dispose()


@pytest.mark.skipif(not DB_URL, reason=_REASON)
async def test_sql_event_repository_roundtrip():
    engine = await _fresh_engine()
    try:
        repo = SqlEventRepository(create_session_factory(engine))
        record = EventRecord(
            seq=1,
            ts="2024-01-01T00:00:00+00:00",
            source_ip="10.0.0.1",
            source_port=5514,
            size_bytes=42,
            parsed=True,
            action="forward",
            reason="matched",
            fields={"name": "Worm", "severity": "9"},
            raw_preview="CEF:0|x|y|1|1|Worm|9|",
        )
        await repo.add_many([record])
        recent = await repo.recent(10)
        assert len(recent) == 1
        assert recent[0].fields["name"] == "Worm"
    finally:
        await engine.dispose()
