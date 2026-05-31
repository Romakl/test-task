from __future__ import annotations

from app.rules.engine import evaluate
from app.rules.models import (
    Action,
    Combinator,
    Condition,
    Match,
    Operator,
    Rule,
    RuleSet,
)
from tests.conftest import make_event


def _rule(conditions, action=Action.FORWARD, combinator=Combinator.ALL, **kw):
    return Rule(
        id=kw.get("id", "r1"),
        enabled=kw.get("enabled", True),
        match=Match(combinator=combinator, conditions=conditions),
        action=action,
        destination=kw.get("destination"),
    )


def _decide(event, rules, default=Action.FORWARD, default_policy=None):
    rs = RuleSet(rules=rules, default_policy=default_policy)
    return evaluate(event, rs, default)


def test_eq_and_ne():
    ev = make_event(filtertype="ids")
    assert (
        _decide(
            ev,
            [
                _rule(
                    [Condition(field="filtertype", op=Operator.EQ, value="ids")],
                    Action.DROP,
                )
            ],
        ).action
        is Action.DROP
    )
    assert (
        _decide(
            ev,
            [
                _rule(
                    [Condition(field="filtertype", op=Operator.NE, value="av")],
                    Action.DROP,
                )
            ],
        ).action
        is Action.DROP
    )


def test_in_and_not_in():
    ev = make_event(filtertype="ips")
    assert (
        _decide(
            ev,
            [
                _rule(
                    [
                        Condition(
                            field="filtertype", op=Operator.IN, value=["ids", "ips"]
                        )
                    ],
                    Action.DROP,
                )
            ],
        ).action
        is Action.DROP
    )
    assert (
        _decide(
            ev,
            [
                _rule(
                    [Condition(field="filtertype", op=Operator.NOT_IN, value=["av"])],
                    Action.DROP,
                )
            ],
        ).action
        is Action.DROP
    )


def test_contains():
    ev = make_event(name="Brute force login attempt")
    assert (
        _decide(
            ev,
            [
                _rule(
                    [
                        Condition(
                            field="name",
                            op=Operator.CONTAINS,
                            value="brute",
                            case_insensitive=True,
                        )
                    ],
                    Action.DROP,
                )
            ],
        ).action
        is Action.DROP
    )
    assert (
        _decide(
            ev,
            [
                _rule(
                    [
                        Condition(
                            field="name", op=Operator.NOT_CONTAINS, value="malware"
                        )
                    ],
                    Action.DROP,
                )
            ],
        ).action
        is Action.DROP
    )


def test_regex():
    ev = make_event(name="Port scan detected")
    assert (
        _decide(
            ev,
            [
                _rule(
                    [Condition(field="name", op=Operator.REGEX, value=r"^Port scan")],
                    Action.DROP,
                )
            ],
        ).action
        is Action.DROP
    )
    assert (
        _decide(
            ev,
            [
                _rule(
                    [Condition(field="name", op=Operator.NOT_REGEX, value=r"^Malware")],
                    Action.DROP,
                )
            ],
        ).action
        is Action.DROP
    )


def test_cidr_ipv4():
    ev = make_event(filteripaddress="10.1.2.3")
    assert (
        _decide(
            ev,
            [
                _rule(
                    [
                        Condition(
                            field="filteripaddress",
                            op=Operator.CIDR,
                            value=["10.0.0.0/8"],
                        )
                    ],
                    Action.DROP,
                )
            ],
        ).action
        is Action.DROP
    )
    ev2 = make_event(filteripaddress="8.8.8.8")
    assert (
        _decide(
            ev2,
            [
                _rule(
                    [
                        Condition(
                            field="filteripaddress",
                            op=Operator.CIDR,
                            value=["10.0.0.0/8"],
                        )
                    ],
                    Action.DROP,
                )
            ],
        ).action
        is Action.FORWARD
    )


