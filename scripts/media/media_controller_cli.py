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


def ref(uri: str, source: str = "local-mpd") -> dict:
    return {"source": source,
            "kind": "video" if source == "youtube" else
                    "stream" if source == "direct-stream" else
                    "station" if source == "radio-browser" else "track",
            "id": uri}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hi-Fi // Universal Controller v0 (local MPD source)"
    )
    parser.add_argument("--socket", type=Path, default=None)
    subs = parser.add_subparsers(dest="action", required=True)
    for name in ("health", "sources", "snapshot", "audio-evidence", "queue", "play",
                 "pause", "stop", "next", "previous"):
        command = subs.add_parser(name)
        if name == "snapshot":
            command.add_argument("--client", default="default")
    search = subs.add_parser("search")
    search.add_argument("--client", default="default", help="Radio browse client scope")
    search.add_argument("query")
    search.add_argument("--source", choices=["local-mpd", "youtube", "radio-browser"], default="local-mpd")
    search.add_argument("--cursor", default=None, help="YouTube or Radio Browser pagination token")
    playlist = subs.add_parser("playlist")
    playlist.add_argument("playlist_id", help="YouTube playlist ID")
    playlist.add_argument("--cursor", default=None)
    for name in ("inspect", "select", "queue-add"):
        sub = subs.add_parser(name)
        sub.add_argument("--client", default="default", help="Radio browse client scope")
        sub.add_argument("uri", help="Exact source-qualified media ID returned by search")
        sub.add_argument("--source", choices=["local-mpd", "youtube", "direct-stream", "radio-browser"], default="local-mpd")
    load = subs.add_parser("load")
    load.add_argument("--client", default="default", help="Radio selection scope")
    load.add_argument("--uri", default=None,
                      help="Exact MPD library file or approved HTTPS stream URL; otherwise selected media")
    load.add_argument("--source", choices=["local-mpd", "youtube", "direct-stream", "radio-browser"], default="local-mpd")
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
        data = {"source": args.source, "query": args.query}
        if args.cursor is not None:
            data["cursor"] = args.cursor
    elif op == "playlist":
        op = "list"
        data = {"source": "youtube", "collection": {
            "source": "youtube", "kind": "playlist", "id": args.playlist_id}}
        if args.cursor is not None:
            data["cursor"] = args.cursor
    elif op in ("inspect", "select", "queue_add"):
        data = {"ref": ref(args.uri, args.source)}
    elif op == "load":
        data = {"autoplay": args.autoplay}
        if args.uri is not None:
            data["ref"] = ref(args.uri, args.source)
    elif op == "seek":
        op = "seek_relative"
        data = {"seconds": args.seconds}
    elif op == "queue_remove":
        data = {"queueId": args.queue_id}

    if args.action in ("search", "snapshot", "inspect", "select", "queue-add", "load"):
        if args.client != "default":
            data["client"] = args.client

    try:
        result = send(args.socket or default_socket(), op, data)
    except (OSError, RuntimeError, ValueError) as exc:
        print("HI-FI // CONNECTION ERROR // " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
