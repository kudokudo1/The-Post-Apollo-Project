"""CI-only child for the real R3 pipe and synthetic observation providers."""
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

SOURCE = {"boot_id": "c23683a9-b2ab-4a2c-87ce-31bdf27a3012",
          "base": {"device": 42, "inode": 9007199254740993, "size_kib": 16777212},
          "extension": {"device": 42, "inode": 9007199254740995, "size_kib": 8388604}}


def capture():
    wall, mono = system_clock_ms()
    return {"version": 1, "source": copy.deepcopy(SOURCE),
            "wall_ms": wall, "monotonic_ms": mono}


def observe(record, observer):
    # No claim of native readiness; unavailable provider is explicit.
    return None


class DelayedReplyRuntime(Runtime):
    def local_action(self, message):
        result=super().local_action(message)
        # Test-only delay after the durable transaction, before reply.
        if os.environ.get("POST_APOLLO_QUEUE_WATCHDOG_TRIAL")=="1":
            print("QUEUE_R3_CHILD // committed before delayed reply",file=sys.stderr,flush=True)
            time.sleep(8)
        return result


def factory(queue):
    return DelayedReplyRuntime(queue, capture, observe, interval_ms=10000,
                   max_age_ms=20000, max_gap_ms=20000, stable_ms=20000)


owner = Owner(Queue(root / "private" / "queue.db"), factory, durable_actions=True)
serve(owner, 0, 1, io_timeout_ms=3000)
