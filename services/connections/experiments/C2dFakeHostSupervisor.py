#!/usr/bin/env python3
"""C2d disposable host supervisor for the C2c descriptor experiment.

FAKE-ONLY. Not imported by QML, not installed, never runs in production.
The trusted test harness creates channels, starts the exact broker and fake
Weather executables, keeps the operator endpoint, revokes and reaps children.
No public socket, real provider, disk credential, keyring or ambient user data.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import selectors
import socket
import subprocess
import sys

BROKER_SCRIPT = (Path(__file__).resolve().parents[3] /
                 "tests/connections/fixtures/C2cDescriptorBroker.py")
MAX_PACKET = 4096
REQUEST = {
    "op": "read", "consumer": "weather-earth", "provider": "nasa-firms",
    "operation": "fires.hotspots.read", "profile": "ci-only-profile",
}
GRANT = {
    "op": "approve", "approved": True, "provider": "nasa-firms",
    "operation": "fires.hotspots.read", "profile": "ci-only-profile",
    "ttlMs": 5000,
}
DENIED = {"ok": False, "reason": "HOST_NOT_READY"}


def _guard() -> None:
    """Recheck the C2c CI-only guard, also before subprocess creation."""
    spec = importlib.util.spec_from_file_location("c2c_fixture_guard", BROKER_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("C2D_C2C_SOURCE_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not module.allowed_fixture():
        raise RuntimeError("C2D_PRIVATE_FAKE_FIXTURE_REQUIRED")


def _child_env() -> dict[str, str]:
    """No ambient OAuth, key material, desktop or arbitrary Python injection."""
    safe = ("HOME", "PATH", "LANG", "LC_ALL",
            "GITHUB_ACTIONS", "POST_APOLLO_C2C_FAKE_ONLY")
    return {key: os.environ[key] for key in safe if key in os.environ}


class FakeConnectionsHost:
    """Single-use owner of one Weather client and one C2c broker.

    A caller-supplied consumer string is never used to select an executable.
    Host controls two separate anonymous descriptors, then closes child ends
    immediately after passing only the permitted FD to each child.
    """

    def __init__(self) -> None:
        self._broker: subprocess.Popen | None = None
        self._weather: subprocess.Popen | None = None
        self._control: socket.socket | None = None
        self._state = "STOPPED"
        self._ever_started = False

    @property
    def state(self) -> str:
        return self._state

    @property
    def pids(self) -> tuple[int, ...]:
        return tuple(p.pid for p in (self._broker, self._weather) if p is not None)

    def start(self) -> str:
        if self._ever_started or self._state != "STOPPED":
            return "REFUSED_C2D_RESTART_INSTANCE"
        _guard()  # Never start real programs or touch a personal desktop.
        self._ever_started = True

        host_op = broker_op = host_weather = broker_weather = None
        try:
            host_op, broker_op = socket.socketpair(
                socket.AF_UNIX, socket.SOCK_SEQPACKET)
            host_weather, broker_weather = socket.socketpair(
                socket.AF_UNIX, socket.SOCK_SEQPACKET)
            host_op.settimeout(2)
            self._control = host_op
            # Deliberately fixed executable and arguments.
            self._broker = subprocess.Popen(
                [sys.executable, "-B", str(BROKER_SCRIPT), "--broker",
                 str(broker_op.fileno()), str(broker_weather.fileno())],
                pass_fds=(broker_op.fileno(), broker_weather.fileno()),
                close_fds=True,
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, env=_child_env(), text=True)
            broker_op.close()
            broker_op = None
            broker_weather.close()
            broker_weather = None

            self._weather = subprocess.Popen(
                [sys.executable, "-B", str(BROKER_SCRIPT), "--client",
                 str(host_weather.fileno()), "0"],
                pass_fds=(host_weather.fileno(),),
                close_fds=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, env=_child_env(),
                text=True, bufsize=1)
            host_weather.close()
            host_weather = None
            # A fixed, harmless command confirms broker starts and can answer
            # on the exclusive host control channel.
            response = self._control_exchange({"op": "ready_probe"})
            if response != {"ok": False, "reason": "HOST_ACTION_UNKNOWN"}:
                raise RuntimeError("C2D_BROKER_DID_NOT_START")
            if self._weather.poll() is not None:
                raise RuntimeError("C2D_CLIENT_DID_NOT_START")
            self._state = "READY"
            return "C2D_FAKE_RUNTIME_READY"
        except (OSError, RuntimeError, ValueError, TimeoutError):
            self.stop()
            return "REFUSED_C2D_START_FAILURE"
        finally:
            for endpoint in (broker_op, broker_weather, host_weather):
                if endpoint is not None:
                    endpoint.close()

    def _control_exchange(self, message: dict) -> dict:
        if self._control is None or self._broker is None:
            raise RuntimeError("C2D_HOST_CHANNEL_UNAVAILABLE")
        if self._broker.poll() is not None:
            raise RuntimeError("C2D_BROKER_EXITED")
        raw = json.dumps(message, separators=(",", ":")).encode()
        if len(raw) > MAX_PACKET:
            raise ValueError("C2D_MESSAGE_TOO_LARGE")
        self._control.sendall(raw)
        received = self._control.recv(MAX_PACKET + 1)
        if not received or len(received) > MAX_PACKET:
            raise RuntimeError("C2D_CONTROL_REPLY_INVALID")
        result = json.loads(received)
        if not isinstance(result, dict):
            raise ValueError("C2D_NON_OBJECT_REPLY")
        return result

    def _live(self) -> bool:
        return (self._state == "READY"
                and self._broker is not None and self._broker.poll() is None
                and self._weather is not None and self._weather.poll() is None)

    def approve(self, *, confirmed: bool, ttl_ms: int = 5000) -> dict:
        """Simulation only: never accept a Weather-supplied approval."""
        if not self._live():
            self.stop()
            return DENIED.copy()
        if confirmed is not True or type(ttl_ms) is not int:
            return {"ok": False, "reason": "OPERATOR_APPROVAL_REQUIRED"}
        try:
            return self._control_exchange({**GRANT, "ttlMs": ttl_ms})
        except (OSError, ValueError, RuntimeError, TimeoutError):
            self.stop()
            return DENIED.copy()

    def revoke(self) -> dict:
        if not self._live():
            self.stop()
            return DENIED.copy()
        try:
            return self._control_exchange({"op": "revoke"})
        except (OSError, ValueError, RuntimeError, TimeoutError):
            self.stop()
            return DENIED.copy()

    def read_fake_hotspots(self, request: dict | None = None) -> dict:
        """Send on client's stdin; receive only sanitized JSON from stdout.

        This harness is NOT an arbitrary untrusted request interface: tests
        can supply malformed requests for negative cases, no URLs or secrets.
        """
        if not self._live():
            self.stop()
            return DENIED.copy()
        assert self._weather is not None
        if not isinstance(request, dict):
            request = REQUEST.copy()
        message = json.dumps(request, separators=(",", ":"))
        if len(message.encode()) > MAX_PACKET:
            return {"ok": False, "reason": "CLIENT_FIELDS_REJECTED"}
        try:
            assert self._weather.stdin is not None
            assert self._weather.stdout is not None
            self._weather.stdin.write(message + "\n")
            self._weather.stdin.flush()
            # A crashed/misbehaving client must not hang its owner indefinitely.
            # Read bounded bytes. TextIO.readline after a partial write
            # could block despite selector readiness on a broken client.
            payload = bytearray()
            while b"\n" not in payload and len(payload) <= MAX_PACKET:
                with selectors.DefaultSelector() as selector:
                    selector.register(self._weather.stdout, selectors.EVENT_READ)
                    if not selector.select(timeout=2):
                        raise TimeoutError("C2D_CLIENT_TIMED_OUT")
                chunk = os.read(self._weather.stdout.fileno(), MAX_PACKET + 1 - len(payload))
                if not chunk:
                    raise RuntimeError("C2D_CLIENT_DISCONNECTED")
                payload.extend(chunk)
            if len(payload) > MAX_PACKET or not payload.endswith(b"\n"):
                raise RuntimeError("C2D_CLIENT_REPLY_INVALID")
            response = json.loads(payload.decode("utf-8"))
            if not isinstance(response, dict):
                raise ValueError("C2D_NON_OBJECT_CLIENT_RESPONSE")
            return response
        except (OSError, ValueError, RuntimeError, TimeoutError):
            self.stop()
            return DENIED.copy()

    def stop(self) -> str:
        # Idempotent. All grants are lost when the broker is shut down.
        if self._state == "CLOSED":
            return "C2D_ALREADY_CLOSED"
        if self._control is not None and self._broker is not None:
            if self._broker.poll() is None:
                for cmd in ({"op": "revoke"}, {"op": "shutdown"}):
                    try:
                        self._control_exchange(cmd)
                    except (OSError, ValueError, RuntimeError, TimeoutError):
                        break
            self._control.close()
            self._control = None
        for process in (self._weather, self._broker):
            if process is None:
                continue
            if process.stdin is not None and not process.stdin.closed:
                process.stdin.close()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1)
            for stream in (process.stdout, process.stderr):
                if stream is not None:
                    stream.close()
        self._state = "CLOSED"
        return "C2D_FAKE_RUNTIME_STOPPED"

    def __enter__(self):
        if self.start() != "C2D_FAKE_RUNTIME_READY":
            raise RuntimeError("C2D_HOST_START_REFUSED")
        return self

    def __exit__(self, *_):
        self.stop()


def main() -> int:
    # Never auto-start when imported or run from an actual desktop terminal.
    if len(sys.argv) != 2 or sys.argv[1] != "--fake-self-check":
        print("REFUSED_C2D_NOT_A_PRODUCTION_LAUNCHER")
        return 2
    try:
        with FakeConnectionsHost() as host:
            first = host.read_fake_hotspots()
            assert first == {"ok": False, "reason": "NO_OPERATOR_GRANT"}
            assert host.approve(confirmed=True)["ok"] is True
            result = host.read_fake_hotspots()
            assert result.get("kind") == "SYNTHETIC_FIRE_HOTSPOTS"
            assert all(row["synthetic"] for row in result["observations"])
        print("C2D_PASS // PRIVATE_HOST_SUPERVISOR_FAKE_ONLY")
        return 0
    except (RuntimeError, OSError, AssertionError, KeyError):
        print("REFUSED_C2D_HOST_TEST")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
