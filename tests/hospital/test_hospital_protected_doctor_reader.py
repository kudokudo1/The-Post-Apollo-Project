#!/usr/bin/env python3
"""H1 protected Doctor directory client: exact native request, no write path.

Source-only, disposable Linux socketpair test. No root-owned installation,
Hospital SQLite, real Doctor roster, socket service or desktop changes.
The protected PX parser is pinned to an exact Hospital #133 Git head.
"""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "services/hospital/native/hospital_room_read_client.py"
PINNED_PX = ROOT / "px-h1-doctor-source/bin/px_hospital_room_writer.py"
assert PINNED_PX.is_file(), "EXACT_PX_H1_SOURCE_REQUIRED"
source = CLIENT.read_text(encoding="utf-8")
for marker in (
    '#!/usr/bin/python3 -I',
    'CLIENT = Path("/usr/libexec/post-apollo/hospital/hospital-room-read")',
    'CONFIG = Path("/etc/post-apollo/hospital/room-read-client.json")',
    'socket.SO_PEERCRED',
    'getattr(os, "O_NOFOLLOW"',
    'elif operation == "doctor-directory" and room_id is None:',
    '"operation": "doctor-directory"',
    'MAX_DOCTORS = 250',
    'set(row) != DOCTOR_FIELDS',
):
    assert marker in source, "MISSING_PROTECTED_SOURCE_CONTRACT: " + marker
for forbidden in (
    "sqlite3", "subprocess.", "getenv(", "execve(", "os.system(",
    "signedEnvelope", "BURN_ALL", "store-command", "doctor-put",
):
    assert forbidden not in source, "READ_CLIENT_PRIVILEGED_SURFACE: " + forbidden

loader = importlib.machinery.SourceFileLoader("hospital_h1_doctor_reader", str(CLIENT))
spec = importlib.util.spec_from_loader(loader.name, loader)
reader = importlib.util.module_from_spec(spec)
loader.exec_module(reader)

sys.path.insert(0, str(PINNED_PX.parent))
from px_hospital_room_writer import parse_request

RESPONSE_SCHEMA = "post-apollo.hospital.protected-room-writer.v1"
def good_doctor(identifier="doctor-1"):
    return {
        "id": identifier,
        "name": "Doctor Fixture",
        "role": "DOCTOR",
        "status": "ACTIVE",
        "createdAt": "2026-01-01 00:00:00",
        "updatedAt": "2026-01-01 00:00:00",
    }

def wire(data):
    return json.dumps(
        {"ok": True, "data": data}, sort_keys=True,
        separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii") + b"\n"

def fixture(*, response, operation="doctor-directory", room_id=None,
            succeeds=True):
    client, owner = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(3)
    owner.settimeout(3)
    received = {}
    def server():
        try:
            request = bytearray()
            while True:
                chunk = owner.recv(8192)
                if not chunk:
                    break
                request.extend(chunk)
            received["raw"] = bytes(request)
            if response is not None:
                owner.sendall(response)
        finally:
            owner.close()
    worker = threading.Thread(target=server, daemon=True)
    worker.start()
    error = None
    result = None
    try:
        result = reader._exchange(client, operation, room_id, os.getuid())
    except reader.BackendHold as exc:
        error = str(exc)
    finally:
        client.close()
        worker.join(timeout=3)
    assert not worker.is_alive(), "SOCKET_FIXTURE_THREAD_STUCK"
    assert (error is None) == succeeds, (error, result)
    return received.get("raw", b""), result

raw, doctors = fixture(response=wire([good_doctor()]))
assert doctors == [good_doctor()]
expected = {"schema": RESPONSE_SCHEMA, "operation": "doctor-directory"}
assert json.loads(raw) == expected
assert raw.endswith(b"\n") and raw.count(b"\n") == 1
assert parse_request(raw) == expected, "PX_WRITER_REJECTED_PINNED_DOCTOR_ACTION"
assert "doctor-directory" in source
assert fixture(response=wire([]))[1] == []
assert len(fixture(response=wire([good_doctor(str(i)) for i in range(250)]))[1]) == 250

# Malformed and overbroad replies fail closed, not silently truncated.
mutations = [
    {**good_doctor(), "argv": ["doctor-put"]},
    {**good_doctor(), "status": "UNREVIEWED"},
    {**good_doctor(), "id": ""},
    {**good_doctor(), "id": "x" * 161},
    {**good_doctor(), "name": "x" * 1025},
    {**good_doctor(), "name": "bad\x00name"},
    {**good_doctor(), "role": 4},
    {**good_doctor(), "createdAt": None},
]
for row in mutations:
    fixture(response=wire([row]), succeeds=False)
for invalid in (
    [good_doctor(), good_doctor()],
    [good_doctor(str(i)) for i in range(251)],
    {"id": "doctor-1"},
    "NOT A DIRECTORY",
):
    fixture(response=wire(invalid), succeeds=False)
for malformed in (
    b'{"ok":true,"data":[],"data":[]}\n',
    b'{"ok":false,"error":"DENIED"}\n',
    wire([]) + b"TRAILER",
    wire([]) + b"\n",
):
    fixture(response=malformed, succeeds=False)

# Exact command shape. No object IDs, status filters, SQL or writer mutation.
for argv in (
    ["doctor-directory", "--status", "ACTIVE"],
    ["doctor-directory", "doctor-1"],
    ["doctor-put", "doctor-1"],
    ["bin", "doctor-directory"],
    ["sql"],
    ["trash", "room-1"],
):
    try:
        reader.main(argv)
    except reader.BackendHold:
        pass
    else:
        raise AssertionError("CLIENT_ACCEPTED_UNREVIEWED_ARGUMENTS: " + str(argv))
for op, room in (("doctor-directory", "room-1"),
                 ("doctor-put", None), ("trash", "room-1")):
    try:
        reader._exchange(None, op, room, os.getuid())
    except reader.BackendHold:
        pass
    else:
        raise AssertionError("UNREVIEWED_SOCKET_OPERATION")

# Even valid command syntax cannot run as an uninstalled source file.
trial = subprocess.run(
    [sys.executable, "-I", str(CLIENT), "doctor-directory"],
    capture_output=True, text=True, timeout=6,
)
assert trial.returncode != 0
assert "HOSPITAL BACKEND NOT READY" in trial.stderr
assert "hospital.db" not in trial.stdout + trial.stderr

print(
    "HOSPITAL H1 DOCTOR NATIVE READ // PASS // exact pinned PX action, "
    "250-row bound, hostile response refusal, no write/SQL/CLI fallback, "
    "NO NATIVE INSTALL"
)
