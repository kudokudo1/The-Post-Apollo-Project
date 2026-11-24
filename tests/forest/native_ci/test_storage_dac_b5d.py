"""B5d disposable Linux DAC storage experiment, not protected custody.

Run only in a fresh root-controlled CI container. The harness creates two
synthetic B1 databases under distinct numeric UIDs, with WAL, SHM and backups.
No production paths, authenticated principals, private data, or host changes.
"""
from __future__ import annotations

import errno
import os
from pathlib import Path
import select
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest

SELF = str(Path(__file__).resolve())
PYTHON = sys.executable
OWNER_A, OWNER_B, RENDERER = 61001, 61002, 61003
FILES = ("sessions.db", "sessions.db-wal", "sessions.db-shm", "backup.db")
DENIED = (errno.EACCES, errno.EPERM)


def require_ci():
    if (not sys.platform.startswith("linux")
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or not Path("/.dockerenv").is_file()):
        raise RuntimeError("DISPOSABLE_CI_CONTAINER_REQUIRED")


def require_child(uid):
    if (uid not in (OWNER_A, OWNER_B, RENDERER)
            or os.getuid() != uid or os.geteuid() != uid
            or os.getgid() != uid or os.getegid() != uid
            or os.getgroups()):
        raise RuntimeError("CI_UNPRIVILEGED_IDENTITY_REQUIRED")


def child_main(args):
    # Test controller chooses these paths; no request or production interface.
    command, uid_text, path_text, *rest = args
    uid = int(uid_text)
    require_child(uid)
    path = Path(path_text)
    if command == "writer":
        if uid not in (OWNER_A, OWNER_B) or rest:
            return 2
        sys.path.insert(0, "/b1")
        from session_journal_v0 import bootstrap_synthetic, ForestSessionJournal
        if any(path.iterdir()):
            return 2
        with sqlite3.connect(path / "sessions.db") as db:
            db.execute("PRAGMA temp_store=MEMORY")
            if db.execute("PRAGMA journal_mode=WAL").fetchone() != ("wal",):
                return 2
            bootstrap_synthetic(db)
            journal = ForestSessionJournal(db)
            row = journal.create_session("fixture-owner-" + str(uid), "CHERRY",
                                         "CI synthetic title", now_ms=100)
            journal.append_turn("fixture-owner-" + str(uid), row["session_id"],
                                expected_revision=0, role="user",
                                body="CI synthetic body", now_ms=101)
            with sqlite3.connect(path / "backup.db") as backup:
                db.backup(backup)
            if not all((path / name).is_file() for name in FILES):
                return 2
            print("READY", flush=True)
            if sys.stdin.readline() != "STOP\n":
                return 2
        db.close()
        return 0
    if command == "read-own":
        if uid not in (OWNER_A, OWNER_B) or rest:
            return 2
        for name in ("sessions.db", "backup.db"):
            db = sqlite3.connect((path / name).as_uri() + "?mode=ro", uri=True)
            try:
                if db.execute("SELECT owner_key, title FROM forest_sessions").fetchall() != [
                        ("fixture-owner-" + str(uid), "CI synthetic title")]:
                    return 2
                if db.execute("SELECT body FROM forest_turns").fetchall() != [
                        ("CI synthetic body",)]:
                    return 2
            finally:
                db.close()
        return 0
    if command == "deny-path":
        if rest:
            return 2
        # O_WRONLY does not truncate. These are only synthetic fixtures.
        for name in FILES:
            for flags in (os.O_RDONLY, os.O_WRONLY):
                try:
                    fd = os.open(path / name, flags | os.O_CLOEXEC)
                except OSError as exc:
                    if exc.errno not in DENIED:
                        return 2
                else:
                    os.close(fd)
                    return 2
        try:
            os.listdir(path)
        except OSError as exc:
            if exc.errno not in DENIED:
                return 2
        else:
            return 2
        # SQLite cannot bypass the pathname boundary either.
        try:
            db = sqlite3.connect((path / "sessions.db").as_uri() + "?mode=ro",
                                 uri=True)
        except sqlite3.OperationalError:
            return 0
        else:
            db.close()
            return 2
    if command == "deny-mutation":
        if rest:
            return 2
        # Synthetic directory only; no data deletion on real paths.
        for operation in (
            lambda: os.unlink(path / "backup.db"),
            lambda: os.rename(path / "sessions.db", path / "renamed.db"),
            lambda: os.open(path / "unexpected", os.O_CREAT | os.O_EXCL |
                            os.O_WRONLY | os.O_CLOEXEC, 0o600),
        ):
            try:
                result = operation()
            except OSError as exc:
                if exc.errno not in DENIED:
                    return 2
            else:
                if type(result) is int:
                    os.close(result)
                return 2
        return 0
    if command == "inherited-fd":
        if uid != RENDERER or len(rest) != 1:
            return 2
        # Intentional negative-security control: an already-open descriptor
        # bypasses pathname DAC. No row data or private bytes are returned.
        fd = int(rest[0])
        try:
            return 0 if os.read(fd, 16) == b"SQLite format 3\x00" else 2
        finally:
            os.close(fd)
    return 2


