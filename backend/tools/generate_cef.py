from __future__ import annotations

import argparse
import random
import socket
import time


NAMES = [
    "Port scan detected",
    "Malware signature match",
    "Brute force login attempt",
    "Suspicious outbound connection",
    "Privilege escalation attempt",
    "Data exfiltration suspected",
    "Configuration drift",
    "Disk usage threshold exceeded",
]
FILTER_TYPES = ["ids", "ips", "av", "edr", "fim", "netflow", "heartbeat"]
HOSTNAMES = ["sensor-a", "sensor-b", "edge-01", "edge-02", "core-fw"]
NODENAMES = ["node-1", "node-2", "node-3"]
SUBNETS = ["10.0.0.", "192.168.1.", "172.16.5.", "203.0.113."]


def _esc_header(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|")


def _esc_ext(value: str) -> str:
    return value.replace("\\", "\\\\").replace("=", "\\=")


def build_cef(rng: random.Random, *, syslog: bool) -> str:
    eventid = rng.randint(1000, 9999)
    severity = rng.randint(0, 10)
    name = rng.choice(NAMES)
    ext = {
        "eventid": str(eventid),
        "filterhostname": rng.choice(HOSTNAMES),
        "filterid": str(rng.randint(1, 50)),
        "filteripaddress": rng.choice(SUBNETS) + str(rng.randint(1, 254)),
        "filternodename": rng.choice(NODENAMES),
        "filterpriority": str(rng.randint(1, 10)),
        "filtertype": rng.choice(FILTER_TYPES),
        "notificationtime": str(int(time.time() * 1000)),
    }
    header = "|".join(
        [
            "CEF:0",
            _esc_header("Acme"),
            _esc_header("FilterEngine"),
            _esc_header("1.0"),
            str(eventid),
            _esc_header(name),
            str(severity),
        ]
    )
    extension = " ".join(f"{k}={_esc_ext(v)}" for k, v in ext.items())
    line = f"{header}|{extension}"
    if syslog:
        ts = time.strftime("%b %d %H:%M:%S")
        line = f"<134>{ts} {ext['filterhostname']} {line}"
    return line


def main() -> None:
    parser = argparse.ArgumentParser(description="Send synthetic CEF alerts over UDP.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5514)
    parser.add_argument("--count", type=int, default=10, help="number of datagrams")
    parser.add_argument(
        "--interval", type=float, default=0.2, help="seconds between sends"
    )
    parser.add_argument("--syslog", action="store_true", help="wrap in a syslog prefix")
    parser.add_argument(
        "--malformed-rate",
        type=float,
        default=0.0,
        help="fraction (0..1) of datagrams to corrupt, to exercise the parser",
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="RNG seed for reproducibility"
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)  # nosec B311 - synthetic test traffic, not crypto
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sent = 0
    try:
        for i in range(args.count):
            if args.malformed_rate and rng.random() < args.malformed_rate:
                payload = f"not-a-cef-message-{i} garbage|||".encode()
            else:
                payload = build_cef(rng, syslog=args.syslog).encode("utf-8")
            sock.sendto(payload, (args.host, args.port))
            sent += 1
            print(
                f"[{sent}/{args.count}] -> {args.host}:{args.port}  {payload.decode('utf-8', 'replace')[:120]}"
            )
            if args.interval:
                time.sleep(args.interval)
    finally:
        sock.close()
    print(f"done: sent {sent} datagram(s)")


if __name__ == "__main__":
    main()
