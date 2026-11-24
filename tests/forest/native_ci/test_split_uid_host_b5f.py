"""B5f: installed host + distinct UID requester + disposable B1 storage.

CI-only root controller, not a privileged production launcher. Reuses B5d's
synthetic writers and the exact B5c RPM. The host still has NO SQLite opener.
"""
import array
import errno
import hashlib
import json
import os
from pathlib import Path
import select
import socket
import stat
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, "/ci")
import test_storage_dac_b5d as storage

HOST = "/usr/libexec/post-apollo/forest-ci/forest-host"
PYTHON = "/usr/bin/python3"
SELF = str(Path(__file__).resolve())
HOLD = {
    "schema": "post-apollo.forest.b5b-ci-only",
    "status": "UNKNOWN_HOLD",
    "sourceAuthenticated": False,
    "recipientAuthenticated": False,
    "permissionGranted": False,
    "productionAuthority": False,
    "privateBytesSubmitted": 0,
    "revocationFencedAck": False,
    "safeActions": [],
}


def renderer_main(args):
    storage.require_child(storage.RENDERER)
    fd_text, token, sentinel_text, *paths = args
    sentinel = int(sentinel_text)
    # The controller deliberately marks a fixture DB descriptor inheritable.
    # It must NOT survive into this distinct UID renderer.
    try:
        os.fstat(sentinel)
    except OSError as exc:
        if exc.errno != errno.EBADF:
            return 2
    else:
        return 2
    for path in paths:
        if storage.child_main(["deny-path", str(storage.RENDERER), path]) != 0:
            return 2
    with socket.socket(fileno=int(fd_text)) as peer:
        peer.settimeout(5)
        if token == "RIGHTS":
            extra = os.memfd_create("forest-b5f-public-fixture")
            try:
                peer.sendmsg([b"STATUS"], [(socket.SOL_SOCKET, socket.SCM_RIGHTS,
                                           array.array("i", [extra]))])
            finally:
                os.close(extra)
            return 0 if peer.recv(4096) == b"" else 2
        peer.sendall(token.encode("ascii"))
        wire = peer.recv(4096)
        if token == "STOP":
            return 0 if wire == b"" else 2
        # No session titles, owner IDs or body bytes may enter this channel.
        return 0 if json.loads(wire) == HOLD and peer.recv(4096) == b"" else 2


def spawn(uid, argv, fd):
    # Fixed disposable controller inputs only. Root is not the host/renderer.
    return subprocess.Popen(
        argv, user=uid, group=uid, extra_groups=[], umask=0o077,
        cwd="/", stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, close_fds=True, pass_fds=(fd,),
        env={"PATH": "/usr/bin:/bin", "HOME": "/nonexistent",
             "LC_ALL": "C", "GITHUB_ACTIONS": "true"},
    )


def reap(proc):
    try:
        return proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
        raise RuntimeError("DISPOSABLE_PROCESS_TIMEOUT") from None


def observed_uid(proc):
    lines = Path("/proc", str(proc.pid), "status").read_text().splitlines()
    line = next(line for line in lines if line.startswith("Uid:"))
    return [int(x) for x in line.split()[1:]]


