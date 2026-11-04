#!/usr/bin/env python3
"""C2a read-only Secret Service probe unit tests; no live keyring contact."""
from __future__ import annotations
from dataclasses import dataclass
import importlib.util
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[2]
source = root / "services/connections/ConnectionsSecretServiceProbe.py"
spec = importlib.util.spec_from_file_location("ConnectionsSecretServiceProbe", source)
assert spec and spec.loader
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

@dataclass
class Output:
    stdout: str
    returncode: int = 0

def exercise(text: str, returncode: int = 0) -> dict:
    commands = []
    def run(args, **kwargs):
        commands.append((args, kwargs))
        return Output(text, returncode)
    result = p.probe(which=lambda x: "/usr/bin/gdbus", run=run)
    assert len(commands) == 1
    args, kwargs = commands[0]
    assert tuple(args) == p.QUERY
    assert args[3] == "org.freedesktop.DBus"
    assert args[-1] == "org.freedesktop.secrets"
    assert "org.freedesktop.secrets" not in args[0:8]
    assert kwargs == {
        "capture_output": True, "text": True,
        "timeout": 4, "check": False,
    }
    assert set(result) == {
        "status","serviceAcquired","keyringUnlocked","credentialPresent",
        "providerAuthenticated","permissionGranted"
    }
    for field in ("keyringUnlocked","credentialPresent",
                  "providerAuthenticated","permissionGranted"):
        assert result[field] is False
    return result

assert exercise("(true,)") == {
    "status":"SERVICE_ACQUIRED","serviceAcquired":True,
    "keyringUnlocked":False,"credentialPresent":False,
    "providerAuthenticated":False,"permissionGranted":False,
}
assert exercise(" ( false , ) ")["status"] == "SERVICE_NOT_RUNNING"
assert exercise("(maybe,)")["status"] == "UNEXPECTED_DBUS_RESPONSE"
assert exercise("proton@example.test\n(secret)")["status"] == "UNEXPECTED_DBUS_RESPONSE"
assert exercise("(true,)", 1)["status"] == "SESSION_BUS_UNAVAILABLE"

no_tool_calls = []
r = p.probe(which=lambda x: None,
            run=lambda *args,**kwargs: no_tool_calls.append(1))
assert r["status"] == "DBUS_PROBE_TOOL_MISSING" and not no_tool_calls

def timeout(*args,**kwargs):
    raise subprocess.TimeoutExpired("gdbus",4)
assert p.probe(which=lambda x: "/usr/bin/gdbus",run=timeout)["status"] == "SESSION_BUS_UNAVAILABLE"

text = source.read_text(encoding="utf8")
for forbidden in ("secret-tool","--dest org.freedesktop.secrets","Unlock(",
                  "ReadAlias(","SearchItems(","SetSecret(","OpenSession("):
    assert forbidden not in text, forbidden
assert "NameHasOwner" in text
assert "timeout=4" in text
print("C2a Secret Service read-only host probe safety and status contract: PASS")