def test_cidr_invalid_ip_is_false():
    ev = make_event(filteripaddress="not-an-ip")
    d = _decide(
        ev,
        [
            _rule(
                [
                    Condition(
                        field="filteripaddress", op=Operator.CIDR, value=["10.0.0.0/8"]
                    )
                ],
                Action.DROP,
            )
        ],
        default=Action.FORWARD,
    )
    assert d.action is Action.FORWARD


def test_numeric_operators():
    ev = make_event(severity="8")
    assert (
        _decide(
            ev,
            [
                _rule(
                    [Condition(field="severity", op=Operator.GE, value=7)], Action.DROP
                )
            ],
        ).action
        is Action.DROP
    )
    assert (
        _decide(
            ev,
            [
                _rule(
                    [Condition(field="severity", op=Operator.LT, value=5)], Action.DROP
                )
            ],
        ).action
        is Action.FORWARD
    )


def test_between():
    ev = make_event(filterpriority="5")
    assert (
        _decide(
            ev,
            [
                _rule(
                    [
                        Condition(
                            field="filterpriority", op=Operator.BETWEEN, value=[4, 6]
                        )
                    ],
                    Action.DROP,
                )
            ],
        ).action
        is Action.DROP
    )


def test_severity_enum_word_coercion():
    ev = make_event(severity="High")
    assert (
        _decide(
            ev,
            [
                _rule(
                    [Condition(field="severity", op=Operator.GE, value=7)], Action.DROP
                )
            ],
        ).action
        is Action.DROP
    )


def test_exists_and_not_exists():
    ev = make_event()
    assert (
        _decide(
            ev,
            [_rule([Condition(field="filtertype", op=Operator.EXISTS)], Action.DROP)],
        ).action
        is Action.DROP
    )
    assert (
        _decide(
            ev,
            [_rule([Condition(field="missing", op=Operator.NOT_EXISTS)], Action.DROP)],
        ).action
        is Action.DROP
    )


def test_missing_field_does_not_match():
    ev = make_event()
    d = _decide(
        ev,
        [_rule([Condition(field="missing", op=Operator.EQ, value="x")], Action.DROP)],
        default=Action.FORWARD,
    )
    assert d.action is Action.FORWARD


def test_combinator_all_vs_any():
    ev = make_event(filtertype="ids", severity="2")
    both = [
        Condition(field="filtertype", op=Operator.EQ, value="ids"),
        Condition(field="severity", op=Operator.GE, value=7),
    ]
    assert (
        _decide(ev, [_rule(both, Action.DROP, Combinator.ALL)]).action is Action.FORWARD
    )
    assert _decide(ev, [_rule(both, Action.DROP, Combinator.ANY)]).action is Action.DROP


def test_first_match_wins():
    ev = make_event(filtertype="ids")
    rules = [
        _rule(
            [Condition(field="filtertype", op=Operator.EQ, value="ids")],
            Action.DROP,
            id="first",
        ),
        _rule(
            [Condition(field="filtertype", op=Operator.EQ, value="ids")],
            Action.FORWARD,
            id="second",
        ),
    ]
    d = _decide(ev, rules)
    assert d.action is Action.DROP
    assert d.matched_rule_id == "first"


def test_disabled_rule_skipped():
    ev = make_event(filtertype="ids")
    rules = [
        _rule(
            [Condition(field="filtertype", op=Operator.EQ, value="ids")],
            Action.DROP,
            enabled=False,
        )
    ]
    assert _decide(ev, rules, default=Action.FORWARD).action is Action.FORWARD


def test_default_policy_and_override():
    ev = make_event()
    assert _decide(ev, [], default=Action.DROP).action is Action.DROP
    assert (
        _decide(ev, [], default=Action.DROP, default_policy=Action.FORWARD).action
        is Action.FORWARD
    )


def test_destination_passthrough():
    from app.rules.models import Destination

    ev = make_event(severity="9")
    rule = _rule(
        [Condition(field="severity", op=Operator.GE, value=9)],
        Action.FORWARD,
        destination=Destination(host="elk-crit", port=5141),
    )
    d = _decide(ev, [rule])
    assert d.destination_host == "elk-crit"
    assert d.destination_port == 5141
