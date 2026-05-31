from __future__ import annotations

import asyncio

import pytest

from app.core.config import Settings
from app.observability.events_buffer import EventBuffer
from app.observability.metrics import Metrics
from app.proxy.forwarder import UdpForwarder
from app.proxy.listener import UdpListener
from app.proxy.pipeline import Pipeline
from app.rules.models import Action, Condition, Match, Operator, Rule, RuleSet
from app.rules.repository import InMemoryRuleRepository
from app.rules.store import RuleStore


pytestmark = pytest.mark.integration

FORWARDED = (
    "CEF:0|Acme|Engine|1.0|100|Port scan|9|filtertype=ids filteripaddress=10.0.0.9"
)
DROPPED = "CEF:0|Acme|Engine|1.0|200|Heartbeat|1|filtertype=heartbeat"


class _Capture(asyncio.DatagramProtocol):
    def __init__(self, queue: asyncio.Queue[bytes]) -> None:
        self._queue = queue

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        self._queue.put_nowait(data)


async def test_end_to_end_forward_and_drop(tmp_path):
    loop = asyncio.get_running_loop()

    received: asyncio.Queue[bytes] = asyncio.Queue()
    recv_transport, _ = await loop.create_datagram_endpoint(
        lambda: _Capture(received), local_addr=("127.0.0.1", 0)
    )
    elk_port = recv_transport.get_extra_info("sockname")[1]

    settings = Settings(
        LISTEN_HOST="127.0.0.1",
        LISTEN_PORT=0,
        ELK_HOST="127.0.0.1",
        ELK_PORT=elk_port,
        DEFAULT_POLICY="forward",
        LOG_PER_EVENT=False,
        WORKER_COUNT=2,
    )

    store = RuleStore(InMemoryRuleRepository())
    store._ruleset = RuleSet(
        default_policy=Action.FORWARD,
        rules=[
            Rule(
                id="drop-heartbeat",
                match=Match(
                    conditions=[
                        Condition(field="filtertype", op=Operator.EQ, value="heartbeat")
                    ]
                ),
                action=Action.DROP,
            )
        ],
    )

    metrics = Metrics()
    buffer = EventBuffer(maxlen=50)
    forwarder = UdpForwarder()
    await forwarder.start()
    pipeline = Pipeline(
        settings=settings,
        store=store,
        forwarder=forwarder,
        metrics=metrics,
        buffer=buffer,
    )
    listener = UdpListener(settings=settings, pipeline=pipeline, metrics=metrics)
    await listener.start()
    proxy_port = listener.bound_port

    sender = await loop.create_datagram_endpoint(
        asyncio.DatagramProtocol, remote_addr=("127.0.0.1", proxy_port)
    )
    send_transport = sender[0]

    try:
        send_transport.sendto(FORWARDED.encode())
        got = await asyncio.wait_for(received.get(), timeout=3.0)
        assert got == FORWARDED.encode()

        send_transport.sendto(DROPPED.encode())
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(received.get(), timeout=1.0)

        assert metrics.forwarded == 1
        assert metrics.dropped == 1
    finally:
        send_transport.close()
        await listener.stop()
        forwarder.close()
        recv_transport.close()
