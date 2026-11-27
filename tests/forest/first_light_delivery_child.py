"""FL7 test-only child: actual FL5 delivery, actual B2, fixed fake HTTP peer.

One stdin/stdout bounded NDJSON command at a time, no argv settings,
path/model/endpoint/user-content override, native adapter or authority.
This synchronous stepped fixture is not a native asynchronous service.
"""
import json
import sys
import threading
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


class Control:
    def __init__(self, delivery):
        self.delivery = delivery
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
            "STEP": {"op"}, "OUTCOME": {"op"}, "CLOSE": {"op"},
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
            self.delivery.submit(view, PROMPT)
            return {"ok": True}  # not admission or draft consumption
        if op == "TAKE":
            snapshot = self.delivery.take(self.current(cmd["epoch"]))
            return {"ok": True, "epoch": self.epoch,
                    "snapshot": asdict(snapshot) if snapshot is not None else None}
        if op == "STOP":
            ack = self.delivery.request_stop(self.current(cmd["epoch"]))
            return {"ok": True, "ack": ack}
        if op == "STEP":
            self.delivery.advance()
            return {"ok": True}
        if op == "OUTCOME":
            status, local = self.delivery.owner_outcome()
            return {"ok": True, "status": status, "local_outcome": local}
        local = self.delivery.close()
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

    control = Control(FirstLightDelivery(test_transport=transport))
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
            if not control.closed:
                control.delivery.close()
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)


if __name__ == "__main__":
    sys.exit(main())
