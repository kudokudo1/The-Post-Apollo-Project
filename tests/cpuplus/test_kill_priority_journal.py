"""Offline priority journal contracts: no resource-setting syscalls."""
import fcntl
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services/kill"))
import priority_journal as j


class JournalTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.store = j.PriorityJournal(self.directory)
        self.target = (123, 456, "worker")
        self.before = dict(nice=0, soft=20, hard=20, scheduler=0, uid=os.geteuid())
        self.after = dict(self.before, nice=5)

    def mark(self, **kw):
        args = dict(operation="apply", original=0, before=self.before, requested=5)
        return self.store.mark(*self.target, **dict(args, **kw))

    def test_reopen_and_restore(self):
        self.assertIsNone(self.store.read(*self.target))
        self.assertEqual(list(self.directory.iterdir()), [])
        token = self.mark()
        other = j.PriorityJournal(self.directory)
        pending = other.read(*self.target)
        self.assertEqual(pending["phase"], "pending_unknown")
        self.assertEqual(pending["original"], 0)
        with self.assertRaises(j.JournalRefused):
            self.mark()
        managed = other.finish(*self.target, token=token, after=self.after)
        self.assertEqual(managed["phase"], "managed")
        self.assertEqual(self.store.read(*self.target), managed)
        token2 = self.mark(operation="restore", before=self.after, requested=0)
        self.assertNotEqual(token2, token)
        self.assertEqual(other.read(*self.target)["original"], 0)
        restored = other.finish(*self.target, token=token2, after=self.before)
        self.assertEqual(restored["phase"], "restored")
        self.assertEqual(self.store.read(*self.target), restored)

    def test_wrong_completion_never_clears_marker(self):
        token = self.mark()
        pending = self.store.read(*self.target)
        for bad_token, readback in [(str(j.uuid.uuid4()), self.after),
                                    (token, self.before),
                                    (token, dict(self.after, soft=21, hard=21))]:
            with self.assertRaises(j.JournalRefused):
                self.store.finish(*self.target, token=bad_token, after=readback)
            self.assertEqual(self.store.read(*self.target), pending)

    def test_changed_ownership_refused(self):
        token = self.mark()
        managed = self.store.finish(*self.target, token=token, after=self.after)
        for change in [dict(before=dict(self.after, nice=6), requested=7),
                       dict(before=self.after, original=1, requested=7)]:
            with self.assertRaises(j.JournalRefused):
                self.mark(**change)
        self.assertEqual(self.store.read(*self.target), managed)

    def test_identity_and_boot_isolation(self):
        self.mark()
        self.assertIsNone(self.store.read(123, 457, "worker"))
        self.assertIsNone(self.store.read(123, 456, "other"))
        scope = j.scope()
        with mock.patch.object(j, "scope", return_value=dict(scope, boot=str(j.uuid.uuid4()))):
            self.assertIsNone(self.store.read(*self.target))
        self.assertEqual(self.store.read(*self.target)["phase"], "pending_unknown")

    def test_invalid_intents_write_nothing(self):
        for bad in [dict(requested=0), dict(requested=-1), dict(original=1),
                    dict(operation="restore", requested=0),
                    dict(before=dict(self.before, soft=0, hard=0))]:
            with self.assertRaises(j.JournalRefused):
                self.mark(**bad)
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_corruption_and_symlink_fail_closed(self):
        self.mark()
        path, = self.directory.iterdir()
        path.write_text("{}")
        with self.assertRaises(j.JournalRefused):
            self.mark()
        self.assertEqual(path.read_text(), "{}")
        path.unlink()
        victim = self.directory / "victim"
        victim.write_text("unchanged")
        path.symlink_to(victim)
        with self.assertRaises(OSError):
            self.mark()
        self.assertEqual(victim.read_text(), "unchanged")

    def test_lock_and_private_directory(self):
        fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                self.mark()
        finally:
            os.close(fd)
        self.directory.chmod(0o755)
        with self.assertRaises(j.JournalRefused):
            self.mark()
        self.directory.chmod(0o700)
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_fsync_failure_does_not_return_admission(self):
        with mock.patch.object(j.os, "fsync", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                self.mark()
        self.assertIsNone(self.store.read(*self.target))
        self.assertEqual(list(self.directory.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
