#!/usr/bin/env python3
"""Real ForestW Runtime child: bounded private stdio; native admission HOLD.

No test peer, model pull, default endpoint, command-line settings, or
automatic launch. The separately reviewed parent owns process lifetime.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import select
import sys
import time
from concurrent.futures import ThreadPoolExecutor

# A reviewed absolute script under Python -I imports only its siblings.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from first_light_delivery import RealLocalRequestBridge

INPUT_CAP = 32768
OUTPUT_CAP = 100000
TOTAL_CAP = 512000
ACTIONS = 256
LIFETIME = 180
FRAME_SECONDS = 5
MAX_EPOCH = 2**53 - 1
TOKEN = re.compile(r"[0-9a-f]{32}\Z", re.ASCII)
FIELDS = {
    "OBSERVE": {"epoch"}, "SUBMIT_BEGIN": {"epoch", "model", "prompt"},
    "SUBMIT_POLL": set(), "ATTACH": {"correlation"},
    "TAKE": {"correlation"}, "STOP": {"correlation"},
    "WITHDRAW": {"correlation"}, "STEP_BEGIN": set(),
    "STEP_POLL": set(), "CLOSE": set(),
}


class Refusal(ValueError):
    pass


def reject(_):
    raise Refusal()


def pairs(items):
    result = {}
    for key, value in items:
        if key in result or key in ("__proto__", "constructor", "prototype"):
            raise Refusal()
        result[key] = value
    return result


def shape(raw):
    # Depth guard BEFORE JSON allocation; ignore braces inside strings.
    depth = 0
    quoted = escaped = False
    for c in raw:
        if quoted:
            if escaped:
                escaped = False
            elif c == 92:
                escaped = True
            elif c == 34:
                quoted = False
        elif c == 34:
            quoted = True
        elif c in (91, 123):
            depth += 1
            if depth > 4:
                raise Refusal()
        elif c in (93, 125):
            depth -= 1
            if depth < 0:
                raise Refusal()
    if depth or quoted:
        raise Refusal()


def bounded(s, limit):
    if type(s) is not str or not s or len(s) > limit or "\x00" in s:
        return False
    try:
        return len(s.encode("utf-8")) <= limit
    except UnicodeError:
        return False


def epoch(v):
    return type(v) is int and 0 < v <= MAX_EPOCH


def correlation(v):
    return (type(v) is dict and set(v) == {"token"}
            and type(v["token"]) is str and TOKEN.fullmatch(v["token"]) is not None)


def decode(raw, expected):
    if (type(raw) is not bytes or not 1 < len(raw) <= INPUT_CAP
            or raw[-1:] != b"\n" or any(c < 32 or c > 126 for c in raw[:-1])):
        raise Refusal()
    shape(raw[:-1])
    try:
        value = json.loads(raw[:-1], object_pairs_hook=pairs,
                           parse_constant=reject, parse_float=reject)
    except (ValueError, UnicodeError, RecursionError):
        raise Refusal() from None
    if (type(value) is not dict or set(value) != {"seq", "op", "data"}
            or type(value["seq"]) is not int or value["seq"] != expected
            or type(value["op"]) is not str or value["op"] not in FIELDS
            or type(value["data"]) is not dict
            or set(value["data"]) != FIELDS[value["op"]]):
        raise Refusal()
    op, data = value["op"], value["data"]
    if op == "OBSERVE" and data["epoch"] is not None and not epoch(data["epoch"]):
        raise Refusal()
    if op == "SUBMIT_BEGIN" and (not epoch(data["epoch"])
            or not bounded(data["model"], 256) or not bounded(data["prompt"], 4096)):
        raise Refusal()
    if "correlation" in data and not correlation(data["correlation"]):
        raise Refusal()
    return op, data


class Pipe:
    """No unbounded readline, write, queue, or exception output."""
    def __init__(self):
        self.end = time.monotonic() + LIFETIME
        self.total = 0
        os.set_blocking(0, False)
        os.set_blocking(1, False)

    def wait(self, fd, writing, end):
        remaining = min(end, self.end) - time.monotonic()
        if remaining <= 0:
            raise Refusal()
        ready = select.select([] if writing else [fd],
                              [fd] if writing else [], [], remaining)
        if not ready[1 if writing else 0]:
            raise Refusal()

    def charge(self, n):
        self.total += n
        if self.total > TOTAL_CAP:
            raise Refusal()

    def read(self):
        buf = bytearray()
        end = self.end
        while len(buf) < INPUT_CAP:
            self.wait(0, False, end)
            try:
                b = os.read(0, 1)
            except BlockingIOError:
                continue
            if not b:
                if buf:
                    raise Refusal()
                return None
            if not buf:
                end = min(self.end, time.monotonic() + FRAME_SECONDS)
            self.charge(1)
            buf.extend(b)
            if b == b"\n":
                return bytes(buf)
        raise Refusal()

    def write(self, seq, result):
        raw = json.dumps({"seq": seq, "result": result}, ensure_ascii=True,
                         separators=(",", ":"), allow_nan=False).encode("ascii") + b"\n"
        if len(raw) > OUTPUT_CAP:
            raise Refusal()
        self.charge(len(raw))
        end = min(self.end, time.monotonic() + FRAME_SECONDS)
        pending = memoryview(raw)
        while pending:
            self.wait(1, True, end)
            try:
                n = os.write(1, pending)
            except BlockingIOError:
                continue
            if n <= 0:
                raise Refusal()
            pending = pending[n:]


class Worker:
    """Original owner thread only for submit, advance and close."""
    def __init__(self):
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.bridge = self.pool.submit(RealLocalRequestBridge).result(timeout=5)
        self.pending = None
        self.kind = None
        self.attached = False
        self.observed_epoch = None
        self.closed = False

    def command(self, op, data):
        b = self.bridge
        if op in ("SUBMIT_BEGIN", "STEP_BEGIN"):
            if self.pending is not None or (op == "STEP_BEGIN" and not self.attached):
                return "REFUSED"
            self.kind = op
            self.pending = self.pool.submit(
                b.submit, data["model"], data["prompt"], data["epoch"]
            ) if op == "SUBMIT_BEGIN" else self.pool.submit(b.advance)
            return "PENDING"
        if op in ("SUBMIT_POLL", "STEP_POLL"):
            if self.pending is None or self.kind != op.replace("POLL", "BEGIN"):
                return "REFUSED"
            if not self.pending.done():
                return "PENDING"
            future, self.pending = self.pending, None
            self.kind = None
            result = future.result()
            return result if op == "SUBMIT_POLL" else "DONE"
        # A pending submit may hold the bridge lock. Never block control
        # on that lock; parent must retire/reap the exact child on loss.
        if self.kind == "SUBMIT_BEGIN":
            return "PENDING"
        if op == "OBSERVE":
            epoch = data["epoch"]
            result = b.observe(epoch)
            if result and epoch != self.observed_epoch:
                self.attached = False
                self.observed_epoch = epoch
            return result
        if op == "ATTACH":
            result = b.attach(data["correlation"])
            if result:
                self.attached = True
            return result
        if op == "TAKE":
            return b.take(data["correlation"])
        if op == "STOP":
            return b.stop(data["correlation"])
        if op == "WITHDRAW":
            result = b.withdraw(data["correlation"])
            if result:
                self.attached = False
                self.observed_epoch = None
            return result
        if op == "CLOSE":
            if self.pending is not None:
                return "PENDING"
            result = self.pool.submit(b.close).result(timeout=5)
            self.closed = True
            return result
        raise Refusal()

    def dispose(self):
        # No foreign-thread generator close, no replacement or retry.
        # Current native HOLD has no I/O. A future admitted parent must
        # independently enforce whole-process deadline and provider cleanup.
        if self.pending is not None:
            self.pending.result(timeout=5)
        if not self.closed:
            self.pool.submit(self.bridge.close).result(timeout=5)
        self.pool.shutdown(wait=True)


def main():
    if len(sys.argv) != 1:
        return 2
    worker = None
    try:
        pipe = Pipe()
        worker = Worker()
        for seq in range(1, ACTIONS + 1):
            raw = pipe.read()
            if raw is None:
                return 2  # no clean close receipt
            op, data = decode(raw, seq)
            result = worker.command(op, data)
            pipe.write(seq, result)
            if worker.closed:
                return 0
        return 2
    except Exception:
        return 2
    finally:
        if worker is not None:
            try:
                worker.dispose()
            except Exception:
                # Do not pretend an uncertain original is safely retired.
                os._exit(2)


if __name__ == "__main__":
    sys.exit(main())
