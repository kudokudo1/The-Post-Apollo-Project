"""Disposable real v2 owner. No native memory provider or installed paths."""
import copy
import os
from pathlib import Path
import sys
import time

if os.environ.get("POST_APOLLO_QUEUE_PIPE_SMOKE") != "CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable fixture only")
root = Path(__file__).resolve().parent
sys.path.insert(0, str(root / "memory"))
from memory_adjustment_queue import Queue
from memory_queue_owner import Owner
from memory_queue_runtime import Runtime, system_clock_ms
from memory_queue_pipe import serve

generation = int(sys.argv[1])
if generation not in (1, 2, 3):
    raise SystemExit("Invalid fixture owner generation")
source = {"boot_id": "c23683a9-b2ab-4a2c-87ce-31bdf27a3012",
          "base": {"device": 42, "inode": 100, "size_kib": 16777212},
          "extension": {"device": 42, "inode": 101, "size_kib": 8388604}}

def capture():
    wall, mono = system_clock_ms()
    return {"version":1, "source":copy.deepcopy(source), "wall_ms":wall, "monotonic_ms":mono}

# Supervisor must bind a pidfd to this exact child before any packet.
ticks = Path("/proc/self/stat").read_text().rsplit(")",1)[1].split()[19]
print("R6F_OWNER // %d %d %s" % (generation, os.getpid(), ticks), file=sys.stderr, flush=True)
until = time.monotonic()+8
while not (root / ("owner-%d.ready" % generation)).is_file():
    if time.monotonic() >= until:
        raise SystemExit("Missing disposable process witness")
    time.sleep(.01)

owner = Owner(Queue(root/"private"/"queue.db"),
    lambda q:Runtime(q,capture,lambda *_:None,interval_ms=10000,max_age_ms=20000,
                     max_gap_ms=20000,stable_ms=20000,local_disposition_enabled=True),
    durable_actions=True,staged_max_age_ms=10000,local_disposition_enabled=True)
serve(owner,0,1,io_timeout_ms=3000,review_max_age_ms=10000,disposition_wire=True)
