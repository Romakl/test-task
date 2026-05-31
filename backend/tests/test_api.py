from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.rules.repository import InMemoryRuleRepository
from app.rules.store import RuleStore
from tests.conftest import build_app


def _rule_body(rule_id="drop-ids", action="drop"):
    return {
        "id": rule_id,
        "description": "test",
        "action": action,
        "match": {"conditions": [{"field": "filtertype", "op": "eq", "value": "ids"}]},
    }


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["rules_count"] == 0


def test_metrics_endpoints(client):
    assert client.get("/api/stats").status_code == 200
    prom = client.get("/metrics")
    assert prom.status_code == 200
    assert "cefproxy_forwarded_total" in prom.text


def test_rule_crud_flow(client):
    assert client.get("/api/rules").json()["rules"] == []

    created = client.post("/api/rules", json=_rule_body())
    assert created.status_code == 201

    assert client.post("/api/rules", json=_rule_body()).status_code == 409

    got = client.get("/api/rules/drop-ids")
    assert got.status_code == 200 and got.json()["action"] == "drop"

    upd = client.put("/api/rules/drop-ids", json=_rule_body(action="forward"))
    assert upd.status_code == 200 and upd.json()["action"] == "forward"

    assert client.delete("/api/rules/drop-ids").status_code == 204
    assert client.get("/api/rules/drop-ids").status_code == 404


def test_invalid_rule_rejected(client):
    bad = {
        "id": "bad",
        "action": "forward",
        "match": {
            "conditions": [{"field": "name", "op": "regex", "value": "(unclosed"}]
        },
    }
    assert client.post("/api/rules", json=bad).status_code == 422


def test_reorder(client):
    for rid in ("a", "b", "c"):
        client.post("/api/rules", json=_rule_body(rule_id=rid))
    r = client.post("/api/rules/reorder", json={"order": ["c", "b", "a"]})
    assert r.status_code == 200
    assert [x["id"] for x in r.json()["rules"]] == ["c", "b", "a"]


def test_dry_run(client):
    client.post("/api/rules", json=_rule_body())
    cef = "CEF:0|Acme|Engine|1.0|100|Worm|9|filtertype=ids"
    r = client.post("/api/dry-run", json={"raw": cef})
    body = r.json()
    assert body["parsed"] is True
    assert body["decision"]["action"] == "drop"
    assert body["event"]["filtertype"] == "ids"


def test_dry_run_parse_error(client):
    r = client.post("/api/dry-run", json={"raw": "not cef"})
    assert r.json()["parsed"] is False


def test_set_default_policy(client):
    r = client.put(
        "/api/rules/settings/default-policy", json={"default_policy": "drop"}
    )
    assert r.status_code == 200
    assert r.json()["default_policy"] == "drop"


def _authed_client(token="secret"):
    settings = Settings(API_TOKEN=token)
    store = RuleStore(InMemoryRuleRepository())
    return TestClient(build_app(settings, store))


def test_auth_required_for_mutations():
    c = _authed_client()
    assert c.post("/api/rules", json=_rule_body()).status_code == 401
    assert (
        c.post(
            "/api/rules", json=_rule_body(), headers={"Authorization": "Bearer nope"}
        ).status_code
        == 401
    )
    assert c.get("/api/rules").status_code == 200
    ok = c.post(
        "/api/rules", json=_rule_body(), headers={"Authorization": "Bearer secret"}
    )
    assert ok.status_code == 201


def test_blank_api_token_normalized_to_none():
    s = Settings(API_TOKEN="   ")
    assert s.API_TOKEN is None


def test_audit_endpoint_records_changes(client):
    client.post("/api/rules", json=_rule_body())
    entries = client.get("/api/audit").json()
    assert len(entries) >= 1
    assert entries[0]["action"] == "rule.added"


def test_event_history_endpoint(client):
    r = client.get("/api/events/history")
    assert r.status_code == 200
    assert r.json() == []


def test_cors_allows_configured_origin_and_blocks_others():
    from app.main import create_app

    c = TestClient(create_app())
    allowed = c.get("/", headers={"Origin": "http://localhost:3000"})
    assert allowed.status_code == 200
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"

    blocked = c.get("/", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in blocked.headers
