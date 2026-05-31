from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import audit, events, health, metrics, rules
from app.cef.models import CefEvent
from app.core.config import Settings
from app.observability.event_repository import InMemoryEventRepository
from app.observability.events_buffer import EventBuffer
from app.observability.metrics import Metrics
from app.rules.repository import InMemoryRuleRepository
from app.rules.store import RuleStore


def make_event(**overrides: str) -> CefEvent:
    base = {
        "raw": "CEF:0|Acme|FilterEngine|1.0|1001|Port scan detected|8|",
        "cef_version": "0",
        "device_vendor": "Acme",
        "device_product": "FilterEngine",
        "device_version": "1.0",
        "signature_id": "1001",
        "name": "Port scan detected",
        "severity": "8",
    }
    extensions = {
        "eventid": "1001",
        "filterhostname": "sensor-a",
        "filterid": "7",
        "filteripaddress": "10.0.0.5",
        "filternodename": "node-1",
        "filterpriority": "9",
        "filtertype": "ids",
        "notificationtime": "1700000000000",
    }
    for key, value in overrides.items():
        if key in base:
            base[key] = value
        else:
            extensions[key] = value
    return CefEvent(extensions=extensions, **base)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        ELK_HOST="127.0.0.1",
        ELK_PORT=5140,
        DEFAULT_POLICY="forward",
        API_TOKEN=None,
        LOG_PER_EVENT=False,
    )


@pytest.fixture
def store() -> RuleStore:
    return RuleStore(InMemoryRuleRepository())


def build_app(settings: Settings, store: RuleStore) -> FastAPI:
    app = FastAPI()
    app.include_router(health.router)
    app.include_router(metrics.router)
    app.include_router(events.router)
    app.include_router(rules.router)
    app.include_router(rules.dry_run_router)
    app.include_router(audit.router)
    app.state.settings = settings
    app.state.store = store
    app.state.metrics = Metrics()
    app.state.buffer = EventBuffer(maxlen=100)
    app.state.event_repository = InMemoryEventRepository()
    return app


@pytest.fixture
def client(settings: Settings, store: RuleStore) -> TestClient:
    return TestClient(build_app(settings, store))
