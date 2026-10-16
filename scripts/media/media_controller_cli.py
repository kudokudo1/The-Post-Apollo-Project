#!/usr/bin/env python3
"""Terminal client for the shared Hi-Fi JSON API; does not spawn playback."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import socket
import sys

from media_controller_server import default_socket


def send(socket_path: Path, op: str, args: dict | None = None) -> dict:
    message = {"version": 1, "id": "cli", "op": op, "args": args or {}}
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(5)
        client.connect(str(socket_path))
        client.sendall((json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8"))
        with client.makefile("r", encoding="utf-8") as reply:
            line = reply.readline(5_000_001)
        if not line or not line.endswith("\n"):
            raise RuntimeError("Controller returned no complete response")
    result = json.loads(line)
    if not isinstance(result, dict) or result.get("version") != 1:
        raise RuntimeError("Unsupported controller response")
    return result


def ref(uri: str) -> dict:
    return {"source": "local-mpd", "kind": "track", "id": uri}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hi-Fi // Universal Controller v0 (local MPD source)"
    )
    parser.add_argument("--socket", type=Path, default=None)
    subs = parser.add_subparsers(dest="action", required=True)
    for name in ("health", "sources", "snapshot", "queue", "play",
                 "pause", "stop", "next", "previous"):
        subs.add_parser(name)
    search = subs.add_parser("search")
    search.add_argument("query")
    for name in ("inspect", "select", "queue-add"):
        sub = subs.add_parser(name)
        sub.add_argument("uri", help="Exact MPD library file ID returned by search")
    load = subs.add_parser("load")
    load.add_argument("--uri", default=None,
                      help="Specific MPD library file; default is selected track")
    load.add_argument("--autoplay", action="store_true",
                      help="Explicitly start after loading (default is NO autoplay)")
    seek = subs.add_parser("seek")
    seek.add_argument("seconds", type=int, help="Relative seconds, e.g. -5 or +5")
    remove = subs.add_parser("queue-remove")
    remove.add_argument("queue_id")
    args = parser.parse_args()

    op = args.action.replace("-", "_")
    data: dict = {}
    if op == "search":
        data = {"source": "local-mpd", "query": args.query}
    elif op in ("inspect", "select", "queue_add"):
        data = {"ref": ref(args.uri)}
    elif op == "load":
        data = {"autoplay": args.autoplay}
        if args.uri is not None:
            data["ref"] = ref(args.uri)
    elif op == "seek":
        op = "seek_relative"
        data = {"seconds": args.seconds}
    elif op == "queue_remove":
        data = {"queueId": args.queue_id}

    try:
        result = send(args.socket or default_socket(), op, data)
    except (OSError, RuntimeError, ValueError) as exc:
        print("HI-FI // CONNECTION ERROR // " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
