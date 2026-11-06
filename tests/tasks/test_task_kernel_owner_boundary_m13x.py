#!/usr/bin/env python3
"""TASKS M13x // real Linux UID custody limits, DISPOSABLE CI ONLY.

Run only as root on a disposable CI runner with GITHUB_ACTIONS=true and
M13X_DISPOSABLE_CI=1. No useradd, SELinux changes, live tasks, network,
Quickshell launch, keyring, service install or production source writes.
Tests OS DAC and SO_PEERCRED, NOT real desktop app or native callback trust.
"""
from __future__ import annotations

import fcntl
import hashlib
import os
from pathlib import Path
import pwd
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC = b'{"fixture":"M13X_DISPOSABLE_ONLY","counter":0}\n'
REPLACED = b'{"fixture":"M13X_DISPOSABLE_ONLY","counter":1}\n'
CLIENT = r'''
import os, sys
op, path = sys.argv[1:]
try:
    if op == "read":
        with open(path, "rb") as f:
            f.read()
    elif op == "overwrite":
        with open(path, "wb") as f:
            f.write(b'{"fixture":"M13X_DISPOSABLE_ONLY","counter":1}\n')
    elif op == "atomic":
        parent = os.path.dirname(path)
        temp = os.path.join(parent, ".m13x-only-temp")
        fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(b'{"fixture":"M13X_DISPOSABLE_ONLY","counter":1}\n')
        os.replace(temp, path)
    else:
        raise ValueError("INVALID_TEST_COMMAND")
    print("OS_WRITE_OR_READ_ALLOWED")
except (OSError, PermissionError) as error:
    print("OS_DENIED", error.errno)
'''
SOCKET_CLIENT = r'''
import socket, sys
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect(sys.argv[1])
s.sendall(sys.argv[2].encode("ascii"))
s.close()
'''


def unused_identities():
    assigned = {record.pw_uid for record in pwd.getpwall()}
    assigned.add(os.geteuid())
    chosen = [uid for uid in range(58001, 60000)
              if uid not in assigned]
    if len(chosen) < 3:
        raise AssertionError("NO_ISOLATED_SYNTHETIC_UIDS")
    return chosen[:3]


