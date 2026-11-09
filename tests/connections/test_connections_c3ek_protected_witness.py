#!/usr/bin/env python3
"""C3e-K: Linux DAC-protected witness and kernel sender tests (CI only).

Run ONLY in a disposable GitHub Ubuntu runner using `sudo -n python3 -B`.
This is not a production service installer or a workstation procedure.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "tests/connections/c3e_release_trust"
SERVER = HERE / "C3eProtectedWitnessPeer.py"

CLIENT = r'''
import json, os, socket, subprocess, sys
print("READY", flush=True)
request = json.loads(sys.stdin.readline())
if request["op"] == "direct":
    allowed = False
    try:
        with open(request["witness"], "rb") as src:
            src.read(1)
        allowed = True
    except (PermissionError, FileNotFoundError):
        pass
    print(json.dumps({"direct_read": allowed}), flush=True)
    sys.exit(0)
sock = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
sock.settimeout(5)
sock.connect(request["socket"])
operation = request["op"]
if operation == "forward":
    program = ("import socket,sys; s=socket.socket(fileno=int(sys.argv[1]));"
               "s.sendall(b'WITNESS-FLOOR-READ-V1');"
               "print(s.recv(4096).decode()); s.close()")
    child = subprocess.run([sys.executable, "-c", program, str(sock.fileno())],
                           pass_fds=(sock.fileno(),), stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, text=True, timeout=6, check=True)
    raw = child.stdout.strip()
else:
    data = b'WITNESS-FLOOR-READ-V1'
    if operation == "write":
        data = b'WRITE-FLOOR-V1'
    if operation == "oversized":
        data += b'X' * 300
    sock.sendall(data)
    raw = sock.recv(4096).decode()
sock.close()
print(json.dumps({"reply":json.loads(raw)}), flush=True)
'''


def kernel_start(pid):
    raw = Path("/proc/%d/stat" % pid).read_text()
    return raw.rsplit(") ", 1)[1].split()[19]


class C3eKProtectedWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not sys.platform.startswith("linux") or os.geteuid() != 0:
            raise RuntimeError("C3EK_DISPOSABLE_CI_ROOT_REQUIRED")
        cls.untrusted = pwd.getpwnam("nobody")
        if cls.untrusted.pw_uid == 0:
            raise RuntimeError("C3EK_NONROOT_CLIENT_REQUIRED")

    def setUp(self):
        self.client_uid = self.untrusted.pw_uid
        self.client_gid = self.untrusted.pw_gid
        self.base = Path(tempfile.mkdtemp(prefix="c3ek-ci-", dir="/run"))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.base.chmod(0o711)  # traverse only; no client writes
        self.private = self.base / "private"
        self.private.mkdir(mode=0o700)
        self.private.chmod(0o700)
        self.public = self.base / "public"
        self.public.mkdir(mode=0o700)
        os.chown(self.public, 0, self.client_gid)
        self.public.chmod(0o750)
        self.witness = self.private / "witness.sqlite"
        self.socket = self.public / "witness.sock"
        with sqlite3.connect(self.witness) as db:
            db.execute("""CREATE TABLE witness (
                id INTEGER PRIMARY KEY CHECK(id=1),
                release_id TEXT NOT NULL,
                node_id TEXT NOT NULL,
                release_root_pin TEXT NOT NULL,
                authority_anchor_pin TEXT NOT NULL,
                minimum_policy_epoch INTEGER NOT NULL,
                minimum_release_sequence INTEGER NOT NULL)""")
            db.execute("INSERT INTO witness VALUES(1,?,?,?,?,?,?)", (
                "postapollo-connections-status", "c3ek-runner-test-01",
                "A" * 40, "B" * 40, 4, 9))
        self.witness.chmod(0o600)

    def _stop(self, proc):
        if proc.poll() is None:
            proc.terminate()
        try:
            proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate(timeout=3)

    def _client(self):
        uid, gid = self.client_uid, self.client_gid

        def drop():
            os.setgroups([])
            os.setgid(gid)
            os.setuid(uid)

        proc = subprocess.Popen(
            [sys.executable, "-u", "-c", CLIENT], preexec_fn=drop,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1)
        self.addCleanup(self._stop, proc)
        self.assertEqual(proc.stdout.readline().strip(), "READY")
        return proc

    def _server(self, client, *, should_start=True):
        cmd = [sys.executable, "-B", str(SERVER),
               "--socket", str(self.socket), "--witness", str(self.witness),
               "--peer-pid", str(client.pid), "--peer-uid", str(self.client_uid),
               "--peer-gid", str(self.client_gid),
               "--peer-start", kernel_start(client.pid)]
        proc = subprocess.Popen(
            cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1)
        self.addCleanup(self._stop, proc)
        if should_start:
            self.assertEqual(proc.stdout.readline().strip(),
                             "C3EK_READY // DISTINCT_OS_UID_READ_ONLY_WITNESS",
                             "C3EK_SERVER_BOOT_FAILED status=%r" % proc.poll())
            self.assertEqual(stat.S_IMODE(self.socket.lstat().st_mode), 0o660)
            self.assertEqual(self.socket.lstat().st_uid, 0)
            self.assertEqual(self.socket.lstat().st_gid, self.client_gid)
        else:
            self.assertNotEqual(proc.wait(timeout=5), 0)
            self.assertFalse(self.socket.exists())
        return proc

    def _ask(self, client, op="read", *, witness=None):
        data = {"op": op, "socket": str(self.socket),
                "witness": str(witness or self.witness)}
        client.stdin.write(json.dumps(data) + "\n")
        client.stdin.flush()
        line = client.stdout.readline()
        if not line:
            error = client.stderr.read()
            self.fail("C3EK_CLIENT_NO_REPLY status=%r stderr=%r" %
                      (client.poll(), error[-3000:]))
        value = json.loads(line)
        self.assertEqual(client.wait(timeout=5), 0)
        return value

    def test_01_separate_uid_reads_only_floor_and_leaves_db_intact(self):
        before = hashlib.sha256(self.witness.read_bytes()).hexdigest()
        client = self._client()
        server = self._server(client)
        reply = self._ask(client)["reply"]
        self.assertEqual(reply["minimum_policy_epoch"], 4)
        self.assertEqual(reply["minimum_release_sequence"], 9)
        self.assertEqual(reply["schema"], "postapollo.connections.c3ej.witness-read.v1")
        self.assertEqual(len(reply["enrollment_sha256"]), 64)
        self.assertIs(reply["authorized"], False)
        self.assertIs(reply["writable"], False)
        self.assertNotIn("release_root_pin", reply)
        self.assertEqual(server.wait(timeout=5), 0)
        self.assertEqual(hashlib.sha256(self.witness.read_bytes()).hexdigest(), before)
        self.assertFalse(self.socket.exists())

    def test_02_untrusted_client_cannot_open_root_private_witness(self):
        client = self._client()
        self.assertIs(self._ask(client, "direct")["direct_read"], False)

    def test_03_same_uid_different_pid_refused(self):
        approved = self._client()
        self._server(approved)
        intruder = self._client()
        self.assertEqual(self._ask(intruder)["reply"],
                         {"error": "REFUSED", "authorized": False})

    def test_04_forwarded_connection_fd_from_child_refused(self):
        client = self._client()
        self._server(client)
        self.assertEqual(self._ask(client, "forward")["reply"],
                         {"error": "REFUSED", "authorized": False})

    def test_05_write_operation_refused_with_ledger_unchanged(self):
        before = hashlib.sha256(self.witness.read_bytes()).hexdigest()
        client = self._client()
        self._server(client)
        self.assertEqual(self._ask(client, "write")["reply"],
                         {"error": "REFUSED", "authorized": False})
        self.assertEqual(hashlib.sha256(self.witness.read_bytes()).hexdigest(), before)

    def test_06_oversized_packet_refused(self):
        client = self._client()
        self._server(client)
        self.assertEqual(self._ask(client, "oversized")["reply"],
                         {"error": "REFUSED", "authorized": False})

    def test_07_missing_witness_fails_before_socket_exposure(self):
        self.witness.unlink()
        client = self._client()
        self._server(client, should_start=False)
        self.assertFalse(self.witness.exists())

    def test_08_symlink_witness_refused_without_following(self):
        real = self.private / "real.sqlite"
        self.witness.rename(real)
        self.witness.symlink_to(real)
        client = self._client()
        self._server(client, should_start=False)
        self.assertTrue(self.witness.is_symlink())

    def test_09_group_writable_socket_parent_refused(self):
        self.public.chmod(0o770)
        client = self._client()
        self._server(client, should_start=False)

    def test_10_bad_witness_schema_refused(self):
        with sqlite3.connect(self.witness) as db:
            db.execute("UPDATE witness SET node_id=?", ("!bad",))
        client = self._client()
        self._server(client)
        self.assertEqual(self._ask(client)["reply"],
                         {"error": "REFUSED", "authorized": False})

    def test_11_production_permissions_remain_default_deny(self):
        base = ROOT / "services/connections"
        self.assertIn("readonly property bool credentialActionsEnabled: false",
                      (base / "ConnectionsBroker.qml").read_text())
        self.assertIn("readonly property bool hostAuthenticated: false",
                      (base / "ConnectionsRequestStatus.qml").read_text())
        for item in (*base.glob("*.qml"), *base.glob("*.js"), base / "qmldir"):
            self.assertNotIn("C3eProtectedWitnessPeer", item.read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
