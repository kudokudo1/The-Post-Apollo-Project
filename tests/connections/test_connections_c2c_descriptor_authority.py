#!/usr/bin/env python3
"""C2c fake-only process-level descriptor authority integration acceptance."""
from __future__ import annotations
import json
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import time

SCRIPT = (pathlib.Path(__file__).resolve().parent /
          "fixtures/C2cDescriptorBroker.py")
CORRECT = {"op": "read", "consumer": "weather-earth", "provider": "nasa-firms",
           "operation": "fires.hotspots.read", "profile": "ci-only-profile"}
APPROVE = {"op": "approve", "approved": True, "provider": "nasa-firms",
           "operation": "fires.hotspots.read", "profile": "ci-only-profile",
           "ttlMs": 5000}


def exchange(sock: socket.socket, data: dict) -> dict:
    sock.sendall(json.dumps(data, separators=(",", ":")).encode())
    raw = sock.recv(8192)
    if not raw:
        raise AssertionError("CONTROL_SOCKET_DISCONNECTED")
    return json.loads(raw)


class HostSession:
    def __init__(self, env: dict):
        self.env = env
        self.ctrl_host, ctrl_broker = socket.socketpair(
            socket.AF_UNIX, socket.SOCK_SEQPACKET)
        client_host, client_broker = socket.socketpair(
            socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.ctrl_host.settimeout(4)
        self.broker = subprocess.Popen(
            [sys.executable, "-B", str(SCRIPT), "--broker",
             str(ctrl_broker.fileno()), str(client_broker.fileno())],
            pass_fds=(ctrl_broker.fileno(), client_broker.fileno()),
            close_fds=True, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env, text=True)
        ctrl_broker.close()
        client_broker.close()
        self.client = subprocess.Popen(
            [sys.executable, "-B", str(SCRIPT), "--client",
             str(client_host.fileno()), "0"],
            pass_fds=(client_host.fileno(),), close_fds=True,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=env, text=True, bufsize=1)
        client_host.close()

    def operator(self, message):
        return exchange(self.ctrl_host, message)

    def weather(self, message):
        assert self.client.stdin and self.client.stdout
        self.client.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        self.client.stdin.flush()
        raw = self.client.stdout.readline()
        assert raw, "CLIENT_DISCONNECTED"
        return json.loads(raw)

    def close(self):
        try:
            if self.broker.poll() is None:
                try: self.operator({"op": "shutdown"})
                except (OSError, ConnectionError): pass
        finally:
            self.ctrl_host.close()
            if self.client.stdin: self.client.stdin.close()
            try: self.client.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.client.kill()
                self.client.wait(timeout=3)
            if self.broker.poll() is None:
                try: self.broker.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.broker.kill()
                    self.broker.wait(timeout=3)
            assert self.broker.returncode == 0, "BROKER_NOT_CLEAN"
            assert self.client.returncode == 0, "CLIENT_NOT_CLEAN"
            assert self.broker.stdout and self.broker.stdout.read() == "", "BROKER_STDOUT_NOT_EMPTY"
            assert self.broker.stderr and self.broker.stderr.read() == "", "BROKER_STDERR_NOT_EMPTY"
            assert self.client.stderr and self.client.stderr.read() == "", "CLIENT_STDERR_NOT_EMPTY"


def assert_denied(actual, reason):
    assert actual == {"ok": False, "reason": reason}, (actual, reason)


def main():
    absent = subprocess.run(
        [sys.executable, "-B", str(SCRIPT), "--broker", "8", "9"],
        env={"HOME": "/tmp/nope", "GITHUB_ACTIONS": "false"},
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
    assert absent.returncode == 2
    assert absent.stdout.strip() == "REFUSED_C2C_PRIVATE_FIXTURE_REQUIRED"
    assert absent.stderr == ""
    with tempfile.TemporaryDirectory(
            prefix="postapollo-c2c-ci-", dir="/tmp") as temp:
        root = pathlib.Path(temp)
        home = root / "home"
        home.mkdir(mode=0o700)
        marker = root / ".ci-only-authority"
        marker.write_text("C2C_PRIVATE_SOCKETPAIR_ONLY\n")
        marker.chmod(0o600)
        env = os.environ.copy()
        env.update({"HOME": str(home), "GITHUB_ACTIONS": "true",
                    "POST_APOLLO_C2C_FAKE_ONLY": "1"})
        env.pop("POST_APOLLO_FIRMS_MAP_KEY", None)
        bad_fd = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--client", "9999", "0"],
            env=env, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=3)
        assert bad_fd.returncode == 2
        assert bad_fd.stdout.strip() == "REFUSED_C2C_INVALID_DESCRIPTOR"
        session = HostSession(env)
        try:
            assert_denied(session.weather(CORRECT), "NO_OPERATOR_GRANT")
            assert_denied(session.weather({"op": "approve", **APPROVE}),
                          "CLIENT_CANNOT_APPROVE_OR_REVOKE")
            assert_denied(session.weather({"op": "revoke"}),
                          "CLIENT_CANNOT_APPROVE_OR_REVOKE")
            assert_denied(session.operator({**APPROVE, "approved": False}),
                          "OPERATOR_DID_NOT_APPROVE")
            assert_denied(session.operator({**APPROVE, "operation": "mail.send"}),
                          "INVALID_APPROVAL_SCOPE")
            assert_denied(session.operator({**APPROVE, "ttlMs": True}),
                          "INVALID_APPROVAL_SCOPE")
            assert_denied(session.operator({**APPROVE, "ttlMs": 60001}),
                          "INVALID_APPROVAL_SCOPE")
            assert_denied(session.weather(CORRECT), "NO_OPERATOR_GRANT")
            assert session.operator(APPROVE) == {
                "ok": True, "result": "APPROVED_FAKE_ONLY_ONE_SHOT"}
            assert_denied(session.weather({**CORRECT, "consumer": "social-mail"}),
                          "CONSUMER_CLAIM_MISMATCH")
            assert_denied(session.weather({**CORRECT, "provider": "proton-mail"}),
                          "CROSS_PROVIDER_OR_OPERATION")
            assert_denied(session.weather({**CORRECT, "operation": "mail.send"}),
                          "CROSS_PROVIDER_OR_OPERATION")
            assert_denied(session.weather({**CORRECT, "profile": "other-profile"}),
                          "PROFILE_MISMATCH")
            assert_denied(session.weather(
                {**CORRECT, "url": "https://example.test"}),
                "CLIENT_FIELDS_REJECTED")
            success = session.weather(CORRECT)
            assert success["ok"] is True
            assert success["kind"] == "SYNTHETIC_FIRE_HOTSPOTS"
            assert len(success["observations"]) == 2
            assert all(x["synthetic"] is True
                       for x in success["observations"])
            assert "C2C_SYNTHETIC_NEVER" not in json.dumps(success)
            assert_denied(session.weather(CORRECT), "NO_OPERATOR_GRANT")
            assert session.operator(APPROVE)["ok"] is True
            assert session.operator({"op": "revoke"})["ok"] is True
            assert_denied(session.weather(CORRECT), "NO_OPERATOR_GRANT")
            assert session.operator({**APPROVE, "ttlMs": 10})["ok"] is True
            time.sleep(0.05)
            assert_denied(session.weather(CORRECT), "GRANT_EXPIRED")
        finally:
            session.close()
        second = HostSession(env)
        try:
            assert_denied(second.weather(CORRECT), "NO_OPERATOR_GRANT")
        finally:
            second.close()
        assert sorted(x.name for x in root.iterdir()) == [
            ".ci-only-authority", "home"]
        assert not any(home.iterdir()), "HOME_WRITTEN_BY_FAKE_BROKER"
    print("C2C_PASS // PRIVATE_DESCRIPTOR_HOST_GRANT_FAKE_NASA_AND_RESTART_REFUSAL")


if __name__ == "__main__":
    main()
