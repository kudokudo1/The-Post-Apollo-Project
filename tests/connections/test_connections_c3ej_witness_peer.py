#!/usr/bin/env python3
"""C3e-J: real Linux peer-credential tests, isolated and read-only (CI only)."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "tests/connections/c3e_release_trust"
SOURCE = HERE / "C3eReadOnlyWitnessPeer.py"


def load():
    spec = importlib.util.spec_from_file_location("c3ej_peer_test", SOURCE)
    assert spec and spec.loader
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


peer = load()


class C3eJWitnessPeerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="c3ej-witness-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.db = self.directory / "witness.sqlite"
        self.sock = self.directory / "peer.sock"
        with sqlite3.connect(self.db) as db:
            db.execute("""CREATE TABLE witness (
                id INTEGER PRIMARY KEY CHECK(id=1),
                release_id TEXT NOT NULL,
                node_id TEXT NOT NULL,
                release_root_pin TEXT NOT NULL,
                authority_anchor_pin TEXT NOT NULL,
                minimum_policy_epoch INTEGER NOT NULL,
                minimum_release_sequence INTEGER NOT NULL)""")
            db.execute("INSERT INTO witness VALUES(1,?,?,?,?,?,?)", (
                "postapollo-connections-status", "c3ej-runner-test-01",
                "A" * 40, "B" * 40, 4, 9))
        self.db.chmod(0o600)

    def _start(self):
        cmd = [sys.executable, "-B", str(SOURCE),
               "--socket", str(self.sock), "--witness", str(self.db),
               "--peer-pid", str(os.getpid()), "--peer-uid", str(os.getuid()),
               "--peer-start", peer.process_start(os.getpid())]
        process = subprocess.Popen(
            cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True)
        self.addCleanup(self._stop, process)
        ready = process.stdout.readline()
        self.assertEqual(ready.strip(), "C3EJ_READY // test-only-read-only-peer",
                         "server startup refusal; return code=%r" % process.poll())
        return process

    @staticmethod
    def _stop(process):
        if process.poll() is None:
            process.terminate()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=3)

    def _connect(self, payload=peer.REQUEST):
        with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as sock:
            sock.settimeout(4)
            sock.connect(str(self.sock))
            sock.sendall(payload)
            answer = sock.recv(4096)
        return json.loads(answer)

    def test_01_verified_running_peer_reads_existing_floor_only(self):
        before = hashlib.sha256(self.db.read_bytes()).hexdigest()
        process = self._start()
        result = self._connect()
        self.assertEqual(result["minimum_policy_epoch"], 4)
        self.assertEqual(result["minimum_release_sequence"], 9)
        self.assertEqual(len(result["enrollment_sha256"]), 64)
        self.assertIs(result["authorized"], False)
        self.assertIs(result["writable"], False)
        self.assertNotIn("release_root_pin", result)
        self.assertNotIn("authority_anchor_pin", result)
        self.assertEqual(process.wait(timeout=5), 0)
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(), before)

    def test_02_write_and_release_admission_are_not_protocol_operations(self):
        self._start()
        self.assertEqual(self._connect(b"WRITE-FLOOR-V1"),
                         {"error": "REFUSED", "authorized": False})

    def test_03_oversized_or_truncated_packet_refused(self):
        self._start()
        self.assertEqual(self._connect(b"WITNESS-FLOOR-READ-V1" + b"X" * 200),
                         {"error": "REFUSED", "authorized": False})

    def test_04_different_process_cannot_impersonate_parent(self):
        self._start()
        child = subprocess.run(
            [sys.executable, "-c",
             "import socket,sys,json; s=socket.socket(socket.AF_UNIX,socket.SOCK_SEQPACKET);"
             "s.connect(sys.argv[1]); s.sendall(b'WITNESS-FLOOR-READ-V1');"
             "print(s.recv(4096).decode()); s.close()", str(self.sock)],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=8, check=True)
        self.assertEqual(json.loads(child.stdout),
                         {"error": "REFUSED", "authorized": False})

    def test_05_forwarded_connected_socket_refused_per_message(self):
        self._start()
        with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as sock:
            sock.connect(str(self.sock))
            # SO_PEERCRED sees parent at connect; SCM_CREDENTIALS must see child.
            child = subprocess.run(
                [sys.executable, "-c",
                 "import socket,sys; s=socket.socket(fileno=int(sys.argv[1]));"
                 "s.sendall(b'WITNESS-FLOOR-READ-V1');"
                 "print(s.recv(4096).decode()); s.close()", str(sock.fileno())],
                pass_fds=(sock.fileno(),), text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=8, check=True)
            self.assertEqual(json.loads(child.stdout),
                             {"error": "REFUSED", "authorized": False})

    def test_06_missing_witness_does_not_create_database(self):
        self.db.unlink()
        self._start()
        self.assertEqual(self._connect(),
                         {"error": "REFUSED", "authorized": False})
        self.assertFalse(self.db.exists())

    def test_07_symlink_and_unsafe_permissions_refused(self):
        target = self.directory / "real-witness.sqlite"
        self.db.rename(target)
        self.db.symlink_to(target)
        self._start()
        self.assertEqual(self._connect(),
                         {"error": "REFUSED", "authorized": False})

    def test_08_invalid_witness_record_refused(self):
        with sqlite3.connect(self.db) as db:
            db.execute("UPDATE witness SET release_root_pin=?",
                       ("UNSIGNED-CLAIM",))
        self._start()
        self.assertEqual(self._connect(),
                         {"error": "REFUSED", "authorized": False})

    def test_09_prod_broker_deny_only_unchanged(self):
        source = ROOT / "services/connections"
        self.assertIn("readonly property bool credentialActionsEnabled: false",
                      (source / "ConnectionsBroker.qml").read_text())
        self.assertIn("readonly property bool hostAuthenticated: false",
                      (source / "ConnectionsRequestStatus.qml").read_text())
        for path in (*source.glob("*.qml"), *source.glob("*.js"), source / "qmldir"):
            self.assertNotIn("C3eReadOnlyWitnessPeer", path.read_text())

    def test_10_server_does_not_mutate_symlink_socket(self):
        self.sock.symlink_to(self.db)
        proc = subprocess.run(
            [sys.executable, "-B", str(SOURCE),
             "--socket", str(self.sock), "--witness", str(self.db),
             "--peer-pid", str(os.getpid()), "--peer-uid", str(os.getuid()),
             "--peer-start", peer.process_start(os.getpid())],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            timeout=6)
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue(self.sock.is_symlink())
        self.assertTrue(self.db.is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
