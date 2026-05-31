from __future__ import annotations

import time
from collections import defaultdict


class Metrics:
    def __init__(self) -> None:
        self.started_at = time.time()
        self.datagrams_received = 0
        self.bytes_received = 0
        self.parse_ok = 0
        self.parse_errors = 0
        self.forwarded = 0
        self.dropped = 0
        self.forward_errors = 0
        self.source_rejected = 0
        self.rate_limited = 0
        self.queue_overflow = 0
        self.oversized = 0
        self.events_persisted = 0
        self.event_persist_dropped = 0
        self.rule_hits: dict[str, int] = defaultdict(int)

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self.started_at

    def record_rule_hit(self, rule_id: str) -> None:
        self.rule_hits[rule_id] += 1

    def snapshot(self) -> dict[str, object]:
        return {
            "uptime_seconds": round(self.uptime_seconds, 1),
            "datagrams_received": self.datagrams_received,
            "bytes_received": self.bytes_received,
            "parse_ok": self.parse_ok,
            "parse_errors": self.parse_errors,
            "forwarded": self.forwarded,
            "dropped": self.dropped,
            "forward_errors": self.forward_errors,
            "source_rejected": self.source_rejected,
            "rate_limited": self.rate_limited,
            "queue_overflow": self.queue_overflow,
            "oversized": self.oversized,
            "events_persisted": self.events_persisted,
            "event_persist_dropped": self.event_persist_dropped,
            "rule_hits": dict(self.rule_hits),
        }

    def prometheus(self) -> str:
        lines = [
            "# HELP cefproxy_datagrams_received_total UDP datagrams received.",
            "# TYPE cefproxy_datagrams_received_total counter",
            f"cefproxy_datagrams_received_total {self.datagrams_received}",
            "# HELP cefproxy_forwarded_total Events forwarded downstream.",
            "# TYPE cefproxy_forwarded_total counter",
            f"cefproxy_forwarded_total {self.forwarded}",
            "# HELP cefproxy_dropped_total Events dropped by policy.",
            "# TYPE cefproxy_dropped_total counter",
            f"cefproxy_dropped_total {self.dropped}",
            "# HELP cefproxy_parse_errors_total CEF parse failures.",
            "# TYPE cefproxy_parse_errors_total counter",
            f"cefproxy_parse_errors_total {self.parse_errors}",
            "# HELP cefproxy_forward_errors_total Downstream send failures.",
            "# TYPE cefproxy_forward_errors_total counter",
            f"cefproxy_forward_errors_total {self.forward_errors}",
            "# HELP cefproxy_rule_hits_total Per-rule match counts.",
            "# TYPE cefproxy_rule_hits_total counter",
        ]
        lines.extend(
            f'cefproxy_rule_hits_total{{rule_id="{rid}"}} {count}'
            for rid, count in self.rule_hits.items()
        )
        return "\n".join(lines) + "\n"
