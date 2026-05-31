from __future__ import annotations

import hmac

from fastapi import Depends, Header, HTTPException, Request, status

from app.core.config import Settings
from app.observability.event_repository import EventRepository
from app.observability.events_buffer import EventBuffer
from app.observability.metrics import Metrics
from app.rules.store import RuleStore


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_store(request: Request) -> RuleStore:
    return request.app.state.store


def get_metrics(request: Request) -> Metrics:
    return request.app.state.metrics


def get_buffer(request: Request) -> EventBuffer:
    return request.app.state.buffer


def get_event_repository(request: Request) -> EventRepository:
    return request.app.state.event_repository


def require_auth(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.API_TOKEN:
        return
    expected = f"Bearer {settings.API_TOKEN}"
    if not hmac.compare_digest(authorization or "", expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing or invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
