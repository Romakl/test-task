from __future__ import annotations

import argparse
import socket


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mock UDP receiver (stand-in for ELK)."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5140)
    parser.add_argument(
        "--quiet", action="store_true", help="count only, do not print payloads"
    )
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((args.host, args.port))
    print(
        f"mock-elk listening on udp://{args.host}:{args.port} (Ctrl-C to stop)",
        flush=True,
    )

    received = 0
    try:
        while True:
            data, addr = sock.recvfrom(65535)
            received += 1
            if not args.quiet:
                text = data.decode("utf-8", errors="replace")
                print(
                    f"[{received}] from {addr[0]}:{addr[1]} ({len(data)}B)  {text}",
                    flush=True,
                )
    except KeyboardInterrupt:
        print(f"\nstopping; received {received} datagram(s)")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
