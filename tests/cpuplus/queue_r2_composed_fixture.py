"""Disposable R2 cross-language fixture, never a production transport.

No /proc, protected files, commands, system services or native observations.
All requests go to a temporary private SQLite database and simulated clock.
"""
import copy
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from memory_adjustment_queue import Queue, QueueError
from memory_queue_runtime import Runtime
from memory_queue_owner import Owner
from memory_queue_delivery import Delivery

SOURCE = {"boot_id": "c23683a9-b2ab-4a2c-87ce-31bdf27a3012",
          "base": {"device": 42, "inode": 9007199254740993, "size_kib": 16777212},
          "extension": {"device": 42, "inode": 9007199254740995, "size_kib": 8388604}}
EVIDENCE = {"targetGiB": 16, "baseSizeKiB": 16777212,
            "extensionSizeKiB": 8388604, "extensionUsedKiB": 0,
            "availableKiB": 10000000, "requiredRamKiB": 8000000,
            "baseFreeKiB": 16000000, "requiredBaseFreeKiB": 2097152,
            "someAvg10": 0.1, "fullAvg10": 0.0}


class Fixture:
    def __init__(self, path):
        self.path = path
        self.wall, self.mono = 100000, 10000
        self.captures = self.samples = self.offers = 0
        self.mode = "READY"
        self.owner = self.make_owner()

    def clock(self):
        return self.wall, self.mono

    def capture(self):
        self.captures += 1
        if self.mode == "UNAVAILABLE":
            raise QueueError("FIXTURE_PROVIDER_UNAVAILABLE")
        return {"version": 1, "source": copy.deepcopy(SOURCE),
                "wall_ms": self.wall, "monotonic_ms": self.mono}

    def observe(self, record, observer):
        self.samples += 1
        if self.mode == "UNAVAILABLE":
            return None
        return {"version": 1, "request_id": record["id"], "observer_id": observer,
                "source": copy.deepcopy(SOURCE), "wall_time": self.wall // 1000,
                "monotonic_ms": self.mono, "operation_state": "IDLE",
                "preflight": {"version": 1,
                              "state": "WAITING" if self.mode == "OCCUPIED" else "READY_ADVISORY",
                              "code": "EXTENSION_OCCUPIED" if self.mode == "OCCUPIED"
                              else "FRESH_AUTH_AND_ROOT_CHECK_REQUIRED",
                              "evidence": copy.deepcopy(EVIDENCE)}}

    def factory(self, queue):
        return Runtime(queue, self.capture, self.observe, interval_ms=1000,
                       max_age_ms=3000, max_gap_ms=2000, stable_ms=3000, clock=self.clock)

    def make_owner(self):
        return Owner(Queue(self.path), self.factory)

    def call(self, command):
        kind = command["kind"]
        if kind == "connect":
            return self.owner.owner_id
        if kind == "publish":
            return self.owner.publish()
        if kind == "passive":
            return self.owner.status()
        if kind == "action":
            return self.owner.action(command["message"])
        if kind == "advance":
            ms = command["ms"]
            assert type(ms) is int and 0 <= ms <= 60000
            self.wall += ms
            self.mono += ms
            return None
        if kind == "mode":
            assert command["mode"] in {"READY", "OCCUPIED", "UNAVAILABLE"}
            self.mode = command["mode"]
            return None
        if kind == "invalidate":
            self.owner.invalidate()
            return None
        if kind == "restart":
            self.owner.close()
            self.owner = self.make_owner()
            return self.owner.owner_id
        if kind == "counts":
            return {"captures": self.captures, "samples": self.samples,
                    "offers": self.offers}
        if kind == "offer":
            # Synchronous fake offer only; no actual Hub or cross-process packet.
            def offer(packet):
                assert packet["can_execute"] is False
                assert packet["delivery_state"] == "ATTEMPT_RESERVED"
                self.offers += 1
                return "HISTORY_OBSERVED"
            return Delivery(self.owner.runtime.events).attempt(
                command["event_id"],
                read_status=lambda: (self.owner.status() or {}).get("projection", {}).get("status"),
                clock=self.clock, max_age_ms=3000, offer=offer)
        if kind == "history_summary":
            # Never send the raw Linux identity or receipt across this test wire.
            d = self.owner.detail(command["request_id"])["detail"]
            return {"state": d["request"]["state"], "outcome": d["adjustment_outcome"],
                    "events": len(d["notification_events"])}
        raise ValueError("Unknown fixture command")


with tempfile.TemporaryDirectory() as tmp:
    fixture = Fixture(Path(tmp) / "queue.db")
    try:
        for line in sys.stdin:
            try:
                result = fixture.call(json.loads(line))
                reply = {"ok": True, "value": result}
            except QueueError as exc:
                reply = {"ok": False, "code": str(exc)}
            print(json.dumps(reply, allow_nan=False), flush=True)
    finally:
        fixture.owner.close()
