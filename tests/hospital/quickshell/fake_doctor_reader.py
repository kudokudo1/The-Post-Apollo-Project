#!/usr/bin/env python3
"""One-purpose fake Doctor reader for disposable Quickshell CI, never Hospital."""
import fcntl
import json
import os
from pathlib import Path
import signal
import sys
import time

state_str = os.environ.get("H1_DISPOSABLE_STATE_DIR", "")
if not state_str or sys.argv[1:] != ["doctor-directory"]:
    raise SystemExit("FAKE_READER_REFUSED_UNEXPECTED_ENV_OR_OPERATION")
state = Path(state_str).resolve()
if not state.is_dir() or not str(state).startswith("/tmp/"):
    raise SystemExit("FAKE_READER_REFUSED_UNSAFE_STATE_DIRECTORY")

counter = state / "counter"
with counter.open("a+", encoding="utf-8") as f:
    fcntl.flock(f, fcntl.LOCK_EX)
    f.seek(0)
    n = int(f.read().strip() or "0") + 1
    f.seek(0)
    f.truncate()
    f.write(str(n))
    f.flush()
    os.fsync(f.fileno())

def record(event):
    row = {
        "invocation": n,
        "event": event,
        "pid": os.getpid(),
        "time_ns": time.monotonic_ns(),
    }
    with (state / "events.jsonl").open("a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(row, separators=(",", ":")) + "\n")
        f.flush()
        os.fsync(f.fileno())

record("start")

if n == 1:
    # Emit apparently valid output, close stdout, then deliberately hang.
    # The UI must NOT publish it before accepting a normal-zero process exit.
    print('[{"id":"UNTRUSTED-OLD","name":"OLD READER"}]', flush=True)
    os.close(1)
    record("stdout_closed")

    def terminate(signum, frame):
        record("sigterm")
        raise SystemExit(143)

    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGINT, terminate)
    while True:
        time.sleep(1)

elif n == 2:
    # A legitimate new read after the timeout must succeed independently.
    print(json.dumps([{
        "id": "fixture-doctor",
        "name": "Fixture Doctor",
        "role": "DOCTOR",
        "status": "ACTIVE",
        "createdAt": "",
        "updatedAt": "",
    }]), flush=True)
    record("success")
    raise SystemExit(0)
else:
    record("unexpected_third_invocation")
    raise SystemExit(91)
