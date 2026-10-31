#!/usr/bin/env python3
"""M12h real disposable SQLite metadata transactions and source-byte tests."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
FIXTURES=ROOT/"tests/tasks/fixtures"
MODULE=FIXTURES/"TaskStageSourceReceiptM12h.py"

spec=importlib.util.spec_from_file_location("m12h_attribution", MODULE)
lab=importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)


def source(counter=0):
    return (json.dumps({
        "fixture":"M11E_SYNTHETIC_ONLY", "revision":counter,
        "counter":counter, "marker":"sample"
    },separators=(",",":"))+"\n").encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class StageReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="m12h-disposable-")
        self.folder=Path(self.tmp.name)/"m11e-fileview-test"
        self.folder.mkdir(mode=0o700)
        self.file=self.folder/"fixture-only.json"
        self.db=self.folder/"handoff-test.db"
        self.write_initial(source())
        self.owner_id="m12h-test-owner-00001"

    def tearDown(self):
        self.tmp.cleanup()

    def write_initial(self, raw):
        fd=os.open(self.file,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,"wb") as out:
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())

    def simulated_external_fileview_write(self, raw):
        # In THIS TEST ONLY, simulate Quickshell FileView's atomic rename.
        # Ledger never writes the JSON source and never opens live data.
        target=self.folder/"fixture-synthetic-inflight.tmp"
        fd=os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        with os.fdopen(fd,"wb") as out:
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())
        os.replace(target,self.file)

    def new(self, *, bootstrap=True, owner=None):
        return lab.DisposableStageReceipt(
            self.db,owner or self.owner_id,bootstrap=bootstrap)

    def assert_refusal(self, fn, code):
        with self.assertRaisesRegex(lab.AdmissionError,code):
            fn()

    def test_durable_reservation_persists_stage_and_expected_exact_bytes(self):
        with self.new() as owner:
            reserved=owner.reserve("m12h-stage-000001")
            self.assertEqual(reserved["status"],"SYNTHETIC_RESERVED")
            self.assertEqual(reserved["epoch"],0)
            self.assertEqual(reserved["baselineSha256"],digest(source()))
            self.assertEqual(reserved["expectedSha256"],digest(source(1)))
            self.assertEqual(reserved["payload"],source(1))
            self.assertEqual(self.file.read_bytes(),source())
            snap=owner.snapshot()
            self.assertEqual(snap["phase"],"JSON_ACTIVE")
            self.assertEqual(snap["pendingStage"],"m12h-stage-000001")
            self.assertEqual(snap["receipts"][0]["receiptState"],"RESERVED")
            self.assertIsNone(snap["receipts"][0]["actualSha256"])
            self.assertFalse(snap["productionWriterAuthorized"])
            self.assertFalse(snap["nativeCallbackStageProven"])

    def test_native_callback_hint_cannot_settle_stage(self):
        with self.new() as owner:
            owner.reserve("m12h-stage-000001")
            for tag in ("FILE_SAVED","FILE_READBACK_OK"):
                x=owner.notify_native(tag)
                self.assertEqual(x["status"],"NATIVE_HINT_ONLY")
                self.assertFalse(x["settled"])
            self.assertEqual(owner.snapshot()["receipts"][0]["receiptState"],
                             "RESERVED")
            self.assertEqual(self.file.read_bytes(),source())

    def test_exact_host_readback_and_sqlite_clear_are_single_transaction(self):
        with self.new() as owner:
            r=owner.reserve("m12h-stage-000001")
            self.simulated_external_fileview_write(r["payload"])
            receipt=owner.settle_after_independent_readback(
                "m12h-stage-000001",r["epoch"])
            self.assertEqual(receipt["status"],
                             "TEST_RECEIPT_SETTLED_UI_UNACKNOWLEDGED")
            self.assertTrue(receipt["settled"])
            self.assertEqual(receipt["actualSha256"],digest(source(1)))
            self.assertFalse(receipt["productionWriterAuthorized"])
            self.assertFalse(receipt["independentNativeStageAttributionProven"])
            snap=owner.snapshot()
            self.assertIsNone(snap["pendingStage"])
            self.assertEqual(snap["receipts"][0]["receiptState"],
                             "SETTLED_UNACKNOWLEDGED")
            self.assertEqual(snap["receipts"][0]["expectedSha256"],
                             snap["receipts"][0]["actualSha256"])
            self.assertEqual(self.file.read_bytes(),source(1))

    def test_second_sequential_stage_gets_own_immutable_receipt(self):
        with self.new() as owner:
            for n in (1,2):
                stage=f"m12h-stage-{n:06d}"
                r=owner.reserve(stage)
                self.simulated_external_fileview_write(r["payload"])
                self.assertTrue(owner.settle_after_independent_readback(
                    stage,r["epoch"])["settled"])
            records=owner.snapshot()["receipts"]
            self.assertEqual(len(records),2)
            self.assertEqual([r["expectedSha256"] for r in records],
                             [digest(source(1)),digest(source(2))])
            self.assertTrue(all(r["receiptState"]=="SETTLED_UNACKNOWLEDGED"
                                for r in records))
            self.assertEqual(self.file.read_bytes(),source(2))

    def test_wrong_bytes_fail_closed_and_persist_reason(self):
        with self.new() as owner:
            r=owner.reserve("m12h-stage-000001")
            # Valid synthetic JSON, but wrong revision/data.
            self.simulated_external_fileview_write(source(2))
            receipt=owner.settle_after_independent_readback(
                r["stageId"],r["epoch"])
            self.assertEqual(receipt["status"],"READBACK_REVIEW_REQUIRED")
            self.assertFalse(receipt["settled"])
            snap=owner.snapshot()
            self.assertEqual(snap["phase"],"RECOVERY_REVIEW")
            self.assertEqual(snap["epoch"],1)
            self.assertEqual(snap["pendingStage"],r["stageId"])
            self.assertEqual(snap["receipts"][0]["receiptState"],"REVIEW_REQUIRED")
            self.assertEqual(snap["receipts"][0]["actualSha256"],digest(source(2)))
            self.assert_refusal(
                lambda: owner.reserve("m12h-next-stage-0002"),
                "EXTERNAL_SOURCE_BEFORE_RESERVE|STAGE_ADMISSION_REFUSED")

    def test_semantically_equivalent_whitespace_is_not_exact_byte_settlement(self):
        with self.new() as owner:
            r=owner.reserve("m12h-stage-000001")
            # Valid same document with different whitespace.
            pretty=json.dumps(json.loads(r["payload"]),indent=2).encode()+b"\n"
            self.assertNotEqual(pretty,r["payload"])
            self.simulated_external_fileview_write(pretty)
            x=owner.settle_after_independent_readback(r["stageId"],r["epoch"])
            self.assertFalse(x["settled"])
            self.assertEqual(owner.snapshot()["phase"],"RECOVERY_REVIEW")

    def test_missing_or_invalid_json_during_readback_never_settles(self):
        for choice in ("missing","invalid"):
            with self.subTest(choice=choice):
                # Each subcase gets its own disposable fixture.
                if choice=="invalid":
                    with self.new() as owner:
                        r=owner.reserve("m12h-stage-000001")
                        self.simulated_external_fileview_write(b"{invalid}\n")
                        response=owner.settle_after_independent_readback(
                            r["stageId"],r["epoch"])
                        self.assertFalse(response["settled"])
                        self.assertEqual(owner.snapshot()["phase"],
                                         "RECOVERY_REVIEW")
                else:
                    with self.new() as owner:
                        r=owner.reserve("m12h-stage-000001")
                        self.file.unlink()
                        response=owner.settle_after_independent_readback(
                            r["stageId"],r["epoch"])
                        self.assertFalse(response["settled"])
                        self.assertEqual(owner.snapshot()["phase"],
                                         "RECOVERY_REVIEW")

    def test_stale_stage_or_epoch_not_rebound_to_active_receipt(self):
        with self.new() as owner:
            r=owner.reserve("m12h-stage-000001")
            self.simulated_external_fileview_write(r["payload"])
            self.assert_refusal(
                lambda:owner.settle_after_independent_readback(
                    "m12h-foreign-stage",r["epoch"]),"STALE_OR_UNOWNED_STAGE")
            self.assert_refusal(
                lambda:owner.settle_after_independent_readback(
                    r["stageId"],r["epoch"]+1),"STALE_OR_UNOWNED_STAGE")
            self.assertEqual(owner.snapshot()["receipts"][0]["receiptState"],
                             "RESERVED")
            self.assertTrue(owner.settle_after_independent_readback(
                r["stageId"],r["epoch"])["settled"])

    def test_duplicate_receipt_replay_refuses_and_never_reuses_stage(self):
        with self.new() as owner:
            r=owner.reserve("m12h-stage-000001")
            self.simulated_external_fileview_write(r["payload"])
            owner.settle_after_independent_readback(r["stageId"],0)
            self.assert_refusal(
                lambda:owner.settle_after_independent_readback(r["stageId"],0),
                "STALE_OR_UNOWNED_STAGE")
            self.assert_refusal(
                lambda:owner.reserve(r["stageId"]),"DUPLICATE_STAGE_REPLAY")
            self.assertEqual(owner.snapshot()["receipts"][0]["receiptState"],
                             "SETTLED_UNACKNOWLEDGED")

    def test_crash_after_reservation_preserves_pending_and_fresh_owner_review(self):
        with self.new() as owner:
            r=owner.reserve("m12h-stage-000001")
        # Simulates process exit without mutating the test source.
        with self.new(bootstrap=False,owner="m12h-new-owner-00002") as recovery:
            snap=recovery.snapshot()
            self.assertEqual(snap["phase"],"RECOVERY_REVIEW")
            self.assertEqual(snap["epoch"],1)
            self.assertEqual(snap["pendingStage"],r["stageId"])
            self.assertEqual(snap["receipts"][0]["receiptState"],"RESERVED")
            self.assert_refusal(
                lambda:recovery.reserve("m12h-stage-next-02"),
                "STAGE_ADMISSION_REFUSED")
            self.assertEqual(self.file.read_bytes(),source())

    def test_crash_after_settlement_before_ui_ack_preserves_durable_receipt(self):
        with self.new() as owner:
            r=owner.reserve("m12h-stage-000001")
            self.simulated_external_fileview_write(r["payload"])
            self.assertTrue(owner.settle_after_independent_readback(
                r["stageId"],r["epoch"])["settled"])
        with self.new(bootstrap=False,owner="m12h-new-owner-00002") as recovery:
            snap=recovery.snapshot()
            self.assertEqual(snap["phase"],"RECOVERY_REVIEW")
            self.assertEqual(snap["epoch"],1)
            self.assertIsNone(snap["pendingStage"])
            receipt=snap["receipts"][0]
            self.assertEqual(receipt["receiptState"],"SETTLED_UNACKNOWLEDGED")
            self.assertEqual(receipt["actualSha256"],digest(source(1)))
            self.assertFalse(snap["nativeCallbackStageProven"])
            self.assertEqual(self.file.read_bytes(),source(1))
            self.assert_refusal(
                lambda:recovery.reserve("m12h-next-stage-0002"),
                "STAGE_ADMISSION_REFUSED")

    def test_competing_cooperative_authority_cannot_share_test_journal(self):
        with self.new() as owner:
            self.assert_refusal(
                lambda:self.new(bootstrap=False,owner="m12h-rival-owner-0002"),
                "OTHER_PROCESS_OWNS_HANDOFF")
            self.assertEqual(owner.snapshot()["phase"],"JSON_ACTIVE")

    def test_wrong_path_and_symlink_rejected_before_journal_bootstrap(self):
        invalid=Path(self.tmp.name)/"apollo-hub-todo-v1.json"
        self.assert_refusal(
            lambda:lab.DisposableStageReceipt(
                invalid,self.owner_id,bootstrap=True),
            "M11E_DISPOSABLE_JOURNAL_ONLY")
        self.file.unlink()
        self.file.symlink_to("/nonexistent")
        self.assert_refusal(lambda:self.new(),"UNSAFE_SYNTHETIC_FILE")
        self.assertFalse(self.db.exists())

    def test_legacy_single_writer_and_no_m12h_mount(self):
        production=(ROOT/"services/hub/ApolloHubTodoStore.qml").read_text()
        shell=(ROOT/"shell.qml").read_text()
        candidate=MODULE.read_text()
        self.assertIn("readonly property bool guardedWriterEnabled: false",
                      production)
        self.assertEqual(production.count("FileView {"),1)
        self.assertEqual(production.count("return stage(TodoPolicy."),9)
        self.assertNotIn("TaskStageSourceReceiptM12h",production+shell)
        self.assertNotIn("Quickshell.dataDir",candidate)
        self.assertNotIn("apollo-hub-todo-v1.json",candidate)
        self.assertNotIn("UPDATE tasks",candidate)
        self.assertFalse(hasattr(lab.DisposableStageReceipt,"write_json"))


if __name__=="__main__":
    unittest.main(verbosity=2)
