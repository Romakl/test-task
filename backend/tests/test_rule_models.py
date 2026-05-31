from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.rules.models import (
    Action,
    Condition,
    Destination,
    Match,
    Operator,
    Rule,
    RuleSet,
)


def _rule(**kw):
    return Rule(
        id=kw.get("id", "r1"),
        match=Match(conditions=[Condition(field="severity", op=Operator.GE, value=7)]),
        action=kw.get("action", Action.FORWARD),
        destination=kw.get("destination"),
    )


def test_invalid_regex_rejected():
    with pytest.raises(ValidationError):
        Condition(field="name", op=Operator.REGEX, value="(unclosed")


def test_invalid_cidr_rejected():
    with pytest.raises(ValidationError):
        Condition(field="filteripaddress", op=Operator.CIDR, value=["not-a-cidr"])


def test_in_requires_nonempty_list():
    with pytest.raises(ValidationError):
        Condition(field="filtertype", op=Operator.IN, value="ids")
    with pytest.raises(ValidationError):
        Condition(field="filtertype", op=Operator.IN, value=[])


def test_between_requires_two_numbers():
    with pytest.raises(ValidationError):
        Condition(field="severity", op=Operator.BETWEEN, value=[1])
    with pytest.raises(ValidationError):
        Condition(field="severity", op=Operator.BETWEEN, value=["a", "b"])


def test_numeric_op_requires_number():
    with pytest.raises(ValidationError):
        Condition(field="severity", op=Operator.GT, value="not-a-number")


def test_exists_needs_no_value():
    c = Condition(field="filtertype", op=Operator.EXISTS)
    assert c.value is None


def test_destination_only_on_forward():
    with pytest.raises(ValidationError):
        _rule(action=Action.DROP, destination=Destination(host="x", port=5140))


def test_bad_rule_id_rejected():
    with pytest.raises(ValidationError):
        _rule(id="has spaces!")


def test_duplicate_rule_ids_rejected():
    with pytest.raises(ValidationError):
        RuleSet(rules=[_rule(id="dup"), _rule(id="dup")])
