#!/usr/bin/env python3
"""MACHINE peer lifecycle negative evidence: real pidfd, exit and exec tests.

Only local synthetic UNIX sockets and ephemeral child subprocesses. No
production host, browser, archive data, service install or file migration.
"""
from __future__ import annotations

from dataclasses import replace
import errno
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"services/time"))
import MachineBraveProcessLease as lifecycle
import MachineBraveProtectedMetadataContract as broker

def peer(pid):
    return SimpleNamespace(pid=pid,uid=os.getuid(),gid=os.getgid())

def refused(fn,*args,**kwargs):
    try:
        fn(*args,**kwargs)
    except lifecycle.LifecycleRefusal:
        return
    raise AssertionError("INVALID PROCESS LEASE WAS ACCEPTED")

def child_main(path,mode):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
        client.connect(path)
        client.sendall(b"READY")
        command=client.recv(1)
        if command!=b"G":
            return 4
        if mode=="exit":
            return 0
        if mode=="exec":
            # PID survives exec, while exe inode/dev changes. This must
            # invalidate the original Python executable fingerprint.
            os.execv("/bin/sleep",["sleep","5"])
        return 5

def launch_case(path,mode):
    listener=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    try:
        listener.bind(str(path))
        listener.listen(1)
        child=subprocess.Popen([
            sys.executable,"-B","-I",str(Path(__file__).resolve()),
            "--child",str(path),mode],
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        try:
            listener.settimeout(5)
            conn,_=listener.accept()
            with conn:
                conn.settimeout(5)
                assert conn.recv(5)==b"READY"
                actual=broker.peer_credentials(conn)
                assert actual.pid==child.pid
                assert actual.uid==os.getuid()
                assert actual.gid==os.getgid()
                lease=lifecycle.capture_socket_peer(conn,peer=actual)
                try:
                    assert lease.identity.pid==child.pid
                    assert lease.identity.start_ticks>0
                    assert lease.valid()
                    if mode=="exit":
                        conn.sendall(b"G")
                        assert child.wait(timeout=4)==0
                        assert lease.valid() is False
                        assert lease.valid() is False
                    elif mode=="exec":
                        expected=os.stat("/bin/sleep")
                        assert (expected.st_dev,expected.st_ino)!=(
                            lease.identity.exe_device,lease.identity.exe_inode)
                        conn.sendall(b"G")
                        saw_exec=False
                        deadline=time.monotonic()+2.0
                        while time.monotonic()<deadline:
                            try:
                                current=os.stat(f"/proc/{child.pid}/exe")
                                if (current.st_dev,current.st_ino)==(
                                        expected.st_dev,expected.st_ino):
                                    saw_exec=True
                                    break
                            except OSError:
                                pass
                            time.sleep(0.01)
                        assert saw_exec,"child never changed executable"
                        assert child.poll() is None,"child unexpectedly exited"
                        assert lease.valid() is False
                    else:
                        raise AssertionError("unknown mode")
                finally:
                    lease.close()
                    lease.close()
                assert lease.valid() is False
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=3)
            assert not child.stderr.read(), "unexpected synthetic child stderr"
            child.stdout.close()
            child.stderr.close()
    finally:
        listener.close()
        path.unlink(missing_ok=True)

