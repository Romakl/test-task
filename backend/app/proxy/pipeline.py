from __future__ import annotations

import ipaddress
import logging
import time

from app.cef.parser import CefParseError, parse_cef
from app.core.config import Settings
from app.core.logging import get_logger, log_event_decision
from app.observability.event_writer import EventWriter
from app.observability.events_buffer import EventBuffer, EventRecord
from app.observability.metrics import Metrics
from app.proxy.forwarder import UdpForwarder
from app.rules.engine import evaluate
from app.rules.models import Action
from app.rules.store import RuleStore


logger = get_logger("cefproxy.pipeline")

_RATE_LIMIT_GC_THRESHOLD = 10_000


class Pipeline:
    def __init__(
        self,
        *,
        settings: Settings,
        store: RuleStore,
        forwarder: UdpForwarder,
        metrics: Metrics,
        buffer: EventBuffer,
        event_writer: EventWriter | None = None,
    ) -> None:
        self.settings = settings
        self.store = store
        self.forwarder = forwarder
        self.metrics = metrics
        self.buffer = buffer
        self.event_writer = event_writer
        self._allowed_nets = [
            ipaddress.ip_network(c, strict=False) for c in settings.ALLOWED_SOURCE_CIDRS
        ]
        self._rate_window: dict[str, tuple[int, int]] = {}
        self._default_policy = Action(settings.DEFAULT_POLICY)

    def _source_allowed(self, ip: str) -> bool:
        if not self._allowed_nets:
            return True
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return False
        return any(addr in net for net in self._allowed_nets)

    def _rate_ok(self, ip: str) -> bool:
        limit = self.settings.RATE_LIMIT_PER_SOURCE_PER_SEC
        if limit <= 0:
            return True
        sec = int(time.time())
        window, count = self._rate_window.get(ip, (sec, 0))
        if window != sec:
            window, count = sec, 0
        count += 1
        self._rate_window[ip] = (window, count)
        if len(self._rate_window) > _RATE_LIMIT_GC_THRESHOLD:
            self._rate_window = {
                k: v for k, v in self._rate_window.items() if v[0] == sec
            }
        return count <= limit

    async def handle(self, data: bytes, addr: tuple[str, int]) -> EventRecord | None:
        src_ip, src_port = addr[0], addr[1]
        self.metrics.datagrams_received += 1
        self.metrics.bytes_received += len(data)

        if not self._source_allowed(src_ip):
            self.metrics.source_rejected += 1
            logger.warning("rejected datagram from disallowed source %s", src_ip)
            return None

        if not self._rate_ok(src_ip):
            self.metrics.rate_limited += 1
            logger.warning("rate-limited source %s", src_ip)
            return None

        text = data.decode("utf-8", errors="replace")

        try:
            event = parse_cef(text)
        except CefParseError as exc:
            return await self._handle_parse_error(data, text, src_ip, src_port, exc)

        self.metrics.parse_ok += 1
        decision = evaluate(event, self.store.ruleset, self._default_policy)
        if decision.matched_rule_id:
            self.metrics.record_rule_hit(decision.matched_rule_id)

        destination: str | None = None
        if decision.action is Action.FORWARD:
            host = decision.destination_host or self.settings.ELK_HOST
            port = decision.destination_port or self.settings.ELK_PORT
            destination = f"{host}:{port}"
            ok = await self.forwarder.send(data, host, port)
            if ok:
                self.metrics.forwarded += 1
            else:
                self.metrics.forward_errors += 1
        else:
            self.metrics.dropped += 1

        record = EventRecord(
            seq=self.buffer.next_seq(),
            ts=self.buffer.now_iso(),
            source_ip=src_ip,
            source_port=src_port,
            size_bytes=len(data),
            parsed=True,
            action=decision.action.value,
            matched_rule_id=decision.matched_rule_id,
            reason=decision.reason,
            destination=destination if decision.action is Action.FORWARD else None,
            fields=event.as_flat_dict(),
            raw_preview=text[:500],
        )
        self._observe(record)
        return record

    async def _handle_parse_error(
        self,
        data: bytes,
        text: str,
        src_ip: str,
        src_port: int,
        exc: CefParseError,
    ) -> EventRecord:
        self.metrics.parse_errors += 1
        destination: str | None = None
        if self.settings.FORWARD_ON_PARSE_ERROR:
            host, port = self.settings.ELK_HOST, self.settings.ELK_PORT
            destination = f"{host}:{port}"
            ok = await self.forwarder.send(data, host, port)
            if ok:
                self.metrics.forwarded += 1
                action, reason = "forward", f"parse error ({exc}); forwarded by policy"
            else:
                self.metrics.forward_errors += 1
                action, reason = "forward", f"parse error ({exc}); forward FAILED"
        else:
            self.metrics.dropped += 1
            action, reason = "drop", f"parse error ({exc}); dropped by policy"

        record = EventRecord(
            seq=self.buffer.next_seq(),
            ts=self.buffer.now_iso(),
            source_ip=src_ip,
            source_port=src_port,
            size_bytes=len(data),
            parsed=False,
            parse_error=str(exc),
            action=action,
            reason=reason,
            destination=destination,
            raw_preview=text[:500],
        )
        self._observe(record, level=logging.WARNING)
        return record

    def _observe(self, record: EventRecord, level: int = logging.INFO) -> None:
        self.buffer.add(record)
        if self.event_writer is not None:
            self.event_writer.enqueue(record)
        if self.settings.LOG_PER_EVENT:
            log_event_decision(
                logger,
                level=level,
                seq=record.seq,
                src=f"{record.source_ip}:{record.source_port}",
                bytes=record.size_bytes,
                parsed=record.parsed,
                action=record.action,
                rule=record.matched_rule_id or "-",
                dest=record.destination or "-",
                name=record.fields.get("name", "-"),
                severity=record.fields.get("severity", "-"),
                reason=record.reason,
            )