class StorageDACExperiment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_ci()
        if os.getuid() != 0 or os.geteuid() != 0:
            raise RuntimeError("ROOT_TEST_CONTROLLER_REQUIRED")
        cls.temp = tempfile.TemporaryDirectory(prefix="forest-b5d-ci-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.root.chmod(0o755)
        cls.paths = {}
        for uid in (OWNER_A, OWNER_B):
            path = cls.root / ("fixture-" + str(uid))
            path.mkdir(mode=0o700)
            os.chown(path, uid, uid)
            cls.paths[uid] = path
            proc = cls.launch(uid, "writer", path)
            cls.addClassCleanup(cls.stop_writer, proc)
            if not select.select([proc.stdout], [], [], 10)[0]:
                raise RuntimeError("FIXTURE_WRITER_TIMEOUT")
            if proc.stdout.readline() != b"READY\n":
                raise RuntimeError("FIXTURE_WRITER_NOT_READY")

    @staticmethod
    def launch(uid, action, path, *extra, pass_fds=()):
        return subprocess.Popen(
            [PYTHON, "-I", "-B", SELF, "--child", action, str(uid),
             str(path), *map(str, extra)],
            user=uid, group=uid, extra_groups=[], umask=0o077,
            cwd="/", stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, close_fds=True, pass_fds=pass_fds,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C",
                 "HOME": "/nonexistent", "GITHUB_ACTIONS": "true"},
        )

    @staticmethod
    def stop_writer(proc):
        try:
            out, err = proc.communicate(input=b"STOP\n", timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate(timeout=5)
            raise RuntimeError("FIXTURE_WRITER_STOP_TIMEOUT") from None
        if proc.returncode != 0 or out or err:
            raise RuntimeError("FIXTURE_WRITER_STOP_FAILED")

    def run_child(self, uid, action, path, *extra, pass_fds=()):
        proc = self.launch(uid, action, path, *extra, pass_fds=pass_fds)
        try:
            out, err = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate(timeout=5)
            self.fail("DISPOSABLE_CHILD_TIMEOUT")
        self.assertEqual(proc.returncode, 0, "DISPOSABLE_CHILD_REFUSED")
        self.assertEqual((out, err), (b"", b""))

    def test_directory_and_all_sqlite_files_have_distinct_owner_and_modes(self):
        for uid, path in self.paths.items():
            with self.subTest(uid=uid):
                info = path.lstat()
                self.assertTrue(stat.S_ISDIR(info.st_mode))
                self.assertEqual((info.st_uid, info.st_gid,
                                  stat.S_IMODE(info.st_mode)), (uid, uid, 0o700))
                for name in FILES:
                    info = (path / name).lstat()
                    self.assertTrue(stat.S_ISREG(info.st_mode))
                    self.assertEqual((info.st_uid, info.st_gid,
                                      stat.S_IMODE(info.st_mode)),
                                     (uid, uid, 0o600))

    def test_owner_reads_live_wal_database_and_backup(self):
        for uid, path in self.paths.items():
            self.run_child(uid, "read-own", path)

    def test_distinct_owner_cannot_open_other_database_or_sidecars(self):
        self.run_child(OWNER_A, "deny-path", self.paths[OWNER_B])
        self.run_child(OWNER_B, "deny-path", self.paths[OWNER_A])

    def test_distinct_owner_cannot_unlink_rename_or_create_other_files(self):
        self.run_child(OWNER_A, "deny-mutation", self.paths[OWNER_B])
        self.run_child(OWNER_B, "deny-mutation", self.paths[OWNER_A])

    def test_renderer_cannot_open_database_wal_shm_or_backup(self):
        for path in self.paths.values():
            self.run_child(RENDERER, "deny-path", path)

    def test_renderer_cannot_mutate_private_directories(self):
        for path in self.paths.values():
            self.run_child(RENDERER, "deny-mutation", path)

    def test_inherited_descriptor_bypasses_path_dac_not_a_protected_capability(self):
        # Root deliberately passes a synthetic DB descriptor to the renderer.
        # This proves why a real launcher must refuse FD inheritance/leakage.
        fd = os.open(self.paths[OWNER_A] / "sessions.db", os.O_RDONLY | os.O_CLOEXEC)
        try:
            self.run_child(RENDERER, "inherited-fd", self.paths[OWNER_A], fd,
                           pass_fds=(fd,))
        finally:
            os.close(fd)


if __name__ == "__main__":
    require_ci()
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        sys.exit(child_main(sys.argv[2:]))
    if len(sys.argv) != 1:
        sys.exit(2)
    unittest.main(verbosity=2)
