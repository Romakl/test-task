from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_store
from app.rules.repository import AuditEntry
from app.rules.store import RuleStore


router = APIRouter(tags=["audit"])


@router.get("/api/audit", response_model=list[AuditEntry])
async def list_audit(
    limit: int = Query(default=100, ge=1, le=1000),
    store: RuleStore = Depends(get_store),
) -> list[AuditEntry]:
    return await store.list_audit(limit)
