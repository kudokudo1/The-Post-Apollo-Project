#!/usr/bin/env python3
"""FP1k: disposable local-only preference storage and hostile-input tests."""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/finance/household_reserve_preference_store.py"
spec = importlib.util.spec_from_file_location("finance_reserve_fp1k", SCRIPT)
store = importlib.util.module_from_spec(spec)
spec.loader.exec_module(store)

class PreferenceStoreFP1k(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name) / "reserve"
    def command(self, action="list", context="mine", expected=0, percent=None, **extra):
        cmd = {"action": action, "contextId": context}
        if action != "list":
            cmd["expectedRevision"] = expected
        if percent is not None:
            cmd["marginPercent"] = percent
        cmd.update(extra)
        return store.run(self.directory, cmd)
    def save(self, percent=110, expected=0, context="mine"):
        return self.command("save", context, expected, percent)

    def test_read_missing_does_not_write(self):
        empty = self.command()
        self.assertEqual(empty, {"version":1, "contextId":"mine",
                                 "revision":0, "marginPercent":100})
        self.assertFalse(self.directory.exists())
        self.assertEqual(self.command(context="family")["marginPercent"],100)
        self.assertFalse(self.directory.exists())

    def test_save_reset_and_context_isolation(self):
        first = self.save()
        self.assertEqual(first["marginPercent"],110)
        self.assertEqual(first["revision"],1)
        self.assertEqual(stat.S_IMODE(self.directory.stat().st_mode),0o700)
        path = self.directory / "mine.json"
        self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
        self.assertEqual(self.command()["marginPercent"],110)
        self.assertEqual(self.command(context="granny")["marginPercent"],100)
        self.assertEqual(self.save(125, expected=0, context="granny")["revision"],1)
        self.assertEqual(self.command(context="granny")["marginPercent"],125)
        self.assertEqual(self.command()["marginPercent"],110)
        reset = self.command("reset", expected=1)
        self.assertEqual(reset["marginPercent"],100)
        self.assertEqual(reset["revision"],2)
        self.assertEqual(self.command(context="granny")["marginPercent"],125)
        self.assertEqual(json.loads(path.read_text())["marginPercent"],100)

    def test_stale_writes_and_no_implicit_reset(self):
        first = self.save()
        before = (self.directory / "mine.json").read_bytes()
        with self.assertRaises(store.Refusal) as e:
            self.save(125, expected=0)
        self.assertEqual(str(e.exception),"STALE_REVISION")
        self.assertEqual((self.directory / "mine.json").read_bytes(),before)
        with self.assertRaises(store.Refusal):
            self.command("reset", expected=0)
        self.assertEqual((self.directory / "mine.json").read_bytes(),before)

    def test_bad_percentages_are_refused(self):
        self.save()
        path = self.directory / "mine.json"
        before = path.read_bytes()
        for percent in (True, False, 99, 105, 126, "110", 110.0, -1, None):
            cmd = {"action":"save", "contextId":"mine",
                   "expectedRevision":1, "marginPercent":percent}
            with self.subTest(percent=repr(percent)):
                with self.assertRaises(store.Refusal):
                    store.run(self.directory,cmd)
        self.assertEqual(path.read_bytes(),before)

    def test_unexpected_commands_and_contexts(self):
        self.save()
        original = (self.directory / "mine.json").read_bytes()
        attacks = [
            {"action":"list", "contextId":"mine","expectedRevision":1},
            {"action":"save", "contextId":"mine","expectedRevision":1,
             "marginPercent":125,"amountCents":20000},
            {"action":"delete","contextId":"mine","expectedRevision":1},
            {"action":"reset","contextId":"mine","expectedRevision":1,
             "marginPercent":100},
            {"action":"save","contextId":"mom","expectedRevision":True,
             "marginPercent":125},
            {"action":"save","contextId":"mine","expectedRevision":1.0,
             "marginPercent":125},
            {"action":"list","contextId":"../mine"},
            {"action":"list","contextId":"MINE"},
            {"action":"list","contextId":"bank"},
            {"action":"list","contextId":"shared/mine"},
        ]
        for cmd in attacks:
            with self.subTest(cmd=cmd):
                with self.assertRaises(store.Refusal):
                    store.run(self.directory,cmd)
        self.assertEqual((self.directory / "mine.json").read_bytes(),original)
        self.assertFalse((self.directory / "mom.json").exists())

    def test_corrupt_newer_and_missing_fields_fail_closed(self):
        self.save()
        path = self.directory / "mine.json"
        doc = json.loads(path.read_text())
        for changes in (
            {"version":2}, {"marginPercent":109}, {"contextId":"mom"},
            {"marginPercent":True}, {"revision":-1},
            {"revision":2**53}, {"unknownField":"bank-account"}
        ):
            malformed = dict(doc, **changes)
            path.write_text(json.dumps(malformed))
            path.chmod(0o600)
            raw = path.read_bytes()
            with self.subTest(changes=changes):
                with self.assertRaises(store.Refusal):
                    self.command()
                with self.assertRaises(store.Refusal):
                    self.save(expected=1,percent=125)
                self.assertEqual(path.read_bytes(),raw)

    def test_symlink_record_and_lock_refused(self):
        self.directory.mkdir(mode=0o700)
        target = Path(self.tmp.name)/"outside.json"
        target.write_text("{}")
        record = self.directory/"mine.json"
        record.symlink_to(target)
        with self.assertRaises(store.Refusal):
            self.command()
        with self.assertRaises(store.Refusal):
            self.save()
        self.assertEqual(target.read_text(),"{}")
        record.unlink()
        lock = self.directory/"mine.lock"
        lock.symlink_to(target)
        with self.assertRaises(store.Refusal):
            self.save()
        self.assertEqual(target.read_text(),"{}")

    def test_directory_symlink_or_permissions_refused(self):
        root = Path(self.tmp.name)
        bad = root/"outside"
        bad.mkdir(mode=0o700)
        self.directory.symlink_to(bad, target_is_directory=True)
        with self.assertRaises(store.Refusal): self.command()
        with self.assertRaises(store.Refusal): self.save()
        self.directory.unlink()
        self.directory.mkdir(mode=0o777)
        self.directory.chmod(0o755)
        with self.assertRaises(store.Refusal): self.command()
        with self.assertRaises(store.Refusal): self.save()

    def test_advisory_lock_and_revision_are_enforced(self):
        self.save()
        fd = os.open(self.directory/"mine.lock", os.O_RDWR|os.O_NOFOLLOW)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(store.Refusal) as error:
                self.save(percent=125,expected=1)
            self.assertEqual(str(error.exception),"WRITE_BUSY")
        finally:
            fcntl.flock(fd,fcntl.LOCK_UN)
            os.close(fd)
        self.assertEqual(self.save(percent=125,expected=1)["revision"],2)

    def test_stdout_protocol_without_private_record_dump(self):
        with tempfile.TemporaryDirectory() as sandbox:
            env = dict(os.environ, XDG_DATA_HOME=sandbox)
            cmd = {"action":"list","contextId":"mine"}
            r = subprocess.run([sys.executable,"-B",str(SCRIPT)],
                input=json.dumps(cmd)+"\n",text=True,
                capture_output=True,env=env,timeout=10)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertTrue(r.stdout.startswith("FINANCEW_RESERVE_PREF_RESULT "))
            payload = json.loads(r.stdout.split("RESULT ",1)[1])
            self.assertEqual(payload["source"],"LOCAL_OPERATOR_RESERVE_PREFS")
            self.assertIs(payload["bankVerified"],False)
            self.assertIs(payload["identityVerified"],False)
            self.assertEqual(payload["marginPercent"],100)
            self.assertFalse((Path(sandbox)/"post-apollo"/"finance"/"household-reserve-preferences").exists())
            invalid = {"action":"save","contextId":"mine","expectedRevision":0,
                       "marginPercent":999}
            r = subprocess.run([sys.executable,"-B",str(SCRIPT)],
                input=json.dumps(invalid)+"\n",text=True,
                capture_output=True,env=env,timeout=10)
            self.assertNotEqual(r.returncode,0)
            self.assertIn("FINANCEW_RESERVE_PREF_ERROR",r.stderr)
            self.assertNotIn("traceback",r.stderr.lower())

if __name__=="__main__":
    unittest.main()
