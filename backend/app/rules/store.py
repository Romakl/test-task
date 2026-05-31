from __future__ import annotations

import asyncio
from pathlib import Path

import yaml

from app.core.logging import get_logger
from app.rules.models import Action, Rule, RuleSet
from app.rules.repository import AuditEntry, RuleRepository


logger = get_logger("cefproxy.rules")
audit = get_logger("cefproxy.audit")


class RuleNotFoundError(KeyError):
    pass


class RuleStore:
    def __init__(self, repository: RuleRepository) -> None:
        self._repository = repository
        self._ruleset = RuleSet()
        self._lock = asyncio.Lock()

    async def load(self) -> RuleSet:
        self._ruleset = await self._repository.load_ruleset()
        logger.info(
            "loaded %d rule(s) (default_policy=%s)",
            len(self._ruleset.rules),
            self._ruleset.default_policy,
        )
        return self._ruleset

    @property
    def ruleset(self) -> RuleSet:
        return self._ruleset

    def get_rule(self, rule_id: str) -> Rule:
        for rule in self._ruleset.rules:
            if rule.id == rule_id:
                return rule
        raise RuleNotFoundError(rule_id)

    async def _commit(
        self, ruleset: RuleSet, action: str, rule_id: str | None, detail: str | None
    ) -> None:
        await self._repository.save_ruleset(ruleset)
        self._ruleset = ruleset
        await self._repository.add_audit(action, rule_id, detail)
        audit.info("%s id=%s %s", action, rule_id or "-", detail or "")

    async def replace_all(self, ruleset: RuleSet) -> RuleSet:
        async with self._lock:
            await self._commit(
                ruleset, "ruleset.replaced", None, f"{len(ruleset.rules)} rule(s)"
            )
        return self._ruleset

    async def add_rule(self, rule: Rule) -> Rule:
        async with self._lock:
            if any(r.id == rule.id for r in self._ruleset.rules):
                raise ValueError(f"rule id already exists: {rule.id}")
            new = self._ruleset.model_copy(
                update={"rules": [*self._ruleset.rules, rule]}
            )
            await self._commit(new, "rule.added", rule.id, f"action={rule.action}")
        return rule

    async def update_rule(self, rule_id: str, rule: Rule) -> Rule:
        async with self._lock:
            rules = list(self._ruleset.rules)
            for i, existing in enumerate(rules):
                if existing.id == rule_id:
                    rules[i] = rule
                    new = self._ruleset.model_copy(update={"rules": rules})
                    await self._commit(new, "rule.updated", rule_id, None)
                    return rule
            raise RuleNotFoundError(rule_id)

    async def delete_rule(self, rule_id: str) -> None:
        async with self._lock:
            rules = [r for r in self._ruleset.rules if r.id != rule_id]
            if len(rules) == len(self._ruleset.rules):
                raise RuleNotFoundError(rule_id)
            new = self._ruleset.model_copy(update={"rules": rules})
            await self._commit(new, "rule.deleted", rule_id, None)

    async def reorder(self, ordered_ids: list[str]) -> RuleSet:
        async with self._lock:
            by_id = {r.id: r for r in self._ruleset.rules}
            if set(ordered_ids) != set(by_id):
                raise ValueError("reorder list must contain exactly the existing ids")
            new = self._ruleset.model_copy(
                update={"rules": [by_id[i] for i in ordered_ids]}
            )
            await self._commit(new, "rules.reordered", None, ",".join(ordered_ids))
        return self._ruleset

    async def set_default_policy(self, policy: Action) -> RuleSet:
        async with self._lock:
            new = self._ruleset.model_copy(update={"default_policy": policy})
            await self._commit(new, "default_policy.set", None, str(policy))
        return self._ruleset

    async def list_audit(self, limit: int = 100) -> list[AuditEntry]:
        return await self._repository.list_audit(limit)


async def seed_from_file(store: RuleStore, seed_path: str | Path) -> int:
    if store.ruleset.rules:
        return 0
    path = Path(seed_path)
    if not path.exists():
        return 0
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    ruleset = RuleSet.model_validate(raw)
    if not ruleset.rules:
        return 0
    await store.replace_all(ruleset)
    logger.info("seeded %d rule(s) from %s", len(ruleset.rules), path)
    return len(ruleset.rules)
