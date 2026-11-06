#!/usr/bin/env python3
"""M13v: real disposable journal, synthetic FileView writes, advisory hints."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

ROOT=Path(__file__).resolve().parents[2]
FIXTURES=ROOT/"tests/tasks/fixtures"
spec=importlib.util.spec_from_file_location(
    "m13v_disposable_test",FIXTURES/"TaskNativeReceiptHandoffM13v.py")
lab=importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)


def synthetic_raw(revision=0):
    return (json.dumps({"fixture":"M11E_SYNTHETIC_ONLY",
                        "revision":revision,"counter":revision,
                        "marker":"sample"},separators=(",",":"))+"\n").encode()


class M13vTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="m13v-")
        self.folder=Path(self.temp.name)/"m11e-fileview-test"
        self.folder.mkdir(mode=0o700)
        self.source=self.folder/"fixture-only.json"
        self.db=self.folder/"handoff-test.db"
        fd=os.open(self.source,os.O_WRONLY|os.O_CREAT|os.O_EXCL
                   |getattr(os,"O_NOFOLLOW",0),0o600)
        with os.fdopen(fd,"wb") as output:
            output.write(synthetic_raw())
            output.flush()
            os.fsync(output.fileno())
        self.owner_id="m13v-disposable-owner-0001"

    def tearDown(self):
        self.temp.cleanup()

    def new_owner(self,*,bootstrap=False,owner_id=None):
        return lab.m12h.DisposableStageReceipt(
            self.db,owner_id or self.owner_id,bootstrap=bootstrap)

    def replace(self,raw):
        # Only the test simulates a FileView atomic rename. Handoff does not.
        temp=self.folder/(".m13v-disposable-"+uuid.uuid4().hex)
        fd=os.open(temp,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        with os.fdopen(fd,"wb") as output:
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp,self.source)
        directory=os.open(self.folder,os.O_RDONLY|os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def assert_nopower(self,reply):
        for name in lab.NO_POWER:
            self.assertIs(lab.NO_POWER[name],False,name)
            self.assertIs(reply[name],False,name)
        self.assertNotIn("payload",reply)
        self.assertNotIn("draft",reply)
        self.assertNotIn("key",reply)

    def stage(self,bridge,index):
        result=bridge.begin("m13v-stage-%06d"%index)
        self.assertEqual(result["status"],
                         "SYNTHETIC_STAGE_RESERVED_NO_SOURCE_WRITE")
        self.assert_nopower(result)
        return result

    def test_default_no_receipt_and_existing_fake_seed_only(self):
        with self.new_owner(bootstrap=True) as owner:
            bridge=lab.DisposableNativeReceiptHandoff(owner)
            first=bridge.inspect()
            self.assertEqual(first["status"],"NO_DURABLE_SETTLED_REVISION")
            self.assert_nopower(first)
            self.stage(bridge,1)
            self.assertEqual(self.source.read_bytes(),synthetic_raw())
            self.assertEqual(bridge.inspect()["status"],"UNACKNOWLEDGED_STAGE_PENDING")
            self.assertEqual(owner.snapshot()["receipts"][0]["receiptState"],"RESERVED")

    def test_native_saved_hint_cannot_acknowledge_or_settle(self):
        with self.new_owner(bootstrap=True) as owner:
            bridge=lab.DisposableNativeReceiptHandoff(owner)
            s=self.stage(bridge,1)
            event=bridge.native_hint(stage_id=s["stageId"],
                                     owner_epoch=s["ownerEpoch"],kind="FILE_SAVED")
            self.assertEqual(event["status"],"NATIVE_HINT_ONLY_NOT_A_RECEIPT")
            self.assert_nopower(event)
            self.assertEqual(owner.snapshot()["receipts"][0]["receiptState"],"RESERVED")
            self.assertEqual(self.source.read_bytes(),synthetic_raw())
            self.assertEqual(bridge.native_hint(
                stage_id=s["stageId"],owner_epoch=s["ownerEpoch"],
                kind="FILE_SAVED")["status"],"DUPLICATE_NATIVE_HINT_REFUSED")
            second=bridge.settle_after_independent_readback(
                stage_id=s["stageId"],owner_epoch=s["ownerEpoch"])
            self.assertEqual(second["status"],"SOURCE_READBACK_REVIEW_REQUIRED")
            self.assert_nopower(second)
            self.assertEqual(owner.snapshot()["phase"],"RECOVERY_REVIEW")
            self.assertEqual(bridge.begin("m13v-stage-000002")["status"],
                             "REVIEW_REQUIRED_NO_REPLAY")

    def test_two_exact_stage_settlements_each_require_independent_readback(self):
        with self.new_owner(bootstrap=True) as owner:
            bridge=lab.DisposableNativeReceiptHandoff(owner)
            for i in (1,2):
                s=self.stage(bridge,i)
                self.assertEqual(bridge.settle_after_independent_readback(
                    stage_id=s["stageId"],owner_epoch=s["ownerEpoch"]
                )["status"],"NATIVE_HINT_MISSING_NO_SETTLEMENT")
                self.replace(synthetic_raw(i))
                event=bridge.native_hint(stage_id=s["stageId"],
                    owner_epoch=s["ownerEpoch"],kind="FILE_SAVED")
                self.assertEqual(event["status"],"NATIVE_HINT_ONLY_NOT_A_RECEIPT")
                result=bridge.settle_after_independent_readback(
                    stage_id=s["stageId"],owner_epoch=s["ownerEpoch"])
                self.assertEqual(result["status"],
                    "SYNTHETIC_RECEIPT_OBSERVED_UI_UNACKNOWLEDGED")
                self.assertEqual(result["receipt"]["revision"],i)
                self.assertEqual(result["receipt"]["sourceSha256"],
                                 hashlib.sha256(synthetic_raw(i)).hexdigest())
                self.assert_nopower(result)
                self.assertEqual(owner.snapshot()["pendingStage"],None)
                self.assertEqual(bridge.inspect()["receipt"]["revision"],i)
                self.assertEqual(bridge.settle_after_independent_readback(
                    stage_id=s["stageId"],owner_epoch=s["ownerEpoch"]
                )["status"],"STALE_OR_UNOWNED_SETTLEMENT")

    def test_wrong_stage_epoch_and_out_of_order_hints_have_no_effect(self):
        with self.new_owner(bootstrap=True) as owner:
            bridge=lab.DisposableNativeReceiptHandoff(owner)
            s=self.stage(bridge,1)
            for stage,epoch,kind in [
                ("m13v-stage-000099",s["ownerEpoch"],"FILE_SAVED"),
                (s["stageId"],s["ownerEpoch"]+1,"FILE_SAVED"),
                (s["stageId"],s["ownerEpoch"],"UNTRUSTED_SUCCESS"),
            ]:
                reply=bridge.native_hint(stage_id=stage,
                                         owner_epoch=epoch,kind=kind)
                self.assertNotEqual(reply["status"],"NATIVE_HINT_ONLY_NOT_A_RECEIPT")
                self.assert_nopower(reply)
            self.assertEqual(owner.snapshot()["receipts"][0]["receiptState"],"RESERVED")
            self.assertEqual(bridge.settle_after_independent_readback(
                stage_id=s["stageId"],owner_epoch=s["ownerEpoch"]
            )["status"],"NATIVE_HINT_MISSING_NO_SETTLEMENT")
            self.assertEqual(bridge.settle_after_independent_readback(
                stage_id=s["stageId"],owner_epoch=s["ownerEpoch"]+1
            )["status"],"STALE_OR_UNOWNED_SETTLEMENT")

    def test_native_save_failure_preserves_unresolved_stage_for_operator(self):
        with self.new_owner(bootstrap=True) as owner:
            bridge=lab.DisposableNativeReceiptHandoff(owner)
            s=self.stage(bridge,1)
            result=bridge.native_hint(stage_id=s["stageId"],
                                      owner_epoch=s["ownerEpoch"],
                                      kind="FILE_SAVE_FAILED")
            self.assertEqual(result["status"],"AMBIGUOUS_NATIVE_FAILURE_REVIEW_REQUIRED")
            self.assert_nopower(result)
            self.assertEqual(owner.snapshot()["receipts"][0]["receiptState"],"RESERVED")
            self.assertEqual(owner.snapshot()["pendingStage"],s["stageId"])
            self.assertEqual(bridge.begin("m13v-stage-000002")["status"],
                             "REVIEW_REQUIRED_NO_REPLAY")
            self.assertEqual(bridge.settle_after_independent_readback(
                stage_id=s["stageId"],owner_epoch=s["ownerEpoch"]
            )["status"],"REVIEW_REQUIRED_NO_REPLAY")

    def test_missing_or_rolled_back_source_is_never_reinterpreted_as_first_create(self):
        with self.new_owner(bootstrap=True) as owner:
            bridge=lab.DisposableNativeReceiptHandoff(owner)
            self.source.unlink()
            self.assertEqual(bridge.begin("m13v-stage-000001")["status"],
                             "SAVED_SOURCE_UNAVAILABLE_OR_UNSAFE")
        # Separately verify post-settlement rollback.
        # A fresh fixture is needed; don't bootstrap the same DB twice.
        with self.assertRaises(Exception):
            self.new_owner(bootstrap=True)

    def test_saved_source_rollback_blocks_new_stage(self):
        with self.new_owner(bootstrap=True) as owner:
            bridge=lab.DisposableNativeReceiptHandoff(owner)
            for i in (1,2):
                s=self.stage(bridge,i)
                self.replace(synthetic_raw(i))
                bridge.native_hint(stage_id=s["stageId"],owner_epoch=s["ownerEpoch"],
                                   kind="FILE_SAVED")
                self.assertEqual(bridge.settle_after_independent_readback(
                    stage_id=s["stageId"],owner_epoch=s["ownerEpoch"]
                )["status"],"SYNTHETIC_RECEIPT_OBSERVED_UI_UNACKNOWLEDGED")
            self.replace(synthetic_raw(1))
            self.assertEqual(bridge.begin("m13v-stage-000003")["status"],
                             "SOURCE_JOURNAL_REVISION_MISMATCH")

    def test_fresh_process_and_owner_epoch_require_review_no_auto_replay(self):
        with self.new_owner(bootstrap=True) as owner:
            bridge=lab.DisposableNativeReceiptHandoff(owner)
            s=self.stage(bridge,1)
            self.replace(synthetic_raw(1))
            bridge.native_hint(stage_id=s["stageId"],owner_epoch=s["ownerEpoch"],
                               kind="FILE_SAVED")
            self.assertEqual(bridge.settle_after_independent_readback(
                stage_id=s["stageId"],owner_epoch=s["ownerEpoch"]
            )["status"],"SYNTHETIC_RECEIPT_OBSERVED_UI_UNACKNOWLEDGED")
        code=r'''
import importlib.util,json,pathlib,sys
spec=importlib.util.spec_from_file_location("m13v_fresh",pathlib.Path(sys.argv[1]))
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with module.m12h.DisposableStageReceipt(pathlib.Path(sys.argv[2]),
    "m13v-fresh-owner-00002",bootstrap=False) as owner:
    bridge=module.DisposableNativeReceiptHandoff(owner)
    print(json.dumps({"inspect":bridge.inspect(),
                      "begin":bridge.begin("m13v-stage-000002")}))
'''
        result=subprocess.run([sys.executable,"-B","-I","-c",code,
                str(FIXTURES/"TaskNativeReceiptHandoffM13v.py"),str(self.db)],
                text=True,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        state=json.loads(result.stdout)
        self.assertEqual(state["inspect"]["status"],"OWNER_REVIEW_REQUIRED")
        self.assertEqual(state["begin"]["status"],"OWNER_REVIEW_OR_PENDING")
        self.assert_nopower(state["inspect"])
        self.assert_nopower(state["begin"])

    def test_callback_origin_not_authenticated_even_if_bytes_match(self):
        # Known M12k limitation. A same-UID writer that can replace the
        # synthetic file with EXPECTED bytes + forge advisory onSaved can
        # produce test-consistent evidence. Never claim native provenance.
        with self.new_owner(bootstrap=True) as owner:
            bridge=lab.DisposableNativeReceiptHandoff(owner)
            s=self.stage(bridge,1)
            self.replace(synthetic_raw(1)) # NOT written by Quickshell FileView.
            bridge.native_hint(stage_id=s["stageId"],owner_epoch=s["ownerEpoch"],
                               kind="FILE_SAVED")
            reply=bridge.settle_after_independent_readback(
                stage_id=s["stageId"],owner_epoch=s["ownerEpoch"])
            self.assertEqual(reply["status"],
                             "SYNTHETIC_RECEIPT_OBSERVED_UI_UNACKNOWLEDGED")
            self.assertIs(reply["independentNativeCallbackAuthenticated"],False)
            self.assertIs(reply["durableUserSaveAcknowledged"],False)
            self.assert_nopower(reply)

    def test_production_single_writer_and_connections_flags_stay_closed(self):
        store=(ROOT/"services/hub/ApolloHubTodoStore.qml").read_text()
        broker=(ROOT/"services/connections/ConnectionsBroker.qml").read_text()
        bridge=(FIXTURES/"TaskNativeReceiptHandoffM13v.py").read_text()
        self.assertEqual(store.count("FileView {"),1)
        self.assertEqual(store.count("todoFile.setText("),1)
        for setting in ["guardedWriterEnabled","ticketProducerEnabled",
                        "encryptedRecoveryEnabled","encryptedDraftHostEnabled"]:
            self.assertIn("readonly property bool "+setting+": false",store)
        self.assertIn("readonly property bool credentialActionsEnabled: false",broker)
        self.assertNotIn("TaskNativeReceiptHandoffM13v",store+broker)
        for forbidden in ("secret-tool","sqlite3.connect(","os.replace(","FileView {"):
            self.assertNotIn(forbidden,bridge)


if __name__ == "__main__":
    unittest.main()
