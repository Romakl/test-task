from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC)


class RuleRow(Base):
    __tablename__ = "rules"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class AppSettingRow(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditRow(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ts: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)


class EventRow(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    seq: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ts: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    source_ip: Mapped[str] = mapped_column(String(64), nullable=False)
    source_port: Mapped[int] = mapped_column(Integer, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    parsed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    matched_rule_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    destination: Mapped[str | None] = mapped_column(String(128), nullable=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fields: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    raw_preview: Mapped[str] = mapped_column(Text, nullable=False, default="")
