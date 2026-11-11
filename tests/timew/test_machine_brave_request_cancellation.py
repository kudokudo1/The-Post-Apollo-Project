#!/usr/bin/env python3
"""MACHINE // negative-only in-flight cancellation and Linux session drift CI.

Tests use temporary Unix sockets and real disposable subprocesses, not Brave,
a logind seat, a system service, user archives or any production identity.
"""
from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"services/time"))
import MachineBraveRequestCancellation as cancel
import MachineBraveProcessLease as lifecycle
import MachineBraveProtectedMetadataContract as broker

REQUEST={
    "kind":broker.REQUEST_KIND,
    "action":broker.LIST,
    "challenge":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
}

def frame(payload):
    raw=json.dumps(payload,sort_keys=True,separators=(",",":")).encode()
    return struct.pack("=I",len(raw))+raw

def sockets():
    a,b=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)
    peer=broker.peer_credentials(a)
    lease=lifecycle.capture_socket_peer(a,peer=peer)
    guard=cancel.begin(a,lease)
    return a,b,lease,guard

def close_all(a,b,lease,guard):
    guard.cancel()
    lease.close()
    a.close()
    b.close()

def test_live_and_disconnect():
    a,b,lease,guard=sockets()
    try:
        # A first request may already be buffered during preflight.
        b.sendall(frame(REQUEST))
        raw,parsed=broker.read_frame(a)
        assert parsed==REQUEST
        assert guard.valid() is True
        assert lease.valid() is True
        # Half-closing the client's write direction cancels a request
        # even if it could still read a reply.
        b.shutdown(socket.SHUT_WR)
        assert guard.valid() is False
        assert guard.valid() is False   # cancellation sticks
    finally:
        close_all(a,b,lease,guard)

    a,b,lease,guard=sockets()
    try:
        assert guard.valid() is True
        b.close()                       # peer EOF
        assert guard.valid() is False
    finally:
        close_all(a,b,lease,guard)

def test_one_request_only():
    a,b,lease,guard=sockets()
    try:
        b.sendall(frame(REQUEST)+b"SECOND-REQUEST")
        raw,parsed=broker.read_frame(a)
        assert parsed==REQUEST
        # No pipelined extra messages are allowed after first frame.
        assert guard.valid() is False
    finally:
        close_all(a,b,lease,guard)

def test_expiry_and_revocation():
    a,b,lease,guard=sockets()
    try:
        original=guard._initial
        assert original.session_id==os.getsid(os.getpid())
        assert len(original.cgroup_sha256)==64
        assert original.user_ns_inode>0 and original.pid_ns_inode>0
        assert guard.valid() is True
        for changed in (
            replace(original,session_id=original.session_id+1),
            replace(original,cgroup_sha256="0"*64),
            replace(original,pid_ns_inode=original.pid_ns_inode+1),
            replace(original,user_ns_device=original.user_ns_device+1),
        ):
            with patch.object(cancel,"_session_context",return_value=changed):
                assert guard.valid() is False
            # A revoked guard cannot become valid again.
            assert guard.valid() is False
            # New test-only instance, still tied to same socket+lease.
            guard=cancel.begin(a,lease)
        assert guard.valid() is True
        with patch.object(cancel.time,"monotonic_ns",
                          return_value=guard._born_ns+cancel.MAX_GUARD_NS):
            assert guard.valid() is False
        assert guard.valid() is False
        guard=cancel.begin(a,lease)
        with patch.object(cancel.time,"monotonic_ns",
                          return_value=guard._born_ns-1):
            assert guard.valid() is False
        guard=cancel.begin(a,lease)
        with patch.object(cancel,"_session_context",
                          side_effect=cancel.CancelledRequest("proc unavailable")):
            assert guard.valid() is False
        guard=cancel.begin(a,lease)
        with patch.object(cancel,"_socket_still_waiting",return_value=False):
            assert guard.valid() is False
        guard=cancel.begin(a,lease)
        with patch.object(lease,"valid",return_value=False):
            assert guard.valid() is False
    finally:
        close_all(a,b,lease,guard)

def child(path):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
        connection.connect(path)
        connection.sendall(b"READY")
        instruction=connection.recv(1)
        if instruction!=b"S":
            return 3
        # Real session state change without process exit/executable change.
        os.setsid()
        connection.sendall(b"CHANGED")
        connection.recv(1)
    return 0

def test_actual_session_change():
    with tempfile.TemporaryDirectory(prefix="machine-session-drift-test-") as root:
        path=Path(root)/"session.sock"
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as listener:
            listener.bind(str(path))
            listener.listen(1)
            process=subprocess.Popen([
                sys.executable,"-B","-I",str(Path(__file__).resolve()),
                "--child",str(path),
            ],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
              stderr=subprocess.PIPE)
            try:
                listener.settimeout(5)
                connection,_=listener.accept()
                with connection:
                    connection.settimeout(5)
                    assert connection.recv(5)==b"READY"
                    peer=broker.peer_credentials(connection)
                    assert peer.pid==process.pid
                    with lifecycle.capture_socket_peer(connection,peer=peer) as lease:
                        guard=cancel.begin(connection,lease)
                        assert guard.valid() is True
                        sid_before=guard._initial.session_id
                        connection.sendall(b"S")
                        assert connection.recv(7)==b"CHANGED"
                        assert os.getsid(process.pid)!=sid_before
                        assert lease.valid() is True
                        assert guard.valid() is False
                        # No resurrection when the process is still running.
                        assert guard.valid() is False
                        connection.sendall(b"X")
                        guard.cancel()
                assert process.wait(timeout=3)==0
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=3)
                err=process.stderr.read()
                assert err==b"",err.decode(errors="replace")
                process.stdout.close()
                process.stderr.close()

def test_invalid_input_and_broker_boundary():
    for value in (True,0,-1,"123",None):
        try:
            cancel._session_context(value)
        except cancel.CancelledRequest:
            pass
        else:
            raise AssertionError("Invalid session PID accepted")
    with patch.object(cancel.os,"getsid",side_effect=OSError("restricted")):
        try:
            cancel._session_context(os.getpid())
        except cancel.CancelledRequest:
            pass
        else:
            raise AssertionError("Unavailable session state accepted")

    source=(ROOT/"services/time/MachineBraveProtectedMetadataContract.py").read_text()
    handler=source.split("def handle_once(",1)[1].split(
        '\n\nif __name__ == "__main__":',1)[0]
    assert "cancellation.begin(connection, lease)" in handler
    assert handler.count("guard.valid()")>=2
    assert "guard.cancel()" in handler
    assert "metadata_from_protected_root(" not in handler
    assert "test_only_grant" not in handler
    assert "return False" in handler
    assert broker.REFUSED["restore_allowed"] is False
    assert broker.REFUSED["client_authenticated"] is False
    assert broker.REFUSED["operator_consent_verified"] is False
    assert not hasattr(cancel,"grant") and not hasattr(cancel,"authorize")

def main():
    assert sys.platform.startswith("linux")
    assert hasattr(socket,"SO_PEERCRED")
    test_live_and_disconnect()
    test_one_request_only()
    test_expiry_and_revocation()
    test_actual_session_change()
    test_invalid_input_and_broker_boundary()
    print("MACHINE in-flight cancellation: EOF, half-close, extra frames, real setsid, context drift, TTL and deny-only PASS")

if __name__=="__main__":
    if len(sys.argv)==3 and sys.argv[1]=="--child":
        sys.exit(child(sys.argv[2]))
    assert len(sys.argv)==1
    main()
