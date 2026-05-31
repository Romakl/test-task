from __future__ import annotations

import ipaddress
import re
from functools import lru_cache

from pydantic import BaseModel

from app.cef.models import CefEvent
from app.rules.models import (
    Action,
    Combinator,
    Condition,
    Match,
    Operator,
    Rule,
    RuleSet,
)


class Decision(BaseModel):
    action: Action
    matched_rule_id: str | None = None
    matched_rule_description: str | None = None
    destination_host: str | None = None
    destination_port: int | None = None
    reason: str


@lru_cache(maxsize=512)
def _compile(pattern: str, ignore_case: bool) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE if ignore_case else 0)


_SEVERITY_WORDS: dict[str, float] = {
    "unknown": 0.0,
    "low": 2.0,
    "medium": 5.0,
    "high": 8.0,
    "very-high": 10.0,
    "very high": 10.0,
}


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return _SEVERITY_WORDS.get(value.strip().lower())


def _norm(value: str, ignore_case: bool) -> str:
    return value.lower() if ignore_case else value


def _eval_condition(cond: Condition, event: CefEvent) -> bool:
    field_value = event.get_field(cond.field)
    op = cond.op

    if op is Operator.EXISTS:
        return field_value not in (None, "")
    if op is Operator.NOT_EXISTS:
        return field_value in (None, "")

    if field_value is None:
        return False

    ci = cond.case_insensitive

    if op is Operator.EQ:
        return _norm(field_value, ci) == _norm(str(cond.value), ci)
    if op is Operator.NE:
        return _norm(field_value, ci) != _norm(str(cond.value), ci)
    if op is Operator.CONTAINS:
        return _norm(str(cond.value), ci) in _norm(field_value, ci)
    if op is Operator.NOT_CONTAINS:
        return _norm(str(cond.value), ci) not in _norm(field_value, ci)
    if op is Operator.IN:
        candidates = {_norm(str(v), ci) for v in cond.value}
        return _norm(field_value, ci) in candidates
    if op is Operator.NOT_IN:
        candidates = {_norm(str(v), ci) for v in cond.value}
        return _norm(field_value, ci) not in candidates
    if op is Operator.REGEX:
        return _compile(str(cond.value), ci).search(field_value) is not None
    if op is Operator.NOT_REGEX:
        return _compile(str(cond.value), ci).search(field_value) is None

    if op in (Operator.CIDR, Operator.NOT_CIDR):
        try:
            ip = ipaddress.ip_address(field_value.strip())
        except ValueError:
            return False
        nets = cond.value if isinstance(cond.value, list) else [cond.value]
        contained = any(ip in ipaddress.ip_network(str(n), strict=False) for n in nets)
        return contained if op is Operator.CIDR else not contained

    if op in (Operator.GT, Operator.GE, Operator.LT, Operator.LE):
        left = _to_float(field_value)
        right = _to_float(str(cond.value))
        if left is None or right is None:
            return False
        if op is Operator.GT:
            return left > right
        if op is Operator.GE:
            return left >= right
        if op is Operator.LT:
            return left < right
        return left <= right

    if op is Operator.BETWEEN:
        left = _to_float(field_value)
        if left is None:
            return False
        low, high = float(cond.value[0]), float(cond.value[1])
        return low <= left <= high

    return False


def _eval_match(match: Match, event: CefEvent) -> bool:
    checks = (_eval_condition(c, event) for c in match.conditions)
    if match.combinator is Combinator.ANY:
        return any(checks)
    return all(checks)


def _matches(rule: Rule, event: CefEvent) -> bool:
    return rule.enabled and _eval_match(rule.match, event)


def evaluate(
    event: CefEvent,
    ruleset: RuleSet,
    default_policy: Action,
) -> Decision:
    for rule in ruleset.rules:
        if _matches(rule, event):
            dest = rule.destination
            return Decision(
                action=rule.action,
                matched_rule_id=rule.id,
                matched_rule_description=rule.description or None,
                destination_host=dest.host if dest else None,
                destination_port=dest.port if dest else None,
                reason=f"matched rule '{rule.id}' -> {rule.action}",
            )

    policy = ruleset.default_policy or default_policy
    return Decision(
        action=policy,
        matched_rule_id=None,
        reason=f"no rule matched; default policy -> {policy}",
    )
