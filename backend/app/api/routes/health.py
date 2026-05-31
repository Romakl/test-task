from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text

from app.api.deps import get_metrics, get_settings, get_store
from app.api.schemas import HealthResponse
from app.core.config import Settings
from app.observability.metrics import Metrics
from app.rules.store import RuleStore


router = APIRouter(tags=["health"])


async def _database_ok(request: Request) -> bool:
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        return False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        return False
    return True


@router.get("/health", response_model=HealthResponse)
async def health(
    request: Request,
    settings: Settings = Depends(get_settings),
    store: RuleStore = Depends(get_store),
    metrics: Metrics = Depends(get_metrics),
) -> HealthResponse:
    ruleset = store.ruleset
    policy = ruleset.default_policy or settings.DEFAULT_POLICY
    return HealthResponse(
        status="ok",
        app=settings.APP_NAME,
        env=settings.APP_ENV,
        uptime_seconds=round(metrics.uptime_seconds, 1),
        listen=f"udp://{settings.LISTEN_HOST}:{settings.LISTEN_PORT}",
        default_forward_target=f"{settings.ELK_HOST}:{settings.ELK_PORT}",
        rules_count=len(ruleset.rules),
        default_policy=str(policy),
        auth_required=bool(settings.API_TOKEN),
        database_ok=await _database_ok(request),
    )
