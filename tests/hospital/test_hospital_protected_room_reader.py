#!/usr/bin/env python3
"""Hospital protected Room/Bin read client source contract and socket fixture.

Exercises only disposable AF_UNIX SOCK_STREAM socketpairs. Real root-owned
policy, separate UID service, native install and operator consent are NOT
provided by these tests.
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
NATIVE = ROOT / "services/hospital/native/hospital_room_read_client.py"
BIN = (ROOT / "services/hospital/HospitalRoomBinService.qml").read_text()
SERVICE = (ROOT / "services/hospital/HospitalRoomLifecycleService.qml").read_text()
CLIENT = NATIVE.read_text()

loader=importlib.machinery.SourceFileLoader("hospital_protected_room_reader_fixture",str(NATIVE))
spec=importlib.util.spec_from_loader(loader.name,loader)
reader=importlib.util.module_from_spec(spec)
loader.exec_module(reader)

def guard(marker,source,label):
    assert marker in source, label+": "+marker

for marker in (
    '#!/usr/bin/python3 -I',
    'CLIENT = Path("/usr/libexec/post-apollo/hospital/hospital-room-read")',
    'CONFIG = Path("/etc/post-apollo/hospital/room-read-client.json")',
    'SOCKET_NAME = "hospital-room-writer-v1.sock"',
    'socket.SO_PEERCRED',
    'socket.SOCK_STREAM',
    'getattr(os, "O_NOFOLLOW"',
    'os.getuid() != os.geteuid()',
    'info.st_uid != writer_uid',
    'current_peer = _peer(s, writer_uid)',
    '"operation": "review"',
    '"operation": "bin"',
):
    guard(marker,CLIENT,"fixed protected read transport")
for forbidden in ("getenv(", "setenv(", "eval(", "subprocess.",
                  "os.system(", "sqlite3", "signedEnvelope", "BURN_ALL",
                  "room-lifecycle-trash", "room-lifecycle-restore"):
    assert forbidden not in CLIENT, "read client must not expose "+forbidden

for marker in (
    'nativeReadPath, "review", id',
    'HOSPITAL BACKEND NOT READY',
    'readonly property string nativeReadPath',
):
    guard(marker,SERVICE,"Hospital Room source reader")
for marker in (
    '"/usr/libexec/post-apollo/hospital/hospital-room-read"',
    '"bin"',
    'PROTECTED BIN READER UNAVAILABLE',
    'item.burnAllowed === false',
):
    guard(marker,BIN,"Hospital Trash++ source reader")
assert 'room-lifecycle-review' not in SERVICE
assert 'room-lifecycle-bin' not in BIN
assert 'px="$HOME/' not in SERVICE+BIN

def fixture(operation, room=None, *, response=None, result_expected=True):
    a,b=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)
    a.settimeout(3)
    b.settimeout(3)
    got={}
    def server():
        try:
            data=bytearray()
            while True:
                chunk=b.recv(8192)
                if not chunk: break
                data.extend(chunk)
            got["request"]=bytes(data)
            if response is not None:
                b.sendall(response)
        finally:
            b.close()
    worker=threading.Thread(target=server,daemon=True)
    worker.start()
    failed=False
    result=None
    try:
        result=reader._exchange(a,operation,room,os.getuid())
    except reader.BackendHold:
        failed=True
    finally:
        a.close()
        worker.join(timeout=3)
    assert not worker.is_alive(), "fixture thread stuck"
    assert failed != result_expected, (operation, failed, result)
    return got.get("request",b""),result

rev={
    "roomId":"room-fixture","state":"ACTIVE","revision":0,
    "digest":"a"*64,"blockers":[],"canTrash":True,
    "canRestore":False,"canBurn":False,"operatorAuthenticated":False,
    "requiresOwnerReview":True,
}
entry={
    "roomId":"room-fixture","state":"TRASHED","revision":1,
    "kind":"HOSPITAL ROOM","burnAllowed":False,
}

def wire(data):
    return json.dumps({"ok":True,"data":data},
                      separators=(",",":"),sort_keys=True).encode()+b"\n"

request,value=fixture("review","room-fixture",response=wire(rev))
assert value==rev
assert json.loads(request)=={
    "schema":"post-apollo.hospital.protected-room-writer.v1",
    "operation":"review","roomId":"room-fixture"
}
request,value=fixture("bin",None,response=wire([entry]))
assert value==[entry]
assert json.loads(request)=={
    "schema":"post-apollo.hospital.protected-room-writer.v1",
    "operation":"bin",
}

for bad in (
    wire({**rev,"roomId":"different"}),
    wire({**rev,"digest":"z"*64}),
    wire({**rev,"operatorAuthenticated":True}),
    wire({**rev,"canBurn":True}),
    wire({"roomId":"room-fixture"}),
    wire([entry]), # bin list is not valid Room review
    b'{"ok":true,"data":{},"data":{}}\n', # duplicate key
    b'{"ok":false,"error":"DENIED"}\n',
    b'{"ok":true,"data":{}}\n\n',
    b'{"ok":true,"data":{}}\nTRAILER',
):
    fixture("review","room-fixture",response=bad,result_expected=False)
for bad in (
    wire([{**entry,"burnAllowed":True}]),
    wire([{**entry,"roomId":"invalid ROOM"}]),
    wire([{**entry,"state":"ACTIVE"}]),
    wire(rev),
):
    fixture("bin",None,response=bad,result_expected=False)
assert not reader.valid_room("A B")
assert not reader.valid_room("not\\safe")
assert reader.valid_room("room.test/01")
try:
    reader._exchange(None,"trash","room-fixture",os.getuid())
except reader.BackendHold:
    pass
else:
    raise AssertionError("Read-only client accepted trash request")
try:
    reader._exchange(None,"bin","room-fixture",os.getuid())
except reader.BackendHold:
    pass
else:
    raise AssertionError("Bin accepted untrusted Room argument")

# No native install, and no config/socket bypass in local source. This
# must refuse before opening any live PX database or invoking another CLI.
trial=subprocess.run([sys.executable,"-I",str(NATIVE),"bin"],
                     text=True,capture_output=True,timeout=6)
assert trial.returncode != 0
assert "HOSPITAL BACKEND NOT READY" in trial.stderr
assert "hospital.db" not in trial.stdout+trial.stderr
print("HOSPITAL PROTECTED ROOM READER // PASS // source-only, exact read/bin, guarded peer, no legacy fallback")
