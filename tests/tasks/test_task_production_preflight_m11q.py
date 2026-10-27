#!/usr/bin/env python3
"""M11q source-only disabled production integration preflight.

This is an audit, NOT executable production migration or writer activation.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "tests/tasks/fixtures/task_production_preflight_m11q.json"


class NativeCallbackPreflight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_is_unactivated_and_disposable(self):
        item = self.data
        self.assertEqual(item["milestone"], "M11q")
        self.assertEqual(item["classification"],
            "DISABLED_PRODUCTION_INTEGRATION_PREFLIGHT_NOT_IMPLEMENTED")
        self.assertTrue(item["noLiveProcessStarted"])
        self.assertEqual(item["observedNativeEvidence"],
            "M11n partial source/journal evidence only")
        self.assertEqual(len(item["faultPoints"]), 4)
        self.assertEqual({x["name"] for x in item["faultPoints"]},
            {"AFTER_RESERVE","AFTER_SAVED","AFTER_READBACK","AFTER_SETTLEMENT"})
        self.assertTrue(all(x["nativeObserved"] is False
                            for x in item["faultPoints"]))
        self.assertTrue(all(x["nextOwner"] == "RECOVERY_REVIEW"
                            for x in item["faultPoints"]))
        self.assertEqual(len(item["productionRequiredChanges"]), 7)
        self.assertTrue(all(x["implemented"] is False
                            for x in item["productionRequiredChanges"]))
        self.assertGreaterEqual(len(item["externalBoundaries"]), 8)
        self.assertTrue(item["authorizations"]["standaloneTestHarnessSourcePatch"])
        self.assertFalse(any(value for key,value in item["authorizations"].items()
                             if key != "standaloneTestHarnessSourcePatch"))

    def test_actual_store_remains_unmodified_single_writer(self):
        store = (ROOT / "services/hub/ApolloHubTodoStore.qml").read_text()
        shell = (ROOT / "shell.qml").read_text()
        policy = (ROOT / "services/hub/ApolloHubTodoPolicy.js").read_text()
        self.assertIn("readonly property bool guardedWriterEnabled: false", store)
        self.assertEqual(store.count("FileView {"), 1)
        self.assertEqual(store.count("todoFile.setText("), 1)
        self.assertIn("function stage(result)", store)
        self.assertIn('if (guardedWriterEnabled)', store)
        for item in ["TaskJsonNativeCallbackGuardM11q",
                     "TaskJsonGateHostBridgeM11m",
                     "TaskJsonGateTransportM11m.py"]:
            self.assertNotIn(item, store)
            self.assertNotIn(item, shell)
        for state in ("loading", "saving", "ready", "empty",
                      "error", "unsupported"):
            self.assertIn('"' + state + '"', policy)
        # The legacy FileView onSaved still publishes without a host:
        # intentionally unchanged, and NOT claimed to be protected.
        self.assertIn("todo.document = todo.pendingDocument", store)

    def test_evidence_and_faults_never_include_actual_task_paths(self):
        bridge = (ROOT / "services/projects/TaskJsonGateHostBridgeM11m.qml").read_text()
        panel = (ROOT / "TaskJsonGateHarnessM11m.qml").read_text()
        evidence = (ROOT / "services/projects/TaskFileViewNativeEvidenceM11i.js").read_text()
        helper = (ROOT / "services/projects/TaskJsonNativeCallbackGuardM11q.js").read_text()
        self.assertIn("m11l-tasks-copy/todo-copy.json", bridge)
        self.assertIn("TaskFileViewNativeEvidenceM11i.js", bridge)
        self.assertIn("TaskJsonNativeCallbackGuardM11q.js", bridge)
        self.assertIn('armedTestFault: "NONE"', bridge)
        self.assertIn("function cycleSyntheticFault()", bridge)
        self.assertIn("function maybeSyntheticFault(point)", bridge)
        self.assertIn('if (bridge.maybeSyntheticFault("AFTER_SAVED")) return', bridge)
        self.assertIn("Qt.callLater(function()", bridge)
        self.assertIn("NativeEvidence.summarize(nativeEvidence)", bridge)
        self.assertIn('model: ["NEW TEST", "EXISTING", "INCREMENT", "FREEZE", "STOP", "ARM FAULT"]', panel)
        self.assertIn("OBSERVATION_ONLY_NOT_NATIVE_ACCEPTED", evidence)
        self.assertIn("function canDeferredReadback(now, captured)", helper)
        self.assertIn("function settledReplyEligible(state, reply, expectedEpoch)", helper)
        self.assertNotIn("ApolloHubTodoStore", bridge + helper)
        self.assertNotIn("Quickshell.dataDir", bridge + helper)
        self.assertNotIn("apollo-hub-todo-v1.json", bridge + helper)

    def test_approval_boundaries_in_document(self):
        document = (ROOT / "docs/tasks-native-callback-preflight-m11q.md").read_text()
        for title in ("IMPLEMENTATION", "HOW TO USE", "VERIFY", "WATCH OUT FOR",
                      "CHECKLIST", "NEXT", "DECISIONS"):
            self.assertIn("## " + title, document)
        self.assertIn("not an active or installable production writer", document.lower())
        for label in ("AFTER_RESERVE", "AFTER_SAVED",
                      "AFTER_READBACK", "AFTER_SETTLEMENT"):
            self.assertIn(label, document)
        self.assertIn("separately authorized", document)


if __name__ == "__main__":
    unittest.main(verbosity=2)