@unittest.skipUnless(sys.platform == "linux", "Linux DAC / SO_PEERCRED only")
class KernelOwnerFeasibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (os.environ.get("GITHUB_ACTIONS") != "true"
                or os.environ.get("M13X_DISPOSABLE_CI") != "1"
                or os.geteuid() != 0):
            raise RuntimeError("M13X_PRIVATE_ROOT_CI_VM_ONLY")
        cls.owner_uid, cls.app_uid, cls.other_uid = unused_identities()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="m13x-custody-", dir="/tmp")
        self.base = Path(self.temp.name)
        assert self.base.is_absolute() and self.base.parent == Path("/tmp")
        assert self.base.name.startswith("m13x-custody-")
        assert not self.base.is_symlink()
        # The numeric test UIDs can traverse the synthetic root, but
        # not the owner-private child. No users/accounts are installed.
        os.chmod(self.base, 0o755)

    def tearDown(self):
        self.temp.cleanup()

    def owned_source(self, name, uid):
        folder = self.base / name
        folder.mkdir(mode=0o700)
        os.chown(folder, uid, uid)
        target = folder / "fixture-only.json"
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                     | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "wb") as output:
            output.write(SYNTHETIC)
            output.flush()
            os.fsync(output.fileno())
        os.chown(target, uid, uid)
        return target

    @staticmethod
    def drop_to(uid):
        def downgrade():
            os.setgroups([])
            os.setgid(uid)
            os.setuid(uid)
        return downgrade

    def run_client(self, uid, op, path):
        command = [sys.executable, "-I", "-B", "-c", CLIENT, op, str(path)]
        child = subprocess.run(
            command, capture_output=True, text=True, timeout=8,
            preexec_fn=self.drop_to(uid), check=False)
        self.assertEqual(child.returncode, 0, child.stderr)
        return child.stdout.strip()

    def test_kernel_denies_distinct_uid_access_to_protected_owner_source(self):
        protected = self.owned_source("owner-private", self.owner_uid)
        self.assertEqual(stat.S_IMODE(protected.parent.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(protected.stat().st_mode), 0o600)
        for operation in ("read", "overwrite", "atomic"):
            result = self.run_client(self.app_uid, operation, protected)
            self.assertIn("OS_DENIED", result)
        self.assertEqual(protected.read_bytes(), SYNTHETIC)
        self.assertEqual(
            self.run_client(self.owner_uid, "overwrite", protected),
            "OS_WRITE_OR_READ_ALLOWED")
        self.assertEqual(protected.read_bytes(), REPLACED)

    def test_current_direct_fileview_writer_cannot_write_other_uid_source(self):
        # The real TASKS FileView executes under desktop user's UID. An
        # otherwise valid direct-write path protected by another UID cannot
        # be opened or atomically replaced by that desktop UID.
        source = self.owned_source("host-owning-source", self.owner_uid)
        direct = self.run_client(self.app_uid, "overwrite", source)
        atomic = self.run_client(self.app_uid, "atomic", source)
        self.assertIn("OS_DENIED", direct)
        self.assertIn("OS_DENIED", atomic)
        self.assertEqual(source.read_bytes(), SYNTHETIC)

    def test_advisory_flock_does_not_stop_same_uid_atomic_replacement(self):
        source = self.owned_source("desktop-owning-source", self.app_uid)
        lock_file = self.base / "fixture-test.lock"
        fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            # A separate process with the exact desktop UID ignores flock.
            result = self.run_client(self.app_uid, "atomic", source)
            self.assertEqual(result, "OS_WRITE_OR_READ_ALLOWED")
            self.assertNotEqual(
                hashlib.sha256(source.read_bytes()).hexdigest(), original_hash)
            self.assertEqual(source.read_bytes(), REPLACED)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def test_so_peercred_authenticates_os_pid_and_uid_not_application(self):
        address = self.base / "identity-test.sock"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(str(address))
            os.chmod(address, 0o666)
            server.listen(3)
            server.settimeout(8)
            observed = []
            for uid, asserted_name in [
                (self.app_uid, "TASKS_UI"),
                (self.app_uid, "OTHER_SAME_UID"),
                (self.other_uid, "UNRELATED_UID"),
            ]:
                proc = subprocess.Popen(
                    [sys.executable, "-I", "-B", "-c", SOCKET_CLIENT,
                     str(address), asserted_name],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    preexec_fn=self.drop_to(uid))
                try:
                    with server.accept()[0] as conn:
                        creds = conn.getsockopt(
                            socket.SOL_SOCKET, socket.SO_PEERCRED,
                            struct.calcsize("3i"))
                        pid, peer_uid, peer_gid = struct.unpack("3i", creds)
                        label = conn.recv(40).decode("ascii")
                        observed.append((pid, peer_uid, peer_gid, label))
                finally:
                    stdout, stderr = proc.communicate(timeout=8)
                    self.assertEqual(proc.returncode, 0, stderr.decode())
                self.assertEqual(pid, proc.pid)
                self.assertEqual(peer_uid, uid)
                self.assertEqual(peer_gid, uid)
            self.assertEqual(observed[0][1], observed[1][1])
            self.assertNotEqual(observed[0][0], observed[1][0])
            self.assertNotEqual(observed[1][1], observed[2][1])
            self.assertEqual(observed[0][3], "TASKS_UI")
            self.assertEqual(observed[1][3], "OTHER_SAME_UID")
            # The two different labels are client-controlled assertions.
            # Neither UID nor PID alone proves code integrity or consent.

    def test_existing_one_writer_and_recovery_guards_are_unmodified(self):
        store = (ROOT / "services/hub/ApolloHubTodoStore.qml").read_text()
        broker = (ROOT / "services/connections/ConnectionsBroker.qml").read_text()
        native = (ROOT / "tests/tasks/fixtures/TaskNativeReceiptLabM12i.qml").read_text()
        self.assertEqual(store.count("FileView {"), 1)
        self.assertEqual(store.count("todoFile.setText("), 1)
        self.assertIn("readonly property bool guardedWriterEnabled: false", store)
        self.assertIn("readonly property bool encryptedRecoveryEnabled: false", store)
        self.assertIn("readonly property bool ticketProducerEnabled: false", store)
        self.assertIn("readonly property bool credentialActionsEnabled: false", broker)
        self.assertIn("fixtureFile.setText(pendingRaw)", native)
        self.assertIn("independentNativeStageAttributionProven: false", native)


if __name__ == "__main__":
    unittest.main()