def same_process_checks():
    a,b=socket.socketpair()
    try:
        # Socketpair peer credentials are our own process.
        actual=broker.peer_credentials(a)
        assert actual.pid==os.getpid()
        assert actual.uid==os.getuid()
        assert actual.gid==os.getgid()
        with lifecycle.capture_socket_peer(a,peer=actual) as lease:
            assert lease.valid() is True
            first=lease.identity
            assert first.pid==os.getpid()
            assert first.uid==os.getuid()
            assert first.gid==os.getgid()
            assert len(first.uid_fields)==4 and first.uid_fields[1]==actual.uid
            assert len(first.gid_fields)==4 and first.gid_fields[1]==actual.gid
            # Changing any pinned real/saved/fs credential is negative even
            # when the effective socket credential stays unchanged.
            with patch.object(lifecycle,"_identity",
                              return_value=replace(first,uid_fields=(
                                  first.uid_fields[0]+1,*first.uid_fields[1:]))):
                assert lease.valid() is False
            with patch.object(lifecycle,"_identity",
                              return_value=replace(first,gid_fields=(
                                  first.gid_fields[0]+1,*first.gid_fields[1:]))):
                assert lease.valid() is False
            # Live process is invalidated on task starttime mismatch
            with patch.object(lifecycle,"_identity",
                              return_value=replace(first,start_ticks=first.start_ticks+1)):
                assert lease.valid() is False
            # Re-exec into a different binary inode is a negative signal.
            with patch.object(lifecycle,"_identity",
                              return_value=replace(first,exe_inode=first.exe_inode+1)):
                assert lease.valid() is False
            # UID/GID changes also invalidate even if PID still exists.
            with patch.object(lifecycle,"_identity",
                              return_value=replace(first,uid=first.uid+1)):
                assert lease.valid() is False
            with patch.object(lifecycle,"_identity",
                              return_value=replace(first,gid=first.gid+1)):
                assert lease.valid() is False
            # Missing /proc information cannot establish liveness.
            with patch.object(lifecycle,"_identity",
                              side_effect=lifecycle.LifecycleRefusal("gone")):
                assert lease.valid() is False
            # Negative/backward monotonic clock or expiry fail closed.
            with patch.object(lifecycle.time,"monotonic_ns",
                              return_value=lease._born_ns-1):
                assert lease.valid() is False
            with patch.object(lifecycle.time,"monotonic_ns",
                              return_value=lease._born_ns+lifecycle.MAX_LEASE_NS):
                assert lease.valid() is False
            assert lease.valid() is True
        assert lease.valid() is False
    finally:
        a.close()
        b.close()

def unsupported_and_parser_checks():
    class Unsupported:
        def getsockopt(self,*_args):
            raise OSError(errno.ENOPROTOOPT,"SO_PEERPIDFD missing")
    refused(lifecycle.capture_socket_peer,Unsupported(),peer=peer(os.getpid()))
    assert lifecycle._pidfd_alive(-1) is False
    refused(lifecycle.capture_socket_peer,Unsupported(),
            peer=SimpleNamespace(pid=True,uid=os.getuid(),gid=os.getgid()))
    refused(lifecycle.capture_socket_peer,Unsupported(),
            peer=SimpleNamespace(pid=os.getpid(),uid=-1,gid=os.getgid()))
    refused(lifecycle.capture_socket_peer,Unsupported(),
            peer=SimpleNamespace(pid=os.getpid(),uid=os.getuid(),gid="wrong"))

    # The comm field contains a parenthesis, proving rfind(") ") handles
    # nontrivial process names without shifting field #22.
    values=[b"S"]+[b"0"]*18+[b"123456"]+[b"0"]*5
    odd=b"1234 (has ) paren) "+b" ".join(values)+b"\n"
    with patch.object(lifecycle,"_read_bytes",return_value=odd):
        assert lifecycle._start_ticks(1234)==123456
    with patch.object(lifecycle,"_read_bytes",return_value=b"1234 (malformed) S\n"):
        refused(lifecycle._start_ticks,1234)

    # No vulnerable post-hoc os.pidfd_open(pid) fallback and NO runtime grant.
    lifecycle_src=(ROOT/"services/time/MachineBraveProcessLease.py").read_text()
    broker_src=(ROOT/"services/time/MachineBraveProtectedMetadataContract.py").read_text()
    handler=broker_src.split("def handle_once(",1)[1].split(
        '\n\nif __name__ == "__main__":',1)[0]
    assert "os.pidfd_open(" not in lifecycle_src.split("from __future__",1)[1]
    assert "SO_PEERPIDFD" in lifecycle_src
    assert "lifecycle.capture_socket_peer(" in handler
    assert handler.count("guard.valid()")>=2
    assert "cancellation.begin(connection, lease)" in handler
    assert "metadata_from_protected_root(" not in handler
    assert "test_only_grant" not in handler
    assert "return False" in handler
    assert broker.REFUSED["restore_allowed"] is False

def main():
    assert sys.platform.startswith("linux")
    assert hasattr(socket,"SO_PEERCRED")
    same_process_checks()
    unsupported_and_parser_checks()
    with tempfile.TemporaryDirectory(prefix="machine-peerlease-ci-") as name:
        root=Path(name)
        assert root.parent==Path("/tmp")
        launch_case(root/"exit.sock","exit")
        launch_case(root/"exec.sock","exec")
    print("MACHINE kernel peerpidfd lease: live, exit, changed exe, stale/invalid proc, TTL, deny-only PASS")

if __name__=="__main__":
    if len(sys.argv)==4 and sys.argv[1]=="--child":
        sys.exit(child_main(sys.argv[2],sys.argv[3]))
    assert len(sys.argv)==1
    main()
