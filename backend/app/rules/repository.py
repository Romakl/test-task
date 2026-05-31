from __future__ import annotations

import datetime as dt
from typing import Protocol

from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import AppSettingRow, AuditRow, RuleRow
from app.rules.models import Action, Rule, RuleSet


_DEFAULT_POLICY_KEY = "default_policy"


def _now_iso() -> str:
    return dt.datetime.now(tz=dt.UTC).isoformat()


class AuditEntry(BaseModel):
    ts: str
    action: str
    rule_id: str | None = None
    detail: str | None = None


class RuleRepository(Protocol):
    async def load_ruleset(self) -> RuleSet: ...

    async def save_ruleset(self, ruleset: RuleSet) -> None: ...

    async def add_audit(
        self, action: str, rule_id: str | None = None, detail: str | None = None
    ) -> None: ...

    async def list_audit(self, limit: int = 100) -> list[AuditEntry]: ...


class InMemoryRuleRepository:
    def __init__(self) -> None:
        self._ruleset = RuleSet()
        self._audit: list[AuditEntry] = []

    async def load_ruleset(self) -> RuleSet:
        return self._ruleset

    async def save_ruleset(self, ruleset: RuleSet) -> None:
        self._ruleset = ruleset

    async def add_audit(
        self, action: str, rule_id: str | None = None, detail: str | None = None
    ) -> None:
        self._audit.append(
            AuditEntry(ts=_now_iso(), action=action, rule_id=rule_id, detail=detail)
        )

    async def list_audit(self, limit: int = 100) -> list[AuditEntry]:
        return self._audit[-limit:][::-1]


class SqlRuleRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def load_ruleset(self) -> RuleSet:
        async with self._session_factory() as session:
            result = await session.execute(select(RuleRow).order_by(RuleRow.position))
            rules = [Rule.model_validate(row.data) for row in result.scalars().all()]
            policy_row = await session.get(AppSettingRow, _DEFAULT_POLICY_KEY)
            policy = (
                Action(policy_row.value)
                if policy_row is not None and policy_row.value
                else None
            )
            return RuleSet(default_policy=policy, rules=rules)

    async def save_ruleset(self, ruleset: RuleSet) -> None:
        async with self._session_factory() as session, session.begin():
            await session.execute(delete(RuleRow))
            for position, rule in enumerate(ruleset.rules):
                session.add(
                    RuleRow(
                        id=rule.id,
                        position=position,
                        enabled=rule.enabled,
                        action=rule.action.value,
                        data=rule.model_dump(mode="json"),
                    )
                )
            value = (
                ruleset.default_policy.value
                if ruleset.default_policy is not None
                else None
            )
            policy_row = await session.get(AppSettingRow, _DEFAULT_POLICY_KEY)
            if policy_row is None:
                session.add(AppSettingRow(key=_DEFAULT_POLICY_KEY, value=value))
            else:
                policy_row.value = value

    async def add_audit(
        self, action: str, rule_id: str | None = None, detail: str | None = None
    ) -> None:
        async with self._session_factory() as session, session.begin():
            session.add(AuditRow(action=action, rule_id=rule_id, detail=detail))

    async def list_audit(self, limit: int = 100) -> list[AuditEntry]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuditRow).order_by(AuditRow.id.desc()).limit(limit)
            )
            return [
                AuditEntry(
                    ts=row.ts.isoformat(),
                    action=row.action,
                    rule_id=row.rule_id,
                    detail=row.detail,
                )
                for row in result.scalars().all()
            ]