class SplitUIDInstalledHostTests(unittest.TestCase):
    def setUp(self):
        storage.require_ci()
        if os.getuid() != 0 or os.geteuid() != 0:
            raise RuntimeError("CI_CONTROLLER_REQUIRED")
        # Each test owns fresh writer processes and databases. A read-only
        # SQLite backup open can create backup.db-wal and backup.db-shm;
        # those sidecars must not contaminate another exchange baseline.
        self.temp = tempfile.TemporaryDirectory(prefix="forest-b5f-ci-")
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        root.chmod(0o755)
        self.paths = {}
        for uid in (storage.OWNER_A, storage.OWNER_B):
            path = root / ("fixture-" + str(uid))
            path.mkdir(mode=0o700)
            os.chown(path, uid, uid)
            self.paths[uid] = path
            writer = storage.StorageDACExperiment.launch(uid, "writer", path)
            self.addCleanup(storage.StorageDACExperiment.stop_writer, writer)
            if not select.select([writer.stdout], [], [], 10)[0]:
                raise RuntimeError("FIXTURE_WRITER_TIMEOUT")
            if writer.stdout.readline() != b"READY\n":
                raise RuntimeError("FIXTURE_WRITER_NOT_READY")
        # Retain the exact roster check; no sidecar exclusion.
        self.snapshot()

    def snapshot(self):
        result = {}
        for uid, path in self.paths.items():
            self.assertEqual(set(p.name for p in path.iterdir()), set(storage.FILES))
            for name in storage.FILES:
                file = path / name
                info = file.stat()
                result[(uid, name)] = (
                    info.st_ino, info.st_uid, info.st_gid, info.st_mode,
                    info.st_size, hashlib.sha256(file.read_bytes()).hexdigest(),
                )
        return result

    def exchange(self, owner, token, expected_host=0):
        before = self.snapshot()
        # This is only a synthetic test DB descriptor, never user data.
        original = os.open(self.paths[owner] / "sessions.db", os.O_RDONLY)
        sentinel = None
        try:
            import fcntl
            sentinel = fcntl.fcntl(original, fcntl.F_DUPFD, 200)
            os.set_inheritable(sentinel, True)
            requester, host = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            with requester, host:
                host_fd = host.fileno()
                worker = spawn(owner, [PYTHON, "-I", "-B", HOST,
                                       "--disposable-test-fd", str(host_fd)], host_fd)
                try:
                    host.close()
                    self.assertEqual(observed_uid(worker), [owner] * 4)
                    renderer = spawn(storage.RENDERER, [
                        PYTHON, "-I", "-B", SELF, "--renderer",
                        str(requester.fileno()), token, str(sentinel),
                        *map(str, self.paths.values()),
                    ], requester.fileno())
                    try:
                        requester.close()
                        self.assertEqual(reap(renderer), 0, "RENDERER_TEST_FAILED")
                        self.assertEqual(reap(worker), expected_host)
                    finally:
                        if renderer.poll() is None:
                            renderer.kill()
                            renderer.wait(timeout=5)
                finally:
                    if worker.poll() is None:
                        worker.kill()
                        worker.wait(timeout=5)
            os.fstat(sentinel)
            self.assertEqual(self.snapshot(), before)
        finally:
            if sentinel is not None:
                os.close(sentinel)
            os.close(original)

    def test_owner_a_host_with_distinct_renderer(self):
        self.exchange(storage.OWNER_A, "STATUS")

    def test_owner_b_host_with_distinct_renderer(self):
        self.exchange(storage.OWNER_B, "STATUS")

    def test_metadata_and_generation_hold_with_both_databases_present(self):
        for token in ("LIST_SESSIONS", "DISCLOSE_SESSION_TITLES", "READ_SESSION",
                      "GENERATE", "DISCLOSE_PROVISIONAL", "COMMIT_GENERATE",
                      "SEND", "VOICE"):
            with self.subTest(token=token):
                self.exchange(storage.OWNER_A, token)

    def test_renderer_rights_transfer_refused_without_storage_change(self):
        self.exchange(storage.OWNER_B, "RIGHTS", 2)

    def test_stop_closes_without_protected_ack_or_storage_change(self):
        self.exchange(storage.OWNER_A, "STOP", 2)

    def test_owner_databases_remain_readable_to_their_own_uid(self):
        for uid, path in self.paths.items():
            proc = storage.StorageDACExperiment.launch(uid, "read-own", path)
            out, err = proc.communicate(timeout=10)
            self.assertEqual((proc.returncode, out, err), (0, b"", b""))
            # SQLite may legitimately create these backup sidecars during
            # the explicit readback. Check their ownership/modes too, but
            # never share these modified fixtures with exchange tests.
            allowed = set(storage.FILES) | {"backup.db-wal", "backup.db-shm"}
            actual = set(p.name for p in path.iterdir())
            self.assertTrue(set(storage.FILES) <= actual <= allowed)
            for name in actual:
                info = (path / name).lstat()
                self.assertTrue(stat.S_ISREG(info.st_mode))
                self.assertEqual((info.st_uid, info.st_gid,
                                  stat.S_IMODE(info.st_mode)), (uid, uid, 0o600))

    def test_exchange_snapshot_still_rejects_unexpected_sidecar(self):
        # A foreign file must fail the strict exchange baseline rather
        # than being filtered out to make the original failure disappear.
        extra = self.paths[storage.OWNER_A] / "backup.db-wal"
        self.assertFalse(extra.exists())
        extra.touch(mode=0o600)
        try:
            with self.assertRaises(AssertionError):
                self.snapshot()
        finally:
            extra.unlink()
        self.snapshot()


if __name__ == "__main__":
    storage.require_ci()
    if len(sys.argv) > 1 and sys.argv[1] == "--renderer":
        sys.exit(renderer_main(sys.argv[2:]))
    if len(sys.argv) != 1:
        sys.exit(2)
    unittest.main(verbosity=2)
