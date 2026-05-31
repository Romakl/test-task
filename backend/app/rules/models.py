from __future__ import annotations

import ipaddress
import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


KNOWN_FIELDS: tuple[str, ...] = (
    "eventid",
    "filterhostname",
    "filterid",
    "filteripaddress",
    "filternodename",
    "filterpriority",
    "filtertype",
    "notificationtime",
    "name",
    "severity",
)


class Operator(StrEnum):
    EQ = "eq"
    NE = "ne"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    REGEX = "regex"
    NOT_REGEX = "not_regex"
    CIDR = "cidr"
    NOT_CIDR = "not_cidr"
    GT = "gt"
    GE = "ge"
    LT = "lt"
    LE = "le"
    BETWEEN = "between"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


_NUMERIC_OPS = {Operator.GT, Operator.GE, Operator.LT, Operator.LE}
_REGEX_OPS = {Operator.REGEX, Operator.NOT_REGEX}
_NO_VALUE_OPS = {Operator.EXISTS, Operator.NOT_EXISTS}


class Condition(BaseModel):
    field: str = Field(min_length=1)
    op: Operator
    value: Any = None
    case_insensitive: bool = False

    @model_validator(mode="after")
    def _validate_value_for_op(self) -> Condition:
        op = self.op
        if op in _NO_VALUE_OPS:
            return self

        if op in _REGEX_OPS:
            if not isinstance(self.value, str):
                raise ValueError(f"operator '{op}' requires a string pattern")
            try:
                re.compile(self.value)
            except re.error as exc:
                raise ValueError(f"invalid regex: {exc}") from exc
            return self

        if op in {Operator.CIDR, Operator.NOT_CIDR}:
            networks = self.value if isinstance(self.value, list) else [self.value]
            for net in networks:
                try:
                    ipaddress.ip_network(str(net), strict=False)
                except ValueError as exc:
                    raise ValueError(f"invalid CIDR '{net}': {exc}") from exc
            return self

        if op in {Operator.IN, Operator.NOT_IN}:
            if not isinstance(self.value, list) or not self.value:
                raise ValueError(f"operator '{op}' requires a non-empty list")
            return self

        if op is Operator.BETWEEN:
            if not isinstance(self.value, list) or len(self.value) != 2:
                raise ValueError("operator 'between' requires [low, high]")
            try:
                _ = [float(self.value[0]), float(self.value[1])]
            except (TypeError, ValueError) as exc:
                raise ValueError("'between' bounds must be numeric") from exc
            return self

        if op in _NUMERIC_OPS:
            try:
                float(self.value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"operator '{op}' requires a numeric value") from exc
            return self

        if self.value is None:
            raise ValueError(f"operator '{op}' requires a value")
        return self


class Combinator(StrEnum):
    ALL = "all"
    ANY = "any"


class Match(BaseModel):
    combinator: Combinator = Combinator.ALL
    conditions: list[Condition] = Field(min_length=1)


class Action(StrEnum):
    FORWARD = "forward"
    DROP = "drop"


class Destination(BaseModel):
    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)


class Rule(BaseModel):
    id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9._-]+$")
    description: str = ""
    enabled: bool = True
    match: Match
    action: Action
    destination: Destination | None = None

    @model_validator(mode="after")
    def _destination_only_on_forward(self) -> Rule:
        if self.destination is not None and self.action is not Action.FORWARD:
            raise ValueError("destination is only valid on a 'forward' rule")
        return self


class RuleSet(BaseModel):
    default_policy: Action | None = None
    rules: list[Rule] = Field(default_factory=list)

    @field_validator("rules")
    @classmethod
    def _unique_ids(cls, rules: list[Rule]) -> list[Rule]:
        seen: set[str] = set()
        for rule in rules:
            if rule.id in seen:
                raise ValueError(f"duplicate rule id: {rule.id}")
            seen.add(rule.id)
        return rules
