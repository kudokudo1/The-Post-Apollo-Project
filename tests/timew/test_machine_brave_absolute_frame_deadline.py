#!/usr/bin/env python3
"""MACHINE // cumulative frame deadline with real partial socket traffic.

No Brave, archives, C3e/C5 credentials, service install, live Hospital
registration, or production machine access. A valid in-flight guard does
NOT authorize metadata access; the actual broker stays deny-only.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import socket
import struct
import sys
import threading
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"services/time"))
import MachineBraveRequestCancellation as cancel
import MachineBraveProcessLease as lifecycle
import MachineBraveProtectedMetadataContract as broker

REQUEST = {"kind":broker.REQUEST_KIND,"action":broker.LIST,
           "challenge":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}


def wire(obj):
    raw=json.dumps(obj,sort_keys=True,separators=(",",":")).encode("ascii")
    return struct.pack("=I",len(raw))+raw


def pair():
    receiver,sender=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)
    receiver.settimeout(3.0)
    peer=broker.peer_credentials(receiver)
    lease=lifecycle.capture_socket_peer(receiver,peer=peer)
    guard=cancel.begin(receiver,lease)
    return receiver,sender,lease,guard


def cleanup(receiver,sender,lease,guard):
    guard.cancel()
    lease.close()
    receiver.close()
    sender.close()


def reject(action):
    try:
        action()
    except (broker.BrokerRefusal,TimeoutError):
        return
    raise AssertionError("UNBOUNDED OR STALE FRAME ACCEPTED")


def test_complete_frame():
    a,b,lease,guard=pair()
    try:
        b.sendall(wire(REQUEST))
        original=a.gettimeout()
        raw,parsed=broker.read_frame(a,guard=guard)
        assert parsed==REQUEST
        assert raw==wire(REQUEST)[4:]
        assert a.gettimeout()==original
        assert guard.valid() is True
        assert broker.REFUSED["client_authenticated"] is False
        assert broker.REFUSED["restore_allowed"] is False
    finally:
        cleanup(a,b,lease,guard)


def test_compatible_unguarded_reader():
    a,b,lease,guard=pair()
    try:
        b.sendall(wire(REQUEST))
        raw,parsed=broker.read_frame(a)  # existing test/fixture compatibility
        assert parsed==REQUEST
        assert raw==wire(REQUEST)[4:]
        assert guard.valid() is True
    finally:
        cleanup(a,b,lease,guard)


def test_trickle_cumulative_timeout():
    # This is a real socket slowly feeding one byte at a time. The client
    # sends often enough to reset conventional per-read socket timeouts,
    # but cannot extend the *one* 0.30s monotonic request lifetime.
    with patch.object(cancel,"MAX_GUARD_NS",300_000_000):
        a,b,lease,guard=pair()
        try:
            stream=wire(REQUEST)
            def drip():
                for byte in stream[:12]:
                    time.sleep(0.07)
                    try:
                        b.sendall(bytes([byte]))
                    except OSError:
                        return
            worker=threading.Thread(target=drip,daemon=True)
            worker.start()
            before=time.monotonic()
            reject(lambda:broker.read_frame(a,guard=guard))
            elapsed=time.monotonic()-before
            assert 0.15<=elapsed<0.9,elapsed
            assert guard.valid() is False  # sticky cancellation
            assert a.gettimeout()==3.0
        finally:
            cleanup(a,b,lease,guard)
            worker.join(timeout=2.0)


def test_idle_first_byte_timeout():
    with patch.object(cancel,"MAX_GUARD_NS",90_000_000):
        a,b,lease,guard=pair()
        try:
            before=time.monotonic()
            reject(lambda:broker.read_frame(a,guard=guard))
            assert time.monotonic()-before<0.6
            assert guard.valid() is False
            assert a.gettimeout()==3.0
        finally:
            cleanup(a,b,lease,guard)


def test_fragmented_fast_frame_passes_negative_check():
    a,b,lease,guard=pair()
    try:
        data=wire(REQUEST)
        def feed():
            for part in (data[:2],data[2:4],data[4:11],data[11:]):
                time.sleep(0.01)
                b.sendall(part)
        worker=threading.Thread(target=feed,daemon=True)
        worker.start()
        raw,parsed=broker.read_frame(a,guard=guard)
        worker.join(timeout=1)
        assert not worker.is_alive()
        assert parsed==REQUEST
        assert guard.valid() is True
        # "valid" means no cancellation reason, not "grant archive access".
        assert broker.REFUSED["status"]=="request_rejected"
    finally:
        cleanup(a,b,lease,guard)


def test_context_drift_during_header():
    a,b,lease,guard=pair()
    try:
        b.sendall(wire(REQUEST))
        original=guard._initial
        class DriftSocket:
            def __init__(self,socket_):
                self.sock=socket_
                self.received=False
            def gettimeout(self):
                return self.sock.gettimeout()
            def settimeout(self,value):
                return self.sock.settimeout(value)
            def recv(self,count):
                part=self.sock.recv(count)
                self.received=True
                return part
        wrapped=DriftSocket(a)
        def context(_pid):
            return (replace(original,session_id=original.session_id+1)
                    if wrapped.received else original)
        with patch.object(cancel,"_session_context",side_effect=context):
            reject(lambda:broker.read_frame(wrapped,guard=guard))
        assert guard.valid() is False
        assert a.gettimeout()==3.0
    finally:
        cleanup(a,b,lease,guard)


def test_hard_frame_bound_and_eof():
    a,b,lease,guard=pair()
    try:
        b.sendall(struct.pack("=I",broker.MAX_REQUEST+1))
        reject(lambda:broker.read_frame(a,guard=guard))
        assert a.gettimeout()==3.0
    finally:
        cleanup(a,b,lease,guard)
    a,b,lease,guard=pair()
    try:
        b.sendall(b"\x04\x00")
        b.shutdown(socket.SHUT_WR)
        reject(lambda:broker.read_frame(a,guard=guard))
        assert guard.valid() is False
    finally:
        cleanup(a,b,lease,guard)


def test_ingress_stays_closed():
    source=(ROOT/"services/time/MachineBraveProtectedMetadataContract.py").read_text()
    handler=source.split("def handle_once(",1)[1].split(
        '\n\nif __name__ == "__main__":',1)[0]
    assert "read_frame(connection, guard=guard)" in handler
    assert handler.count("guard.valid()")>=2
    assert "metadata_from_protected_root(" not in handler
    assert "test_only_grant" not in handler
    assert "return False" in handler
    assert broker.REFUSED["operator_consent_verified"] is False
    guard_source=(ROOT/"services/time/MachineBraveRequestCancellation.py").read_text()
    assert "def receiving_valid(self)" in guard_source
    assert "def remaining_ns(self)" in guard_source
    assert "MAX_GUARD_NS" in guard_source
    assert "return MAX_GUARD_NS - age" in guard_source


def main():
    assert sys.platform.startswith("linux")
    test_complete_frame()
    test_compatible_unguarded_reader()
    test_trickle_cumulative_timeout()
    test_idle_first_byte_timeout()
    test_fragmented_fast_frame_passes_negative_check()
    test_context_drift_during_header()
    test_hard_frame_bound_and_eof()
    test_ingress_stays_closed()
    print("MACHINE absolute request budget: slow trickle, idle, partial bytes, midstream drift and deny-only PASS")


if __name__=="__main__":
    main()
