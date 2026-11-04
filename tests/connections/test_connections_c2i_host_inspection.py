#!/usr/bin/env python3
"""C2i read-only local Connections socket probe tests, no user runtime touched."""
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
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
FILE = ROOT / "services/connections/ConnectionsHostStatusInspect.py"
spec = importlib.util.spec_from_file_location("c2i_status_inspect", FILE)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

FIXED = {
    "schema":m.SCHEMA, "provider":"nasa-firms", "state":"PENDING",
    "readonly": True,
}
FIELDS = {
    "status", "provider", "state", "hostAuthenticated",
    "credentialPresent", "grantActive", "canApprove",
}


def assert_safe(result: dict, status: str, state: str = "") -> None:
    assert set(result) == FIELDS, result
    assert result["status"] == status, result
    assert result["provider"] == "nasa-firms"
    assert result["state"] == state
    for name in ("hostAuthenticated","credentialPresent","grantActive","canApprove"):
        assert result[name] is False, result


def serve_once(folder: Path, response: bytes, got: list[bytes]) -> tuple[socket.socket, threading.Thread]:
    endpoint = folder / m.SOCKET_NAME
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(endpoint))
    os.chmod(endpoint, 0o600)
    server.listen(1)
    server.settimeout(4)

    def work():
        with server:
            try:
                conn, _ = server.accept()
                with conn:
                    conn.settimeout(2)
                    got.append(conn.recv(128))
                    conn.sendall(response)
            finally:
                endpoint.unlink(missing_ok=True)

    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    return server, thread


def check_real_host(root: Path, response: bytes, expected_status: str,
                    state: str = "") -> None:
    folder = root / m.RUNTIME_DIRNAME
    folder.mkdir(mode=0o700, exist_ok=True)
    received = []
    _server, thread = serve_once(folder, response, received)
    value = m.probe(env={"XDG_RUNTIME_DIR":str(root)})
    assert_safe(value, expected_status, state)
    thread.join(timeout=3)
    assert not thread.is_alive()
    assert received == [m.REQUEST], received
    assert not (folder / m.SOCKET_NAME).exists()


def main() -> None:
    no_env = m.probe(env={})
    assert_safe(no_env, "RUNTIME_UNAVAILABLE")
    assert_safe(m.probe(env={"XDG_RUNTIME_DIR":"relative/path"}), "RUNTIME_UNAVAILABLE")
    assert m.REQUEST == b"STATUS V1\n"
    assert m.SOCKET_NAME == "connections-status-v1.sock"
    assert m.RUNTIME_DIRNAME == "post-apollo"
    for item in (
        {"schema":m.SCHEMA,"provider":"nasa-firms","state":"APPROVED",
         "readonly":True},
        {"schema":m.SCHEMA,"provider":"proton-mail","state":"PENDING",
         "readonly":True},
        {"schema":m.SCHEMA,"provider":"nasa-firms","state":"PENDING",
         "readonly":True,"secret":"DO_NOT_DISPLAY"},
        {"schema":m.SCHEMA,"provider":"nasa-firms","state":"CONNECTED",
         "readonly":True},
        {"schema":m.SCHEMA,"provider":"nasa-firms","state":"PENDING",
         "readonly":1},
    ):
        status = "OBSERVED_UNVERIFIED" if (item["provider"]=="nasa-firms"
                    and item["state"]=="APPROVED"
                    and set(item)==set(FIXED)) else "RESPONSE_INVALID"
        assert_safe(m._normalize(json.dumps(item).encode()), status,
                    "APPROVED" if status=="OBSERVED_UNVERIFIED" else "")
    for raw in (b"not-json",b"[]",b"{}",b"null",b"[]\x00"):
        assert_safe(m._normalize(raw), "RESPONSE_INVALID")

    with tempfile.TemporaryDirectory(prefix="postapollo-c2i-inspect-",dir="/tmp") as temp:
        root = Path(temp)
        os.chmod(root,0o700)
        env = {"XDG_RUNTIME_DIR":str(root)}
        assert_safe(m.probe(env=env), "HOST_NOT_FOUND")
        assert not (root / m.RUNTIME_DIRNAME).exists()

        # A symlink cannot substitute a private runtime directory.
        linked = root / m.RUNTIME_DIRNAME
        linked.symlink_to("/tmp")
        assert_safe(m.probe(env=env), "RUNTIME_UNSAFE")
        linked.unlink()

        check_real_host(root, json.dumps(FIXED).encode()+b"\n",
                        "OBSERVED_UNVERIFIED","PENDING")
        check_real_host(root, json.dumps({**FIXED,"state":"APPROVED"}).encode()+b"\n",
                        "OBSERVED_UNVERIFIED","APPROVED")
        check_real_host(root, json.dumps({**FIXED,"token":"SECRET"}).encode()+b"\n",
                        "RESPONSE_INVALID")
        check_real_host(root, b"{" + b"x"*m.MAX_FRAME + b"}\n",
                        "RESPONSE_INVALID")
        assert_safe(m.probe(env=env), "HOST_NOT_FOUND")

        # A world-accessible runtime directory and socket are refused.
        folder = root / m.RUNTIME_DIRNAME
        folder.chmod(0o755)
        assert_safe(m.probe(env=env), "RUNTIME_UNSAFE")
        folder.chmod(0o700)

        # A same-UID socket does not prove host identity.
        assert_safe(m.result("OBSERVED_UNVERIFIED","APPROVED"),
                    "OBSERVED_UNVERIFIED","APPROVED")
        assert not list(root.glob("**/*.json")), "TEST_CREATED_CREDENTIAL_FILE"

    source = FILE.read_text()
    for forbidden in ("secret-tool", "gnome-keyring-daemon",
                      "POST_APOLLO_FIRMS_MAP_KEY","https://", "http://",
                      "subprocess.Popen", "subprocess.run","socket.AF_INET",
                      ".bind(", ".listen(", "os.mkdir(", "os.makedirs("):
        assert forbidden not in source, forbidden
    assert "SO_PEERCRED" in source
    assert "sock.sendall(REQUEST)" in source
    assert "MAX_DURATION = 1.5" in source
    assert "hostAuthenticated" in source
    assert "False" in source

    cli = subprocess.run(
        [sys.executable,"-B",str(FILE)],
        env={"PATH":os.environ.get("PATH","")},capture_output=True,
        text=True,timeout=3)
    assert cli.returncode == 0
    assert_safe(json.loads(cli.stdout),"RUNTIME_UNAVAILABLE")
    assert cli.stderr == ""
    print("C2I_PASS // PRIVATE_SOCKET_READONLY_NO_AUTH_OR_CREDENTIAL_GRANTS")


if __name__ == "__main__":
    main()
