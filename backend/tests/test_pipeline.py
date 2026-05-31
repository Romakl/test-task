from __future__ import annotations

from app.core.config import Settings
from app.observability.events_buffer import EventBuffer
from app.observability.metrics import Metrics
from app.proxy.pipeline import Pipeline
from app.rules.models import Action, Condition, Match, Operator, Rule, RuleSet
from app.rules.repository import InMemoryRuleRepository
from app.rules.store import RuleStore


class FakeForwarder:
    def __init__(self) -> None:
        self.sent: list[tuple[bytes, str, int]] = []

    async def send(self, data: bytes, host: str, port: int) -> bool:
        self.sent.append((data, host, port))
        return True


def _settings(tmp_path, **kw) -> Settings:
    defaults = dict(
        ELK_HOST="127.0.0.1",
        ELK_PORT=5140,
        DEFAULT_POLICY="forward",
        LOG_PER_EVENT=False,
    )
    defaults.update(kw)
    return Settings(**defaults)


def _pipeline(settings, rules=None, default_policy=None):
    store = RuleStore(InMemoryRuleRepository())
    if rules is not None:
        store._ruleset = RuleSet(rules=rules, default_policy=default_policy)
    forwarder = FakeForwarder()
    metrics = Metrics()
    buffer = EventBuffer(maxlen=50)
    pipeline = Pipeline(
        settings=settings,
        store=store,
        forwarder=forwarder,
        metrics=metrics,
        buffer=buffer,
    )
    return pipeline, forwarder, metrics, buffer


CEF = "CEF:0|Acme|Engine|1.0|100|Worm|9|filtertype=ids filteripaddress=10.0.0.5 severity=9"


def _drop_rule():
    return Rule(
        id="drop-ids",
        match=Match(
            conditions=[Condition(field="filtertype", op=Operator.EQ, value="ids")]
        ),
        action=Action.DROP,
    )


async def test_default_policy_forward(tmp_path):
    settings = _settings(tmp_path)
    pipeline, fwd, metrics, buffer = _pipeline(settings)
    data = CEF.encode()
    record = await pipeline.handle(data, ("10.0.0.1", 1234))
    assert record is not None and record.action == "forward"
    assert fwd.sent == [(data, "127.0.0.1", 5140)]
    assert metrics.forwarded == 1
    assert buffer.recent()[0].seq == record.seq


async def test_drop_rule_blocks_forward(tmp_path):
    settings = _settings(tmp_path)
    pipeline, fwd, metrics, _ = _pipeline(settings, rules=[_drop_rule()])
    record = await pipeline.handle(CEF.encode(), ("10.0.0.1", 1234))
    assert record.action == "drop"
    assert fwd.sent == []
    assert metrics.dropped == 1
    assert metrics.rule_hits["drop-ids"] == 1


async def test_forward_bytes_are_verbatim(tmp_path):
    settings = _settings(tmp_path)
    pipeline, fwd, _, _ = _pipeline(settings)
    data = ("<134>Sep 19 08:26:10 host " + CEF).encode()
    await pipeline.handle(data, ("10.0.0.1", 1234))
    assert fwd.sent[0][0] == data


async def test_parse_error_forwarded_by_default(tmp_path):
    settings = _settings(tmp_path, FORWARD_ON_PARSE_ERROR=True)
    pipeline, fwd, metrics, _ = _pipeline(settings)
    bad = b"this is not cef"
    record = await pipeline.handle(bad, ("10.0.0.1", 1234))
    assert record.parsed is False
    assert metrics.parse_errors == 1
    assert fwd.sent == [(bad, "127.0.0.1", 5140)]


async def test_parse_error_dropped_when_failclosed(tmp_path):
    settings = _settings(tmp_path, FORWARD_ON_PARSE_ERROR=False)
    pipeline, fwd, metrics, _ = _pipeline(settings)
    record = await pipeline.handle(b"nope", ("10.0.0.1", 1234))
    assert record.action == "drop"
    assert metrics.parse_errors == 1
    assert fwd.sent == []


async def test_source_allowlist_rejects(tmp_path):
    settings = _settings(tmp_path, ALLOWED_SOURCE_CIDRS=["10.0.0.0/8"])
    pipeline, fwd, metrics, _ = _pipeline(settings)
    assert await pipeline.handle(CEF.encode(), ("8.8.8.8", 1234)) is None
    assert metrics.source_rejected == 1
    assert fwd.sent == []


async def test_source_allowlist_allows(tmp_path):
    settings = _settings(tmp_path, ALLOWED_SOURCE_CIDRS=["10.0.0.0/8"])
    pipeline, fwd, _, _ = _pipeline(settings)
    assert await pipeline.handle(CEF.encode(), ("10.1.2.3", 1234)) is not None
    assert len(fwd.sent) == 1


async def test_rate_limit(tmp_path):
    settings = _settings(tmp_path, RATE_LIMIT_PER_SOURCE_PER_SEC=1)
    pipeline, _, metrics, _ = _pipeline(settings)
    await pipeline.handle(CEF.encode(), ("10.0.0.1", 1234))
    await pipeline.handle(CEF.encode(), ("10.0.0.1", 1234))
    assert metrics.rate_limited == 1


def test_listener_drops_oversized_datagram():
    import asyncio

    from app.proxy.listener import _ListenerProtocol

    metrics = Metrics()
    queue: asyncio.Queue = asyncio.Queue(maxsize=10)
    proto = _ListenerProtocol(queue, metrics, max_bytes=10)
    proto.datagram_received(b"x" * 50, ("10.0.0.1", 1))
    assert metrics.oversized == 1
    assert queue.qsize() == 0
    proto.datagram_received(b"small", ("10.0.0.1", 1))
    assert queue.qsize() == 1


async def test_destination_override(tmp_path):
    from app.rules.models import Destination

    settings = _settings(tmp_path)
    rule = Rule(
        id="crit",
        match=Match(conditions=[Condition(field="severity", op=Operator.GE, value=9)]),
        action=Action.FORWARD,
        destination=Destination(host="crit-elk", port=5141),
    )
    pipeline, fwd, _, _ = _pipeline(settings, rules=[rule])
    await pipeline.handle(CEF.encode(), ("10.0.0.1", 1234))
    assert fwd.sent[0][1:] == ("crit-elk", 5141)
