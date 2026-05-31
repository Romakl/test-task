from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_settings, get_store, require_auth
from app.api.schemas import (
    DefaultPolicyUpdate,
    DryRunRequest,
    DryRunResponse,
    ReorderRequest,
)
from app.cef.parser import CefParseError, parse_cef
from app.core.config import Settings
from app.rules.engine import evaluate
from app.rules.models import Action, Rule, RuleSet
from app.rules.store import RuleNotFoundError, RuleStore


router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("", response_model=RuleSet)
def list_rules(store: RuleStore = Depends(get_store)) -> RuleSet:
    return store.ruleset


@router.get("/{rule_id}", response_model=Rule)
def get_rule(rule_id: str, store: RuleStore = Depends(get_store)) -> Rule:
    try:
        return store.get_rule(rule_id)
    except RuleNotFoundError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"no such rule: {rule_id}"
        ) from exc


@router.post("", response_model=Rule, status_code=status.HTTP_201_CREATED)
async def create_rule(
    rule: Rule,
    store: RuleStore = Depends(get_store),
    _: None = Depends(require_auth),
) -> Rule:
    try:
        return await store.add_rule(rule)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.put("/{rule_id}", response_model=Rule)
async def update_rule(
    rule_id: str,
    rule: Rule,
    store: RuleStore = Depends(get_store),
    _: None = Depends(require_auth),
) -> Rule:
    try:
        return await store.update_rule(rule_id, rule)
    except RuleNotFoundError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"no such rule: {rule_id}"
        ) from exc


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: str,
    store: RuleStore = Depends(get_store),
    _: None = Depends(require_auth),
) -> None:
    try:
        await store.delete_rule(rule_id)
    except RuleNotFoundError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"no such rule: {rule_id}"
        ) from exc


@router.post("/reorder", response_model=RuleSet)
async def reorder_rules(
    body: ReorderRequest,
    store: RuleStore = Depends(get_store),
    _: None = Depends(require_auth),
) -> RuleSet:
    try:
        return await store.reorder(body.order)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.put("/settings/default-policy", response_model=RuleSet)
async def set_default_policy(
    body: DefaultPolicyUpdate,
    store: RuleStore = Depends(get_store),
    _: None = Depends(require_auth),
) -> RuleSet:
    return await store.set_default_policy(body.default_policy)


dry_run_router = APIRouter(tags=["rules"])


@dry_run_router.post("/api/dry-run", response_model=DryRunResponse)
def dry_run(
    body: DryRunRequest,
    store: RuleStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> DryRunResponse:
    try:
        event = parse_cef(body.raw)
    except CefParseError as exc:
        return DryRunResponse(parsed=False, parse_error=str(exc))

    decision = evaluate(event, store.ruleset, Action(settings.DEFAULT_POLICY))
    target = None
    if decision.action is Action.FORWARD:
        host = decision.destination_host or settings.ELK_HOST
        port = decision.destination_port or settings.ELK_PORT
        target = f"{host}:{port}"
    return DryRunResponse(
        parsed=True,
        event=event.as_flat_dict(),
        decision=decision,
        would_forward_to=target,
    )
