from __future__ import annotations

import pytest

from app.rules.models import Action, Condition, Match, Operator, Rule, RuleSet
from app.rules.repository import InMemoryRuleRepository
from app.rules.store import RuleNotFoundError, RuleStore, seed_from_file


def _rule(rule_id: str, action: Action = Action.FORWARD) -> Rule:
    return Rule(
        id=rule_id,
        match=Match(conditions=[Condition(field="severity", op=Operator.GE, value=7)]),
        action=action,
    )


def _store() -> RuleStore:
    return RuleStore(InMemoryRuleRepository())


async def test_load_empty():
    store = _store()
    rs = await store.load()
    assert rs.rules == []


async def test_add_persists_via_repository():
    repo = InMemoryRuleRepository()
    store = RuleStore(repo)
    await store.load()
    await store.add_rule(_rule("a"))
    assert store.get_rule("a").action is Action.FORWARD

    reloaded = RuleStore(repo)
    await reloaded.load()
    assert reloaded.get_rule("a").id == "a"


async def test_update_and_delete():
    store = _store()
    await store.add_rule(_rule("a"))
    await store.update_rule("a", _rule("a", Action.DROP))
    assert store.get_rule("a").action is Action.DROP
    await store.delete_rule("a")
    with pytest.raises(RuleNotFoundError):
        store.get_rule("a")


async def test_add_duplicate_raises():
    store = _store()
    await store.add_rule(_rule("dup"))
    with pytest.raises(ValueError, match="already exists"):
        await store.add_rule(_rule("dup"))


async def test_delete_missing_raises():
    store = _store()
    with pytest.raises(RuleNotFoundError):
        await store.delete_rule("nope")


async def test_reorder():
    store = _store()
    for rid in ("a", "b", "c"):
        await store.add_rule(_rule(rid))
    await store.reorder(["c", "a", "b"])
    assert [r.id for r in store.ruleset.rules] == ["c", "a", "b"]


async def test_reorder_rejects_wrong_set():
    store = _store()
    await store.add_rule(_rule("a"))
    with pytest.raises(ValueError, match="exactly the existing ids"):
        await store.reorder(["a", "b"])


async def test_replace_all_persists():
    repo = InMemoryRuleRepository()
    store = RuleStore(repo)
    await store.replace_all(RuleSet(default_policy=Action.DROP, rules=[_rule("x")]))
    reloaded = RuleStore(repo)
    await reloaded.load()
    assert reloaded.ruleset.default_policy is Action.DROP
    assert reloaded.get_rule("x").id == "x"


async def test_set_default_policy():
    store = _store()
    await store.set_default_policy(Action.DROP)
    assert store.ruleset.default_policy is Action.DROP


async def test_audit_recorded_newest_first():
    store = _store()
    await store.add_rule(_rule("a"))
    await store.update_rule("a", _rule("a", Action.DROP))
    entries = await store.list_audit()
    actions = [e.action for e in entries]
    assert "rule.added" in actions
    assert "rule.updated" in actions
    assert entries[0].action == "rule.updated"


async def test_seed_from_file(tmp_path):
    path = tmp_path / "seed.yaml"
    path.write_text(
        "default_policy: drop\n"
        "rules:\n"
        "  - id: s1\n"
        "    action: forward\n"
        "    match:\n"
        "      conditions:\n"
        "        - field: severity\n"
        "          op: ge\n"
        "          value: 7\n"
    )
    store = _store()
    assert await seed_from_file(store, path) == 1
    assert store.get_rule("s1").id == "s1"
    assert store.ruleset.default_policy is Action.DROP
    assert await seed_from_file(store, path) == 0
