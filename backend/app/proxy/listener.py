from __future__ import annotations

import asyncio

from app.core.config import Settings
from app.core.logging import get_logger
from app.observability.metrics import Metrics
from app.proxy.pipeline import Pipeline


logger = get_logger("cefproxy.listener")


class _ListenerProtocol(asyncio.DatagramProtocol):
    def __init__(
        self,
        queue: asyncio.Queue[tuple[bytes, tuple[str, int]]],
        metrics: Metrics,
        max_bytes: int,
    ) -> None:
        self._queue = queue
        self._metrics = metrics
        self._max_bytes = max_bytes

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        if len(data) > self._max_bytes:
            self._metrics.oversized += 1
            return
        try:
            self._queue.put_nowait((data, addr))
        except asyncio.QueueFull:
            self._metrics.queue_overflow += 1

    def error_received(self, exc: Exception) -> None:
        logger.warning("listener socket error: %s", exc)


class UdpListener:
    def __init__(
        self, *, settings: Settings, pipeline: Pipeline, metrics: Metrics
    ) -> None:
        self._settings = settings
        self._pipeline = pipeline
        self._metrics = metrics
        self._queue: asyncio.Queue[tuple[bytes, tuple[str, int]]] = asyncio.Queue(
            maxsize=settings.INGRESS_QUEUE_MAXSIZE
        )
        self._transport: asyncio.DatagramTransport | None = None
        self._workers: list[asyncio.Task[None]] = []

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: _ListenerProtocol(
                self._queue, self._metrics, self._settings.MAX_DATAGRAM_BYTES
            ),
            local_addr=(self._settings.LISTEN_HOST, self._settings.LISTEN_PORT),
        )
        self._transport = transport
        self._workers = [
            asyncio.create_task(self._worker(i), name=f"cefproxy-worker-{i}")
            for i in range(self._settings.WORKER_COUNT)
        ]
        logger.info(
            "listening for CEF/Syslog on udp://%s:%d with %d worker(s)",
            self._settings.LISTEN_HOST,
            self.bound_port,
            self._settings.WORKER_COUNT,
        )

    @property
    def bound_port(self) -> int:
        if self._transport is None:
            return self._settings.LISTEN_PORT
        sock = self._transport.get_extra_info("sockname")
        return int(sock[1]) if sock else self._settings.LISTEN_PORT

    async def _worker(self, index: int) -> None:
        while True:
            data, addr = await self._queue.get()
            try:
                await self._pipeline.handle(data, addr)
            except Exception:
                logger.exception(
                    "worker %d: unhandled error processing datagram", index
                )
            finally:
                self._queue.task_done()

    async def stop(self) -> None:
        for task in self._workers:
            task.cancel()
        for task in self._workers:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._workers.clear()
        if self._transport is not None:
            self._transport.close()
            self._transport = None
        logger.info("listener stopped")
