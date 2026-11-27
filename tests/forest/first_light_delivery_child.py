"""FL7 test-only child: actual FL5 delivery, actual B2, fixed fake HTTP peer.

One stdin/stdout bounded NDJSON command at a time, no argv settings,
path/model/endpoint/user-content override, native adapter or authority.
Optional independent STOP while one asynchronous STEP is outstanding.
This is still a fixed disposable fixture, not a native service.
"""
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from http.server import ThreadingHTTPServer

from test_ollama_chat_transport import FakeOllama, packet
from first_light_delivery import FirstLightDelivery, DeliveryRefusal
from first_light_trial_host import PROMPT
from ollama_chat_transport import stream_chat

MAX_COMMAND = 512
MAX_EPOCH = 2**31 - 1
MAX_COMMANDS = 64


class ControlRefusal(ValueError):
    pass


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ControlRefusal("INVALID_COMMAND")
        result[key] = value
    return result


class OwnerWorker:
    """One original worker, at most one pending advance; test-only.

    The control thread can observe, take and request STOP during B2 I/O.
    No worker replacement, second queued step, native timeout settlement
    or automatic cancellation on view withdrawal.
    """
    def __init__(self, transport):
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="fl8-owner")
        self.pending = None
        self.closed = False
        try:
            self.delivery = self.executor.submit(
                FirstLightDelivery, test_transport=transport).result()
        except BaseException:
            self.executor.shutdown(wait=True)
            raise

    def call(self, method, *args):
        if self.closed or self.pending is not None:
            raise ControlRefusal("OWNER_STEP_PENDING")
        return self.executor.submit(method, *args).result()

    def begin(self):
        if self.closed or self.pending is not None:
            raise ControlRefusal("OWNER_STEP_PENDING")
        self.pending = self.executor.submit(self.delivery.advance)

    def poll(self):
        if self.pending is None:
            raise ControlRefusal("NO_PENDING_STEP")
        if not self.pending.done():
            return False
        future, self.pending = self.pending, None
        future.result()
        return True

    def dispose(self):
        # Wait for the original fixture step, never close its iterator
        # from the control thread. B2 has its existing finite deadline.
        try:
            if self.pending is not None:
                future, self.pending = self.pending, None
                try:
                    future.result()
                except Exception:
                    pass
            if not self.closed:
                self.call(self.delivery.close)
                self.closed = True
        finally:
            self.executor.shutdown(wait=True)


class Control:
    def __init__(self, owner):
        self.owner = owner
        self.delivery = owner.delivery
        self.epoch = 0
        self.view = None
        self.closed = False

    def current(self, epoch):
        if type(epoch) is not int or epoch != self.epoch or self.view is None:
            raise ControlRefusal("VIEW_UNAVAILABLE")
        return self.view

    def command(self, cmd):
        if type(cmd) is not dict or type(cmd.get("op")) is not str or self.closed:
            raise ControlRefusal("INVALID_COMMAND")
        op = cmd["op"]
        fields = {
            "OBSERVE": {"op", "epoch", "visible"},
            "SUBMIT": {"op", "epoch", "prompt"},
            "TAKE": {"op", "epoch"}, "STOP": {"op", "epoch"},
            "STEP": {"op"}, "STEP_BEGIN": {"op"}, "STEP_POLL": {"op"},
            "OUTCOME": {"op"}, "CLOSE": {"op"},
        }
        if op not in fields or set(cmd) != fields[op]:
            raise ControlRefusal("INVALID_COMMAND")
        if op == "OBSERVE":
            epoch = cmd["epoch"]
            if (type(epoch) is not int or not self.epoch < epoch <= MAX_EPOCH
                    or type(cmd["visible"]) is not bool):
                raise ControlRefusal("VIEW_UNAVAILABLE")
            self.epoch = epoch
            self.view = object() if cmd["visible"] else None
            self.delivery.observe_view(self.view)
            return {"ok": True, "epoch": epoch}
        if op == "SUBMIT":
            view = self.current(cmd["epoch"])
            if type(cmd["prompt"]) is not str or cmd["prompt"] != PROMPT:
                raise ControlRefusal("PUBLIC_INPUT_MISMATCH")
            self.owner.call(self.delivery.submit, view, PROMPT)
            return {"ok": True}  # not admission or draft consumption
        if op == "TAKE":
            snapshot = self.delivery.take(self.current(cmd["epoch"]))
            return {"ok": True, "epoch": self.epoch,
                    "snapshot": asdict(snapshot) if snapshot is not None else None}
        if op == "STOP":
            ack = self.delivery.request_stop(self.current(cmd["epoch"]))
            return {"ok": True, "ack": ack}
        if op == "STEP":
            self.owner.call(self.delivery.advance)
            return {"ok": True}
        if op == "STEP_BEGIN":
            self.owner.begin()
            return {"ok": True}  # queued, not completion
        if op == "STEP_POLL":
            return {"ok": True, "done": self.owner.poll()}
        if op == "OUTCOME":
            status, local = self.owner.call(self.delivery.owner_outcome)
            return {"ok": True, "status": status, "local_outcome": local}
        local = self.owner.call(self.delivery.close)
        self.owner.closed = True
        self.closed = True
        return {"ok": True, "local_outcome": local}


def main():
    if len(sys.argv) != 1:
        return 2

    class Peer(FakeOllama):
        pass

    Peer.lines = [packet("RE"), packet("ADY", done=True)]
    Peer.observed = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), Peer)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    endpoint = "http://127.0.0.1:%d" % server.server_address[1]

    def transport(**kw):
        kw["endpoint"] = endpoint
        yield from stream_chat(**kw)

    owner = OwnerWorker(transport)
    control = Control(owner)
    try:
        for _ in range(MAX_COMMANDS):
            line = sys.stdin.buffer.readline(MAX_COMMAND + 1)
            if not line:
                return 0
            if len(line) > MAX_COMMAND or not line.endswith(b"\n"):
                return 2  # do not process suffix of an oversized line
            try:
                cmd = json.loads(line.decode("utf-8"), object_pairs_hook=pairs,
                                 parse_constant=lambda _: None)
                reply = control.command(cmd)
            except (ValueError, UnicodeError, RecursionError, DeliveryRefusal):
                reply = {"ok": False, "error": "COMMAND_REFUSED"}
            except Exception:
                # Do not leak diagnostics or pretend uncertainty is safe retry.
                return 2
            print(json.dumps(reply, ensure_ascii=True, separators=(",", ":")),
                  flush=True)
            if control.closed:
                return 0
        return 2
    finally:
        try:
            owner.dispose()
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)


if __name__ == "__main__":
    sys.exit(main())
