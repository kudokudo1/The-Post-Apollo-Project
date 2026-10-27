#!/usr/bin/env python3
"""Static M11n evidence provenance and nonactivation boundary verification."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "tests/tasks/fixtures/task_m11n_native_evidence_20261026.json"


class M11nEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    def test_observations_are_exact_and_not_overclaimed(self):
        item = self.data
        self.assertEqual(item["milestone"], "M11n")
        self.assertEqual(item["classification"],
                         "OPERATOR_TERMINAL_OBSERVED_PARTIAL_NATIVE_ACCEPTANCE")
        self.assertTrue(item["fixtureOnly"])
        self.assertFalse(item["storedPrivatePaths"])
        got = item["observed"]
        self.assertEqual(got["standaloneQuickshellLaunch"], "Configuration Loaded")
        self.assertEqual(got["finalTaskTitle"], "M11M_TEST_2")
        self.assertEqual(got["journalPhase"], "RECOVERY_REVIEW")
        self.assertEqual(got["journalEpoch"], 3)
        self.assertIsNone(got["journalPendingStage"])
        self.assertIs(got["journalSourceHashMatchesFile"], True)
        self.assertEqual(got["journalReason"], "FRESH_OWNER_MUST_REVIEW")
        self.assertGreaterEqual(len(item["unobserved"]), 5)
        self.assertEqual(item["acceptance"]["completeNativeButtonSequence"],
                         "not_proven")
        self.assertEqual(item["acceptance"]["productionWriterGate"],
                         "not_implemented")
        self.assertEqual(item["acceptance"]["localProductionActivation"],
                         "not_authorized")
        self.assertEqual(item["acceptance"]["finalOperatorAcceptance"],
                         "not_claimed")

    def test_no_private_paths_in_evidence(self):
        raw = EVIDENCE.read_text(encoding="utf-8")
        doc = (ROOT / "docs/tasks-native-evidence-and-recovery-m11n.md").read_text(
            encoding="utf-8")
        for private_indicator in (
            "/var/home/", "/home/mapple/", "/mnt/data/", "m11n-native-VrHXMo"
        ):
            self.assertNotIn(private_indicator, raw)
            self.assertNotIn(private_indicator, doc)
        self.assertNotIn('"tasks": [', raw)

    def test_exact_epoch_transitions_and_production_off(self):
        host = (ROOT / "services/projects/TaskJsonGateCandidateM11l.py").read_text(
            encoding="utf-8")
        store = (ROOT / "services/hub/ApolloHubTodoStore.qml").read_text(
            encoding="utf-8")
        shell = (ROOT / "shell.qml").read_text(encoding="utf-8")
        self.assertIn("SET phase='RECOVERY_REVIEW'", host)
        self.assertIn("epoch=epoch+1, writer=?", host)
        self.assertIn("epoch=epoch+1, reason='EXPLICIT_TEST_FREEZE'", host)
        self.assertIn("readonly property bool guardedWriterEnabled: false", store)
        self.assertEqual(store.count("FileView {"), 1)
        self.assertEqual(store.count("todoFile.setText("), 1)
        self.assertNotIn("TaskJsonGateHostBridgeM11m", shell)
        self.assertNotIn("TaskJsonGateHostBridgeM11m", store)
        self.assertNotIn("TaskJsonGateTransportM11m.py", store)


if __name__ == "__main__":
    unittest.main(verbosity=2)
