from __future__ import annotations

from pydantic import BaseModel, Field

from app.rules.engine import Decision
from app.rules.models import Action


class ReorderRequest(BaseModel):
    order: list[str] = Field(description="Rule ids in the desired evaluation order")


class DefaultPolicyUpdate(BaseModel):
    default_policy: Action


class DryRunRequest(BaseModel):
    raw: str = Field(
        min_length=1,
        max_length=65535,
        description="A raw CEF/Syslog line to evaluate against the live ruleset",
    )


class DryRunResponse(BaseModel):
    parsed: bool
    parse_error: str | None = None
    event: dict[str, str] | None = None
    decision: Decision | None = None
    would_forward_to: str | None = None


class HealthResponse(BaseModel):
    status: str
    app: str
    env: str
    uptime_seconds: float
    listen: str
    default_forward_target: str
    rules_count: int
    default_policy: str
    auth_required: bool
    database_ok: bool
