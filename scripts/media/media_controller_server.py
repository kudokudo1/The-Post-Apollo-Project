#!/usr/bin/env python3
"""Persistent, user-private JSON-lines socket server for the Hi-Fi controller."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import socket
import socketserver
import stat
import sys

from media_controller import MediaController
from radio_stream_relay import RadioStreamRelay
from media_intent_store import IntentStore


def default_socket() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime:
        raise RuntimeError("XDG_RUNTIME_DIR must be set; no insecure /tmp fallback")
    return Path(runtime) / "post-apollo-media" / "controller.sock"


def prepare_directory(path: Path) -> None:
    parent = path.parent
    if parent.is_symlink():
        raise RuntimeError("Refusing symlink runtime directory")
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = parent.stat()
    if info.st_uid != os.getuid() or (info.st_mode & 0o077):
        raise RuntimeError("Runtime directory must be owned by user and private (0700)")


class Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        raw = self.rfile.readline(65537)
        if not raw:
            return
        if len(raw) > 65536 or not raw.endswith(b"\n"):
            response = {"version": 1, "ok": False,
                        "error": {"code": "INVALID_REQUEST", "reason": "Oversized request"},
                        "result": None}
        else:
            try:
                request = json.loads(raw)
                with self.server.controller_lock:
                    response = self.server.controller.request(request)
            except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
                response = {"version": 1, "ok": False,
                            "error": {"code": "INVALID_JSON", "reason": str(exc)[:180]},
                            "result": None}
        self.wfile.write((json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8"))


class HiFiServer(socketserver.UnixStreamServer):
    allow_reuse_address = False

    def __init__(self, socket_path: str, controller: MediaController):
        import threading
        self.controller = controller
        self.controller_lock = threading.Lock()
        super().__init__(socket_path, Handler)


def run(path: Path) -> None:
    os.umask(0o077)
    prepare_directory(path)
    lock_path = path.with_suffix(".lock")
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(lock_path, flags, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise RuntimeError("Controller lock path must be a regular file")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if path.exists() or path.is_symlink():
            if path.is_symlink():
                raise RuntimeError("Refusing a symlink socket path")
            info = path.stat()
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
                raise RuntimeError("Refusing to replace a non-owned/non-socket path")
            try:
                with socket.socket(socket.AF_UNIX) as peer:
                    peer.settimeout(0.2)
                    peer.connect(str(path))
            except (ConnectionRefusedError, FileNotFoundError):
                path.unlink()  # Stale private socket, while holding our server lock.
            else:
                raise RuntimeError("Controller socket already has a live server")
        # The loopback relay is lazy. It starts only when the user explicitly
        # LOADs a directory station, not at application startup or on SEARCH.
        relay = RadioStreamRelay()
        try:
            controller = MediaController(intent_store=IntentStore(), radio_relay=relay)
            with HiFiServer(str(path), controller) as server:
                os.chmod(path, 0o600)
                bound_inode = path.stat().st_ino
                def stop(_signal, _frame):
                    raise KeyboardInterrupt()
                signal.signal(signal.SIGTERM, stop)
                signal.signal(signal.SIGINT, stop)
                print("HI-FI CONTROLLER // READY // " + str(path), flush=True)
                try:
                    server.serve_forever(poll_interval=0.2)
                except KeyboardInterrupt:
                    pass
                finally:
                    try:
                        if path.stat().st_ino == bound_inode:
                            path.unlink()
                    except FileNotFoundError:
                        pass
        finally:
            relay.close()
    finally:
        os.close(fd)


def main() -> int:
    parser = argparse.ArgumentParser(description="Standalone Hi-Fi media controller")
    parser.add_argument("--socket", type=Path, default=None,
                        help="Override XDG_RUNTIME_DIR socket (testing only)")
    args = parser.parse_args()
    try:
        run(args.socket or default_socket())
        return 0
    except (OSError, RuntimeError) as exc:
        print("HI-FI CONTROLLER // " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
