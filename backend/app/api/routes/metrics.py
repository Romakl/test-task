from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from app.api.deps import get_metrics
from app.observability.metrics import Metrics


router = APIRouter(tags=["metrics"])


@router.get("/api/stats")
def stats(metrics: Metrics = Depends(get_metrics)) -> dict[str, object]:
    return metrics.snapshot()


@router.get("/metrics", response_class=PlainTextResponse)
def prometheus(metrics: Metrics = Depends(get_metrics)) -> str:
    return metrics.prometheus()
