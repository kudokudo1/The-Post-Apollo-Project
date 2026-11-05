#!/usr/bin/env python3
"""C2k explicit-only Post-Apollo Connections status host launcher.

This process owns a C2j read-only server with a fixed IDLE status. Its existence
is NOT trusted-host attestation. C2i continues to display UNVERIFIED, and no
credential, grant, API, or provider process is started.

There is intentionally no daemonization, systemd installation, autostart,
arbitrary endpoint argument, user-supplied state, or request execution.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import signal
import sys
import threading

# Python -I intentionally excludes the script directory from sys.path.
# Load only the fixed sibling C2j server file, never a client-supplied module.
SERVER_SOURCE = Path(__file__).resolve().with_name("ConnectionsHostStatusServer.py")
_spec = importlib.util.spec_from_file_location("_post_apollo_c2j_status", SERVER_SOURCE)
if _spec is None or _spec.loader is None:
    raise ImportError("C2K_MISSING_REVIEWED_STATUS_SERVER")
_server_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_server_module)
ConnectionsHostStatusServer = _server_module.ConnectionsHostStatusServer

START_FLAG = "--run-readonly"
REFUSAL = "C2K_REFUSED_NO_APPROVED_RUNTIME_LAUNCH"
START_FAILED = "C2K_REFUSED_UNSAFE_OR_OCCUPIED_HOST_RUNTIME"


def run_readonly(
    *, runtime_directory: Path, stop_event: threading.Event,
    on_started=None,
) -> None:
    """Explicit, blocking status-only operation owned by this process.

    Supplied status is deliberately fixed. This is not an operator consent
    receipt; a real status producer and independent trust root are future work.
    """
    if not isinstance(stop_event, threading.Event):
        raise ValueError("A private stop event is required")
    # The host server itself checks runtime directory owner/mode, no symlinks,
    # same-UID socket peers, fixed STATUS V1 wire, and exclusive socket bind.
    server = ConnectionsHostStatusServer(
        runtime_directory=runtime_directory,
        status_provider=lambda: "IDLE",
    )
    try:
        server.start()
        if on_started is not None:
            on_started()
        stop_event.wait()
    finally:
        # C2j cleanup never replaces or unlinks a foreign socket inode.
        # This also cleans up on partial startup/occupied-socket failure.
        server.close()


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args != [START_FLAG]:
        print(REFUSAL, file=sys.stderr)
        return 2
    raw_runtime = os.environ.get("XDG_RUNTIME_DIR", "")
    if not raw_runtime or not os.path.isabs(raw_runtime):
        print(START_FAILED, file=sys.stderr)
        return 2

    stop = threading.Event()

    def request_stop(_signum, _frame) -> None:
        stop.set()

    # Only the main thread installs process signal handlers.
    if threading.current_thread() is not threading.main_thread():
        print(START_FAILED, file=sys.stderr)
        return 2
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    try:
        run_readonly(runtime_directory=Path(raw_runtime), stop_event=stop)
    except (OSError, RuntimeError, ValueError):
        print(START_FAILED, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
