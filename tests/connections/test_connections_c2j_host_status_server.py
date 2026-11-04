#!/usr/bin/env python3
"""C2j explicit host-status server uses C2i protocol without trusting a peer."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "services/connections/ConnectionsHostStatusServer.py"
CLIENT = ROOT / "services/connections/ConnectionsHostStatusInspect.py"


def load(name: str, file: Path):
    spec = importlib.util.spec_from_file_location(name, file)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


h = load("c2j_host_status", SERVER)
c = load("c2i_host_probe", CLIENT)


def check(value: dict, status: str, state: str = "") -> None:
    assert value == {
        "status": status, "provider": "nasa-firms", "state": state,
        "hostAuthenticated": False, "credentialPresent": False,
        "grantActive": False, "canApprove": False,
    }, value


def client_child(runtime: Path, status: str, state: str = "") -> None:
    r = subprocess.run(
        [sys.executable, "-B", str(CLIENT)],
        env={"PATH": os.environ.get("PATH", ""),
             "XDG_RUNTIME_DIR": str(runtime)},
        capture_output=True, text=True, timeout=5)
    assert r.returncode == 0, (r.returncode, r.stderr)
    assert r.stderr == ""
    check(json.loads(r.stdout), status, state)


def raw_query(path: Path, payload: bytes) -> bytes:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(2)
        sock.connect(str(path))
        sock.sendall(payload)
        return sock.recv(1024)


def main():
    assert h.NAME == c.SOCKET_NAME == "connections-status-v1.sock"
    assert h.SUBDIR == c.RUNTIME_DIRNAME == "post-apollo"
    assert h.SCHEMA == c.SCHEMA
    assert h.QUERY == c.REQUEST == b"STATUS V1\n"
    assert h.MAX_WIRE <= c.MAX_FRAME
    assert "if __name__ == \"__main__\"" in SERVER.read_text()
    assert "C2J_REFUSED_AUTOSTART_NO_HOST_OWNER" in SERVER.read_text()
    standalone = subprocess.run(
        [sys.executable, "-B", str(SERVER)],
        capture_output=True, text=True, timeout=3)
    assert standalone.returncode != 0
    assert "REFUSED_AUTOSTART" in standalone.stderr

    # Constructing a class cannot spawn a service or write to HOME.
    with tempfile.TemporaryDirectory(prefix="postapollo-c2j-", dir="/tmp") as temp:
        root = Path(temp)
        root.chmod(0o700)
        states = {"current": "IDLE"}
        callback = lambda: states["current"]
        probe_env = {"XDG_RUNTIME_DIR": str(root)}
        check(c.probe(env=probe_env), "HOST_NOT_FOUND")
        obj = h.ConnectionsHostStatusServer(runtime_directory=root,
                                             status_provider=callback)
        assert not (root / h.SUBDIR).exists()
        assert obj._server is None and obj._thread is None
        try:
            obj.start()
            endpoint = obj.socket_path
            assert endpoint.is_socket()
            assert endpoint.lstat().st_uid == os.geteuid()
            assert (endpoint.lstat().st_mode & 0o077) == 0
            assert (endpoint.parent.lstat().st_mode & 0o077) == 0
            assert c.probe(env=probe_env)["status"] == "OBSERVED_UNVERIFIED"
            client_child(root, "OBSERVED_UNVERIFIED", "IDLE")
            for state in ("PENDING", "APPROVED", "DENIED", "CANCELLED",
                          "EXPIRED", "COMPLETED", "FAILED"):
                states["current"] = state
                check(c.probe(env=probe_env), "OBSERVED_UNVERIFIED", state)
                if state == "APPROVED":
                    client_child(root, "OBSERVED_UNVERIFIED", "APPROVED")

            # A spoofed arbitrary state is downgraded; no access claims.
            for invalid in ("CONNECTED", "__proto__", 1, None, {}, []):
                states["current"] = invalid
                check(c.probe(env=probe_env), "OBSERVED_UNVERIFIED", "IDLE")
            def broken():
                raise RuntimeError("provider fault")
            obj._provider = broken
            check(c.probe(env=probe_env), "OBSERVED_UNVERIFIED", "IDLE")
            obj._provider = callback
            states["current"] = "PENDING"

            assert raw_query(endpoint, b"APPROVE\n") == b""
            assert raw_query(endpoint, b"REVOKE\n") == b""
            assert raw_query(endpoint, b"STATUS V1\nextra") == b""
            assert raw_query(endpoint, b"STATUS V1\n") == (
                b'{"schema":"post-apollo.connections.status.v1",'
                b'"provider":"nasa-firms","state":"PENDING","readonly":true}\n')
            # A second instance cannot replace a live endpoint.
            other = h.ConnectionsHostStatusServer(
                runtime_directory=root, status_provider=lambda:"IDLE")
            try:
                try:
                    other.start()
                except FileExistsError:
                    pass
                else:
                    raise AssertionError("SERVER_OVERWROTE_SOCKET")
            finally:
                other.close()
            assert endpoint.is_socket()
            check(c.probe(env=probe_env), "OBSERVED_UNVERIFIED", "PENDING")
        finally:
            obj.close()
        obj.close()  # idempotent
        assert not (root / h.SUBDIR).exists()
        check(c.probe(env=probe_env), "HOST_NOT_FOUND")
        try:
            obj.start()
        except RuntimeError:
            pass
        else:
            raise AssertionError("CLOSED_HOST_RESTARTED")

        # Runtime owner and symlinks are rejected.
        root.chmod(0o755)
        try:
            h.ConnectionsHostStatusServer(
                runtime_directory=root, status_provider=callback)
        except ValueError:
            pass
        else:
            raise AssertionError("INSECURE_RUNTIME_ACCEPTED")
        root.chmod(0o700)
        linked = root / h.SUBDIR
        linked.symlink_to("/tmp")
        suspect = h.ConnectionsHostStatusServer(
            runtime_directory=root, status_provider=callback)
        try:
            suspect.start()
        except ValueError:
            pass
        else:
            raise AssertionError("SYMLINKED_DIRECTORY_ACCEPTED")
        finally:
            suspect.close()
        assert linked.is_symlink()
        linked.unlink()
        assert not any(root.iterdir())
    print("C2J_PASS // EXPLICIT_SERVER_C2I_PROTOCOL_UNVERIFIED_STATES_AND_CLEANUP")


if __name__ == "__main__":
    main()
