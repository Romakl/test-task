from __future__ import annotations

import asyncio
import socket
import time

from app.core.logging import get_logger


logger = get_logger("cefproxy.forwarder")

_RESOLVE_TTL_SECONDS = 60.0
_RESOLVE_NEGATIVE_TTL_SECONDS = 5.0


class _SendProtocol(asyncio.DatagramProtocol):
    pass


class UdpForwarder:
    def __init__(self) -> None:
        self._transport: asyncio.DatagramTransport | None = None
        self._resolve_cache: dict[str, tuple[str | None, float]] = {}

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            _SendProtocol,
            local_addr=("0.0.0.0", 0),  # noqa: S104  # nosec B104 - ephemeral egress source port
            family=socket.AF_INET,
        )
        self._transport = transport
        logger.info("forwarder ready (IPv4 egress socket bound)")

    def close(self) -> None:
        if self._transport is not None:
            self._transport.close()
            self._transport = None

    async def _resolve(self, host: str) -> str | None:
        now = time.time()
        cached = self._resolve_cache.get(host)
        if cached is not None and cached[1] > now:
            return cached[0]

        ip: str | None = None
        try:
            loop = asyncio.get_running_loop()
            infos = await loop.getaddrinfo(
                host, None, family=socket.AF_INET, type=socket.SOCK_DGRAM
            )
            if infos:
                ip = infos[0][4][0]
        except socket.gaierror as exc:
            logger.error("DNS resolution failed for %s: %s", host, exc)

        ttl = _RESOLVE_TTL_SECONDS if ip is not None else _RESOLVE_NEGATIVE_TTL_SECONDS
        self._resolve_cache[host] = (ip, now + ttl)
        return ip

    async def send(self, data: bytes, host: str, port: int) -> bool:
        if self._transport is None:
            logger.error("forwarder not started; dropping forward to %s:%s", host, port)
            return False
        ip = await self._resolve(host)
        if ip is None:
            return False
        try:
            self._transport.sendto(data, (ip, port))
        except OSError as exc:
            logger.error("forward to %s:%s failed: %s", host, port, exc)
            return False
        return True
