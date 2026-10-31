#!/usr/bin/env python3
"""M12i Linux CI: process protocol -> M12h receipt, no native QML execution."""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
FIX=ROOT/"tests/tasks/fixtures"
HOST=FIX/"TaskNativeReceiptHostM12i.py"


def seed_bytes(n=0):
    return (json.dumps({"fixture":"M11E_SYNTHETIC_ONLY","revision":n,
                        "counter":n,"marker":"sample"},
                       separators=(",",":"))+"\n").encode()


class Driver:
    def __init__(self, db, writer, *, bootstrap=False):
        cmd=[sys.executable,"-B","-I",str(HOST),"--db",str(db),
             "--writer-id",writer]
        if bootstrap:
            cmd.append("--bootstrap-fixture")
        self.p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,bufsize=0)
        self.next_id=1
        self.hello=self.read()

    def read(self):
        line=self.p.stdout.readline()
        if not line:
            raise AssertionError("HOST_EXITED_BEFORE_FRAME")
        return json.loads(line)

    def send(self, kind, **kwargs):
        req={"requestId":self.next_id,"kind":kind,**kwargs}
        self.next_id+=1
        self.p.stdin.write((json.dumps(req)+"\n").encode())
        self.p.stdin.flush()
        return self.read()

    def close(self):
        if self.p.stdin and not self.p.stdin.closed:
            self.p.stdin.close()
        try:
            self.p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.p.kill()
            self.p.wait(timeout=5)
        if self.p.stdout: self.p.stdout.close()
        if self.p.stderr: self.p.stderr.close()


class NativeReceiptHostTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="m12i-host-")
        self.folder=Path(self.tmp.name)/"m11e-fileview-test"
        self.folder.mkdir(mode=0o700)
        self.source=self.folder/"fixture-only.json"
        self.source.write_bytes(seed_bytes())
        self.source.chmod(0o600)
        self.db=self.folder/"handoff-test.db"
        self.hosts=[]

    def tearDown(self):
        for h in reversed(self.hosts):h.close()
        self.tmp.cleanup()

    def start(self, writer="m12i-process-owner-0001", *, bootstrap=True, db=None):
        h=Driver(db or self.db,writer,bootstrap=bootstrap)
        self.hosts.append(h)
        return h

    def simulated_fileview_atomic(self, payload):
        target=self.folder/"m12i-fixture-simulation.tmp"
        fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,"wb") as f:
            f.write(payload.encode())
            f.flush()
            os.fsync(f.fileno())
        os.replace(target,self.source)

    def check_flags(self, frame):
        self.assertEqual(set(frame),{
            "protocol","requestId","kind","ok","status","phase","epoch",
            "pending","stageId","payload","actualSha256",
            "productionWriterAuthorized","nativeStageAttributionProven",
            "realTasksAccessAuthorized"})
        self.assertFalse(frame["productionWriterAuthorized"])
        self.assertFalse(frame["nativeStageAttributionProven"])
        self.assertFalse(frame["realTasksAccessAuthorized"])

    def test_hello_reserve_readback_settle_then_freeze(self):
        h=self.start()
        self.check_flags(h.hello)
        self.assertTrue(h.hello["ok"])
        self.assertEqual(h.hello["phase"],"JSON_ACTIVE")
        r=h.send("reserve",stageId="m12i-stage-000001")
        self.check_flags(r)
        self.assertTrue(r["ok"])
        self.assertEqual(r["status"],"SYNTHETIC_RESERVED")
        self.assertTrue(r["pending"])
        self.assertEqual(json.loads(r["payload"])["counter"],1)
        self.assertEqual(self.source.read_bytes(),seed_bytes())
        # Test-only stand-in. A real QML FileView runs only in later manual test.
        self.simulated_fileview_atomic(r["payload"])
        done=h.send("verify",stageId="m12i-stage-000001",epoch=r["epoch"])
        self.check_flags(done)
        self.assertTrue(done["ok"])
        self.assertEqual(done["status"],"TEST_RECEIPT_SETTLED_UI_UNACKNOWLEDGED")
        self.assertRegex(done["actualSha256"],r"^[a-f0-9]{64}$")
        self.assertFalse(done["pending"])
        self.assertEqual(self.source.read_bytes(),seed_bytes(1))
        freeze=h.send("freeze",epoch=done["epoch"])
        self.assertTrue(freeze["ok"])
        self.assertEqual(freeze["phase"],"FREEZE_REQUESTED")

    def test_native_callback_without_verify_never_settles(self):
        h=self.start()
        r=h.send("reserve",stageId="m12i-stage-000001")
        self.assertTrue(r["ok"])
        self.simulated_fileview_atomic(r["payload"])
        # File bytes changed; pending still in SQLite, no verify request.
        status=h.send("status")
        self.assertTrue(status["pending"])
        self.assertIsNone(status["actualSha256"])
        self.assertEqual(status["phase"],"JSON_ACTIVE")

    def test_wrong_source_bytes_enter_durable_recovery_review(self):
        h=self.start()
        r=h.send("reserve",stageId="m12i-stage-000001")
        self.simulated_fileview_atomic(seed_bytes(2).decode())
        wrong=h.send("verify",stageId="m12i-stage-000001",epoch=r["epoch"])
        self.assertFalse(wrong["ok"])
        self.assertEqual(wrong["status"],"READBACK_REVIEW_REQUIRED")
        self.assertEqual(wrong["phase"],"RECOVERY_REVIEW")
        self.assertTrue(wrong["pending"])

    def test_stale_stage_terminates_without_clearing_reservation(self):
        h=self.start()
        r=h.send("reserve",stageId="m12i-stage-000001")
        self.assertTrue(r["ok"])
        reply=h.send("verify",stageId="m12i-foreign-stage",epoch=r["epoch"])
        self.assertFalse(reply["ok"])
        self.assertTrue(reply["pending"])
        self.assertEqual(reply["status"],"TEST_HOST_REFUSED")

    def test_stale_epoch_terminates_without_clearing_reservation(self):
        h=self.start()
        r=h.send("reserve",stageId="m12i-stage-000001")
        self.assertTrue(r["ok"])
        reply=h.send("verify",stageId=r["stageId"],epoch=r["epoch"]+1)
        self.assertFalse(reply["ok"])
        self.assertTrue(reply["pending"])
        self.assertEqual(reply["status"],"TEST_HOST_REFUSED")

    def test_fresh_owner_never_auto_rearms_after_settlement(self):
        h=self.start()
        r=h.send("reserve",stageId="m12i-stage-000001")
        self.simulated_fileview_atomic(r["payload"])
        self.assertTrue(h.send("verify",stageId=r["stageId"],
                               epoch=r["epoch"])["ok"])
        h.close()
        next_owner=self.start(writer="m12i-fresh-owner-0002",bootstrap=False)
        self.assertTrue(next_owner.hello["ok"])
        self.assertEqual(next_owner.hello["phase"],"RECOVERY_REVIEW")
        denied=next_owner.send("reserve",stageId="m12i-next-stage-0002")
        self.assertFalse(denied["ok"])
        self.assertEqual(self.source.read_bytes(),seed_bytes(1))

    def test_invalid_path_refuses_prior_to_any_journal_creation(self):
        invalid=Path(self.tmp.name)/"untrusted.db"
        h=self.start(db=invalid)
        self.check_flags(h.hello)
        self.assertFalse(h.hello["ok"])
        self.assertFalse(self.db.exists())
        self.assertFalse(invalid.exists())

    def test_bad_source_schema_refuses_bootstrap(self):
        self.source.write_bytes(b'{"task":"real-data"}\n')
        h=self.start()
        self.assertFalse(h.hello["ok"])
        self.assertFalse(self.db.exists())

    def test_second_owner_fails_with_existing_lock(self):
        first=self.start()
        self.assertTrue(first.hello["ok"])
        other=self.start(writer="m12i-rival-owner-0002",bootstrap=False)
        self.assertFalse(other.hello["ok"])
        self.assertTrue(first.send("status")["ok"])

    def test_qml_is_standalone_and_never_exposes_production_writer(self):
        lab=(FIX/"TaskNativeReceiptLabM12i.qml").read_text()
        wrap=(ROOT/"TaskNativeReceiptHarnessM12i.qml").read_text()
        production=(ROOT/"services/hub/ApolloHubTodoStore.qml").read_text()
        shell=(ROOT/"shell.qml").read_text()
        self.assertIn('import "./tests/tasks/fixtures"',wrap)
        self.assertIn("TaskNativeReceiptLabM12i {",wrap)
        self.assertIn("nativeRuntimeAcceptedByCI: false",wrap)
        self.assertIn('Quickshell.shellPath("tests/tasks/fixtures/TaskNativeReceiptHostM12i.py")',lab)
        self.assertIn("Qt.callLater(function()",lab)
        self.assertIn("fixtureFile.reload();",lab)
        self.assertIn('onSaved: {',lab)
        self.assertIn('onSaveFailed:',lab)
        self.assertIn('atomicWrites: true',lab)
        self.assertEqual(len(re.findall(r"\bFileView\s*\{",lab)),1)
        self.assertEqual(len(re.findall(r"\bProcess\s*\{",lab)),1)
        self.assertIn("productionWriterAuthorized: false",lab)
        self.assertIn("independentNativeStageAttributionProven: false",lab)
        self.assertNotIn("Quickshell.dataDir",lab)
        self.assertNotIn("apollo-hub-todo-v1.json",lab)
        self.assertNotIn("TaskNativeReceiptLabM12i",shell+production)
        self.assertNotIn("TaskNativeReceiptHarnessM12i",shell+production)
        self.assertIn("readonly property bool guardedWriterEnabled: false",production)
        self.assertEqual(len(re.findall(r"\bFileView\s*\{",production)),1)
        self.assertEqual(production.count("return stage(TodoPolicy."),9)


if __name__=="__main__":
    unittest.main(verbosity=2)
