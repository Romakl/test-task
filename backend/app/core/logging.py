from __future__ import annotations

import datetime as dt
import json
import logging
from typing import Any

from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install as install_rich_traceback

from app.core.config import settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": dt.datetime.fromtimestamp(record.created, tz=dt.UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra_fields = getattr(record, "extra_fields", None)
        if isinstance(extra_fields, dict):
            payload.update(extra_fields)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging() -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    handler: logging.Handler
    if settings.LOG_JSON:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
    else:
        install_rich_traceback(show_locals=settings.DEBUG, width=120)
        handler = RichHandler(
            console=Console(force_terminal=True),
            show_time=True,
            show_path=settings.DEBUG,
            markup=False,
            rich_tracebacks=True,
            tracebacks_show_locals=settings.DEBUG,
            log_time_format="[%Y-%m-%d %H:%M:%S]",
        )
    handler.setLevel(level)

    logging.basicConfig(
        level=level, format="%(message)s", handlers=[handler], force=True
    )

    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event_decision(
    logger: logging.Logger,
    *,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    if settings.LOG_JSON:
        logger.log(level, "event_decision", extra={"extra_fields": fields})
    else:
        rendered = " ".join(f"{k}={v}" for k, v in fields.items())
        logger.log(level, "[event] %s", rendered)


logger = get_logger("cefproxy")
