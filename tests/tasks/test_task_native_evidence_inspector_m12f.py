#!/usr/bin/env python3
"""M12f private fixture/journal post-run evidence and native-not-claimed tests."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/tasks/fixtures"
INSPECT = FIXTURES / "TaskNativeEvidenceInspectorM12f.py"
AUTHORITY = FIXTURES / "TaskSqliteWriterAuthorityFixture.py"


def load(path, label):
    spec = importlib.util.spec_from_file_location(label, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[label] = module
    spec.loader.exec_module(module)
    return module


evidence = load(INSPECT, "m12f_evidence_inspector")
auth = load(AUTHORITY, "m12f_disposable_authority")
TAGS = ["STAGE_REQUEST", "HOST_ADMIT", "FILE_SAVED",
        "FILE_READBACK_OK", "HOST_SETTLED"]


class PostNativeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="m12f-synthetic-")
        self.folder = Path(self.tmp.name) / "m11e-fileview-test"
        self.folder.mkdir(mode=0o700)
        self.source = self.folder / "fixture-only.json"
        self.db = self.folder / "handoff-test.db"
        self.initial = {"fixture":"M11E_SYNTHETIC_ONLY",
                        "revision":0, "counter":0, "marker":"sample"}
        self.write(self.initial)
        with auth.Authority(self.db, "m12f-test-owner-0001",
                            bootstrap=True) as owner:
            self.assertEqual(owner.snapshot()["phase"], "JSON_ACTIVE")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, doc):
        self.source.write_text(json.dumps(doc, separators=(",",":"))+"\n")
        self.source.chmod(0o600)

    def assert_refuses(self, code, *, source=None, count=0,
                       phase="JSON_ACTIVE", tags=None):
        with self.assertRaisesRegex(evidence.EvidenceRefusal, code):
            evidence.inspect(self.source if source is None else source,
                             count, phase, tags)

    def test_synthetic_baseline_and_source_schema_only_no_native_claim(self):
        result = evidence.inspect(self.source, 0, "JSON_ACTIVE")
        self.assertEqual(result["status"], "SYNTHETIC_JOURNAL_MATCH")
        self.assertEqual(result["observedCounter"], 0)
        self.assertEqual(result["journalEpoch"], 0)
        self.assertEqual(result["journalPending"], False)
        self.assertFalse(result["operatorTraceSupplied"])
        self.assertFalse(result["nativeEventsIndependentlyCaptured"])
        self.assertFalse(result["independentNativeAcceptance"])
        self.assertFalse(result["productionWriterAuthorized"])
        self.assertFalse(result["realTasksDataAccess"])
        for forbidden in ("owner_id", "stage_id", "fixture-only.json",
                          str(self.folder), "/home/"):
            self.assertNotIn(forbidden, json.dumps(result))

    def test_synthetic_disposable_admit_file_change_and_settlement(self):
        with auth.Authority(self.db, "m12f-second-owner-0002") as owner:
            # A fresh process must enter recovery review, not auto-reactivate.
            self.assertEqual(owner.snapshot()["phase"], "RECOVERY_REVIEW")
        result = evidence.inspect(self.source, 0, "RECOVERY_REVIEW", TAGS)
        self.assertEqual(result["status"], "SYNTHETIC_JOURNAL_MATCH")
        self.assertEqual(result["journalEpoch"], 1)
        self.assertEqual(result["operatorReportedCompleteChains"], 1)
        self.assertTrue(result["operatorTraceSupplied"])
        self.assertFalse(result["nativeEventsIndependentlyCaptured"])
        self.assertFalse(result["nativeStageAttributionProven"])

    def test_active_disposable_owner_lock_blocks_concurrent_inspection(self):
        with auth.Authority(self.db, "m12f-lock-holder-001") as owner:
            self.assert_refuses("NATIVE_HOST_STILL_OWNS_FIXTURE")
            self.assertEqual(owner.snapshot()["phase"], "RECOVERY_REVIEW")
        self.assertEqual(
            evidence.inspect(self.source, 0, "RECOVERY_REVIEW")["status"],
            "SYNTHETIC_JOURNAL_MATCH")

    def test_counter_mismatch_not_misreported_as_native_failure(self):
        observed = evidence.inspect(self.source, 1, "JSON_ACTIVE")
        self.assertEqual(observed["status"], "SYNTHETIC_EXPECTATION_MISMATCH")
        self.assertFalse(observed["sourceMatchesExpectedCounter"])
        self.assertTrue(observed["journalMatchesExpectedPhase"])
        self.assertFalse(observed["independentNativeAcceptance"])

    def test_phase_mismatch_not_misreported_as_callback_failure(self):
        observed = evidence.inspect(self.source, 0, "RECOVERY_REVIEW")
        self.assertEqual(observed["status"], "SYNTHETIC_EXPECTATION_MISMATCH")
        self.assertFalse(observed["journalMatchesExpectedPhase"])

    def test_unknown_or_out_of_order_operator_tags_cannot_prove_stage(self):
        for bad in (["FILE_SAVED","HOST_SETTLED"],
                    ["HOST_ADMIT","STAGE_REQUEST","FILE_READBACK_OK"],
                    ["STAGE_REQUEST","HOST_ADMIT","HOST_EXIT",
                     "FILE_SAVED","FILE_READBACK_OK","HOST_SETTLED"]):
            result = evidence.inspect(self.source,0,"JSON_ACTIVE",bad)
            self.assertEqual(result["operatorReportedCompleteChains"],0)
            self.assertFalse(result["nativeStageAttributionProven"])
        self.assert_refuses("INVALID_OPERATOR_TRACE",tags=["STAGE_UNKNOWN"])
        self.assert_refuses("INVALID_OPERATOR_TRACE",tags=["FILE_SAVED"]*33)

    def test_unsafe_source_symlink_wrong_name_hardlink_and_loose_permissions(self):
        p = self.source
        raw = p.read_bytes()
        p.unlink()
        p.symlink_to(self.folder/"not-real")
        self.assert_refuses("PRIVATE_FIXTURE_FILE_REQUIRED")
        p.unlink()
        p.write_bytes(raw);p.chmod(0o600)
        linked = self.folder/"hardlink-copy"
        os.link(p,linked)
        self.assert_refuses("PRIVATE_FIXTURE_FILE_REQUIRED")
        linked.unlink()
        p.chmod(0o644)
        self.assert_refuses("PRIVATE_FIXTURE_FILE_REQUIRED")
        p.chmod(0o600)
        self.assert_refuses("M11E_DISPOSABLE_SOURCE_ONLY",
                            source=self.folder/"other.json")
        self.assert_refuses("M11E_DISPOSABLE_SOURCE_ONLY",
                            source=Path(self.tmp.name)/"apollo-hub-todo-v1.json")

    def test_unsafe_folder_and_database_refusal(self):
        self.folder.chmod(0o755)
        self.assert_refuses("PRIVATE_FIXTURE_DIRECTORY_REQUIRED")
        self.folder.chmod(0o700)
        self.db.chmod(0o644)
        self.assert_refuses("PRIVATE_FIXTURE_FILE_REQUIRED")
        self.db.chmod(0o600)
        self.db.rename(self.folder/"moved.db")
        self.assert_refuses("PRIVATE_FIXTURE_FILE_REQUIRED")

    def test_schema_or_duplicate_keys_refused(self):
        self.write({"fixture":"M11E_SYNTHETIC_ONLY","revision":0,
                    "counter":1,"marker":"sample"})
        self.assert_refuses("INVALID_FIXTURE_DOCUMENT")
        self.source.write_text('{"fixture":"M11E_SYNTHETIC_ONLY","revision":0,'
                               '"counter":0,"counter":0,"marker":"sample"}\n')
        self.source.chmod(0o600)
        self.assert_refuses("DUPLICATE_FIXTURE_KEY")

    def test_guard_and_standalone_wrapper_have_no_live_mount(self):
        wrapper = (ROOT/"TaskNativeCallbackHarnessM12f.qml").read_text()
        lab = (FIXTURES/"TaskNativeCallbackLabM12e.qml").read_text()
        store = (ROOT/"services/hub/ApolloHubTodoStore.qml").read_text()
        shell = (ROOT/"shell.qml").read_text()
        bridge = (ROOT/"services/projects/TaskFileViewHostBridgeM11g.qml").read_text()
        inspector = INSPECT.read_text()
        self.assertIn('import "./tests/tasks/fixtures"',wrapper)
        self.assertIn("TaskNativeCallbackLabM12e {",wrapper)
        self.assertIn("nativeAcceptedByGitHubCI: false",wrapper)
        self.assertIn('Quickshell.shellPath("tests/tasks/fixtures/TaskFileViewOwnerHostM11g.py")',bridge)
        self.assertIn("nativeStageAttributionProven: false",lab)
        for bad in ("FileView {","Process {","Quickshell.dataDir",
                    "Component.onCompleted:","Timer {","execDetached("):
            self.assertNotIn(bad,wrapper)
        self.assertNotIn("TaskNativeCallbackHarnessM12f",shell+store)
        self.assertIn("readonly property bool guardedWriterEnabled: false",store)
        self.assertEqual(store.count("FileView {"),1)
        self.assertEqual(store.count("return stage(TodoPolicy."),9)
        self.assertNotIn("Quickshell.dataDir",inspector)
        self.assertNotIn("apollo-hub-todo-v1.json",inspector)

    def test_no_stage_auth_claim_or_source_file_written(self):
        initial = self.source.read_bytes()
        report = evidence.inspect(self.source,0,"JSON_ACTIVE",TAGS)
        self.assertEqual(initial,self.source.read_bytes())
        self.assertTrue(report["operatorTraceSupplied"])
        self.assertEqual(report["operatorReportedCompleteChains"],1)
        self.assertFalse(report["independentNativeAcceptance"])
        self.assertFalse(report["nativeStageAttributionProven"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
