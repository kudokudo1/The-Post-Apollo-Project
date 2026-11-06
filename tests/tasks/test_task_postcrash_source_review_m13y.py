#!/usr/bin/env python3
"""M13y: post-exit source/journal review, real SQLite and child-process crash."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "tests/tasks/fixtures"
MODULE = HERE / "TaskPostCrashSourceReviewM13y.py"
spec = importlib.util.spec_from_file_location("m13y_disposable_review", MODULE)
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)
m12h = lab.m12h


def synthetic(n=0):
    return (json.dumps({"fixture":"M11E_SYNTHETIC_ONLY",
                        "revision":n,"counter":n,"marker":"sample"},
                       separators=(",",":")) + "\n").encode()


CRASH = r'''
import importlib.util, os, pathlib, sys, uuid
spec=importlib.util.spec_from_file_location("m13y_m12h_crash",sys.argv[1])
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
db=pathlib.Path(sys.argv[2])
phase=sys.argv[3]
owner=m.DisposableStageReceipt(db,"m13y-child-owner-0001",bootstrap=True)
step=owner.reserve("m13y-crash-stage-00001")
if phase in ("after_source","after_settlement"):
    temp=db.parent/(".m13y-crash-sim-"+uuid.uuid4().hex)
    fd=os.open(temp,os.O_WRONLY|os.O_EXCL|os.O_CREAT,0o600)
    with os.fdopen(fd,"wb") as f:
        f.write(step["payload"]);f.flush();os.fsync(f.fileno())
    os.replace(temp,db.parent/"fixture-only.json")
    d=os.open(db.parent,os.O_RDONLY|os.O_DIRECTORY)
    os.fsync(d);os.close(d)
if phase=="after_settlement":
    result=owner.settle_after_independent_readback(
        step["stageId"],step["epoch"])
    assert result["settled"]
os._exit(86)
'''


class RecoveryReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="m13y-")
        self.folder = Path(self.temp.name) / "m11e-fileview-test"
        self.folder.mkdir(mode=0o700)
        self.db = self.folder / "handoff-test.db"
        self.source = self.folder / "fixture-only.json"
        fd = os.open(self.source, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as out:
            out.write(synthetic())
            out.flush()
            os.fsync(out.fileno())

    def tearDown(self):
        self.temp.cleanup()

    def owner(self):
        return m12h.DisposableStageReceipt(
            self.db,"m13y-disposable-owner-00001",bootstrap=True)

    def replace(self, raw):
        temp=self.folder/(".m13y-atomic-fixture-"+uuid.uuid4().hex)
        fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,"wb") as out:
            out.write(raw);out.flush();os.fsync(out.fileno())
        os.replace(temp,self.source)
        directory=os.open(self.folder,os.O_RDONLY|os.O_DIRECTORY)
        os.fsync(directory)
        os.close(directory)

    def reserve(self, owner, num):
        return owner.reserve("m13y-source-stage-%06d" % num)

    def settle(self, owner, num):
        stage=self.reserve(owner,num)
        self.replace(stage["payload"])
        result=owner.settle_after_independent_readback(stage["stageId"],
                                                       stage["epoch"])
        self.assertTrue(result["settled"])
        return stage

    def report(self, expected_code):
        result=lab.inspect(self.db)
        self.assertEqual(result["classification"],expected_code,result)
        self.assertEqual(result["draftDisposition"],"KEEP_DRAFT")
        self.assertEqual(result["lastConfirmedDisplay"],"KEEP_LAST_CONFIRMED")
        self.assertEqual(result["nextAction"],"OPERATOR_REVIEW_ONLY")
        for name, fixed in lab.NO_POWER.items():
            self.assertIs(result[name],fixed,name)
        body=json.dumps(result)
        for forbidden in [
            "fixture-only.json","handoff-test.db","m13y-source-stage",
            "m13y-disposable-owner",self.temp.name,
            "M11E_SYNTHETIC_ONLY","counter","sourceSha256","draftText",
        ]:
            self.assertNotIn(forbidden,body)
        return result

    def test_first_bootstrap_does_not_invent_saved_revision(self):
        with self.owner():
            pass
        result=self.report("NO_SETTLED_SOURCE_REVISION")
        self.assertEqual(result["lastSettledRevision"],0)
        self.assertFalse(result["pendingStagePresent"])

    def test_active_writer_lock_refuses_instead_of_observing_midflight(self):
        with self.owner() as owner:
            self.reserve(owner,1)
            self.report("ACTIVE_OR_UNVERIFIED_OWNER_REFUSED")
        self.report("RESERVED_SOURCE_STILL_AT_BASELINE")

    def test_reserved_stage_baseline_and_expected_are_distinct_uncertain_states(self):
        with self.owner() as owner:
            stage=self.reserve(owner,1)
        found=self.report("RESERVED_SOURCE_STILL_AT_BASELINE")
        self.assertTrue(found["pendingStagePresent"])
        self.assertEqual(found["sourcePosition"],"BASELINE")
        self.replace(stage["payload"])
        found=self.report("RESERVED_SOURCE_MATCHES_EXPECTED_UNACKNOWLEDGED")
        self.assertTrue(found["pendingStagePresent"])
        self.assertEqual(found["sourcePosition"],"EXPECTED")
        self.assertEqual(found["lastSettledRevision"],0)

    def test_settled_stage_remains_ui_unacknowledged(self):
        with self.owner() as owner:
            self.settle(owner,1)
        found=self.report("SETTLED_SOURCE_MATCHES_UI_UNACKNOWLEDGED")
        self.assertFalse(found["pendingStagePresent"])
        self.assertEqual(found["lastSettledRevision"],1)
        self.assertEqual(found["sourcePosition"],"LAST_SETTLED")

    def test_multiple_settled_stages_and_pending_expected_preserve_last_revision(self):
        with self.owner() as owner:
            for n in (1,2):
                self.settle(owner,n)
            third=self.reserve(owner,3)
        self.replace(third["payload"])
        found=self.report("RESERVED_SOURCE_MATCHES_EXPECTED_UNACKNOWLEDGED")
        self.assertEqual(found["lastSettledRevision"],2)
        self.assertTrue(found["pendingStagePresent"])

    def test_failed_readback_never_promotes_wrong_source(self):
        with self.owner() as owner:
            stage=self.reserve(owner,1)
            self.replace(synthetic(99))
            result=owner.settle_after_independent_readback(
                stage["stageId"],stage["epoch"])
            self.assertFalse(result["settled"])
        found=self.report("FAILED_STAGE_REQUIRES_REVIEW")
        self.assertTrue(found["pendingStagePresent"])
        self.assertEqual(found["lastSettledRevision"],0)

    def test_bad_source_and_symlink_fail_closed_without_repair(self):
        with self.owner() as owner:
            self.settle(owner,1)
        self.replace(synthetic(0))
        self.report("SETTLED_SOURCE_DIVERGED_REVIEW")
        self.source.unlink()
        self.report("SAVED_SOURCE_UNAVAILABLE_OR_UNSAFE")
        different=self.folder/"not-a-source.json"
        different.write_bytes(synthetic(1))
        self.source.symlink_to(different)
        self.report("SAVED_SOURCE_UNAVAILABLE_OR_UNSAFE")
        self.assertTrue(self.source.is_symlink())

    def test_journal_mismatch_and_tampering_fail_closed(self):
        with self.owner() as owner:
            stage=self.reserve(owner,1)
        # Only disposable CI journal can be deliberately modified.
        with sqlite3.connect(self.db) as con:
            con.execute("UPDATE authority SET pending_stage=NULL WHERE id=1")
        self.report("JOURNAL_CHAIN_UNVERIFIED")
        with sqlite3.connect(self.db) as con:
            con.execute("UPDATE authority SET pending_stage=? WHERE id=1",
                        (stage["stageId"],))
            con.execute("UPDATE stage_receipts_m12h SET expected_sha256=?",
                        ("c"*64,))
        self.report("RESERVED_SOURCE_STILL_AT_BASELINE")
        # The last test is intentionally only read-only review, not a
        # cryptographic attestation of a same-UID writable SQLite journal.

    def test_crash_windows_from_independent_process_are_readable_without_replay(self):
        for phase, code in [
            ("after_reserve","RESERVED_SOURCE_STILL_AT_BASELINE"),
            ("after_source","RESERVED_SOURCE_MATCHES_EXPECTED_UNACKNOWLEDGED"),
            ("after_settlement","SETTLED_SOURCE_MATCHES_UI_UNACKNOWLEDGED"),
        ]:
            with self.subTest(phase=phase):
                with tempfile.TemporaryDirectory(prefix="m13y-crash-") as scratch:
                    folder=Path(scratch)/"m11e-fileview-test"
                    folder.mkdir(mode=0o700)
                    source=folder/"fixture-only.json"
                    source.write_bytes(synthetic());source.chmod(0o600)
                    db=folder/"handoff-test.db"
                    child=subprocess.run(
                        [sys.executable,"-I","-B","-c",CRASH,
                         str(HERE/"TaskStageSourceReceiptM12h.py"),
                         str(db),phase],
                        capture_output=True,text=True,timeout=12)
                    self.assertEqual(child.returncode,86,child.stderr)
                    result=subprocess.run(
                        [sys.executable,"-I","-B",str(MODULE),
                         "--db",str(db)],
                        capture_output=True,text=True,timeout=12)
                    self.assertEqual(result.returncode,0,result.stderr)
                    out=json.loads(result.stdout)
                    self.assertEqual(out["classification"],code,out)
                    self.assertFalse(out["savedAcknowledged"])
                    self.assertFalse(out["automaticReplayAuthorized"])
                    self.assertFalse(out["clearDraftAuthorized"])
                    self.assertNotIn(str(db),result.stdout)
                    self.assertNotIn("m13y-crash-stage-",result.stdout)

    def test_missing_unsafe_journal_or_lock_do_not_create_a_new_owner(self):
        self.report("JOURNAL_UNAVAILABLE_OR_UNSAFE")
        with self.owner():
            pass
        lock=self.folder/"handoff-test.lock"
        lock.unlink()
        self.report("LOCK_UNAVAILABLE_OR_UNSAFE")
        self.assertFalse(lock.exists())

    def test_absent_or_foreign_path_never_opens_a_journal(self):
        for db in [Path("/tmp/apollo-hub-todo-v1.json"),
                   self.folder/"wrong.db",Path("handoff-test.db")]:
            result=lab.inspect(db)
            self.assertEqual(result["classification"],
                             "REFUSED_NOT_DISPOSABLE_M12H_PATH")
            self.assertFalse(result["taskWriteAuthorized"])

    def test_production_writer_connections_and_native_lab_are_untouched(self):
        store=(ROOT/"services/hub/ApolloHubTodoStore.qml").read_text()
        broker=(ROOT/"services/connections/ConnectionsBroker.qml").read_text()
        inspector=MODULE.read_text()
        self.assertEqual(store.count("FileView {"),1)
        self.assertEqual(store.count("todoFile.setText("),1)
        self.assertIn("readonly property bool ticketProducerEnabled: false",store)
        self.assertIn("readonly property bool encryptedRecoveryEnabled: false",store)
        self.assertIn("readonly property bool credentialActionsEnabled: false",broker)
        self.assertNotIn("TaskPostCrashSourceReviewM13y",store+broker)
        for forbidden in ["sqlite3.connect(uri, uri=True, isolation_level=None",
                          "os.replace(", "os.unlink(", "os.remove(",
                          "shutil.rmtree(", "TaskEncryptedDraftHost"]:
            self.assertNotIn(forbidden,inspector)


if __name__=="__main__":
    unittest.main()
