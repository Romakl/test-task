from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import audit, events, health, metrics, rules
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.db.base import Base
from app.db.session import create_engine, create_session_factory
from app.observability.event_repository import SqlEventRepository
from app.observability.event_writer import EventWriter
from app.observability.events_buffer import EventBuffer
from app.observability.metrics import Metrics
from app.proxy.forwarder import UdpForwarder
from app.proxy.listener import UdpListener
from app.proxy.pipeline import Pipeline
from app.rules.repository import SqlRuleRepository
from app.rules.store import RuleStore, seed_from_file


logger = get_logger("cefproxy.main")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    logger.info("starting %s (env=%s)", settings.APP_NAME, settings.APP_ENV)

    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    if settings.DB_AUTO_CREATE:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    rule_repository = SqlRuleRepository(session_factory)
    event_repository = SqlEventRepository(session_factory)

    store = RuleStore(rule_repository)
    await store.load()
    await seed_from_file(store, settings.SEED_RULES_PATH)

    app_metrics = Metrics()
    buffer = EventBuffer(maxlen=settings.EVENT_BUFFER_SIZE)

    event_writer: EventWriter | None = None
    if settings.EVENT_PERSIST:
        event_writer = EventWriter(
            repository=event_repository, metrics=app_metrics, settings=settings
        )
        await event_writer.start()

    forwarder = UdpForwarder()
    await forwarder.start()
    pipeline = Pipeline(
        settings=settings,
        store=store,
        forwarder=forwarder,
        metrics=app_metrics,
        buffer=buffer,
        event_writer=event_writer,
    )
    listener = UdpListener(settings=settings, pipeline=pipeline, metrics=app_metrics)
    await listener.start()

    app.state.settings = settings
    app.state.store = store
    app.state.metrics = app_metrics
    app.state.buffer = buffer
    app.state.forwarder = forwarder
    app.state.engine = engine
    app.state.event_repository = event_repository

    if not settings.API_TOKEN:
        if settings.is_prod:
            msg = (
                "API_TOKEN must be set when APP_ENV=production — refusing to start "
                "an unauthenticated management API."
            )
            raise RuntimeError(msg)
        logger.warning(
            "API_TOKEN is not set — the management API mutating endpoints are OPEN. "
            "Set API_TOKEN before exposing this beyond localhost."
        )

    try:
        yield
    finally:
        logger.info("shutting down")
        await listener.stop()
        forwarder.close()
        if event_writer is not None:
            await event_writer.stop()
        await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="API-only filter-and-forward proxy for CEF/Syslog security alerts.",
        lifespan=lifespan,
    )
    if settings.CORS_ALLOW_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ALLOW_ORIGINS,
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.include_router(health.router)
    app.include_router(metrics.router)
    app.include_router(events.router)
    app.include_router(rules.router)
    app.include_router(rules.dry_run_router)
    app.include_router(audit.router)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {
            "service": settings.APP_NAME,
            "status": "ok",
            "docs": "/docs",
            "health": "/health",
            "metrics": "/metrics",
        }

    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )


if __name__ == "__main__":
    run()
