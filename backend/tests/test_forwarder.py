from __future__ import annotations

import asyncio

from app.proxy.forwarder import UdpForwarder


class _Capture(asyncio.DatagramProtocol):
    def __init__(self, queue: asyncio.Queue[bytes]) -> None:
        self._queue = queue

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        self._queue.put_nowait(data)


async def _bind_receiver() -> tuple[
    asyncio.DatagramTransport, int, asyncio.Queue[bytes]
]:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[bytes] = asyncio.Queue()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: _Capture(queue), local_addr=("127.0.0.1", 0)
    )
    port = transport.get_extra_info("sockname")[1]
    return transport, port, queue


async def test_forwards_bytes_verbatim():
    transport, port, queue = await _bind_receiver()
    forwarder = UdpForwarder()
    await forwarder.start()
    payload = "CEF:0|Acme|Engine|1.0|100|Worm|10|src=10.0.0.1 msg=hello world".encode()
    try:
        assert await forwarder.send(payload, "127.0.0.1", port) is True
        got = await asyncio.wait_for(queue.get(), timeout=2.0)
        assert got == payload
    finally:
        forwarder.close()
        transport.close()


async def test_resolution_failure_returns_false():
    forwarder = UdpForwarder()
    await forwarder.start()
    try:
        assert await forwarder.send(b"x", "nope.invalid", 5140) is False
    finally:
        forwarder.close()


async def test_send_before_start_returns_false():
    forwarder = UdpForwarder()
    assert await forwarder.send(b"x", "127.0.0.1", 5140) is False
