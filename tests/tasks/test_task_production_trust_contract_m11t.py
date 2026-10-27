#!/usr/bin/env python3
"""M11t source-only trust / rollback acceptance contract.

Reads GitHub checkout source and a sanitized record, never user TASKS JSON.
This does NOT verify executable identity, a native callback or runtime safety.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/tasks/fixtures/task_production_trust_review_m11t.json"
DOC = ROOT / "docs/tasks-production-trust-and-rollback-m11t.md"
FAULTS = {
    "AFTER_RESERVE": (0, True, "RESERVED", True),
    "AFTER_SAVED": (1, True, "RESERVED", False),
    "AFTER_READBACK": (1, True, "RESERVED", False),
    "AFTER_SETTLEMENT": (1, False, "SETTLED", True),
}
GATES = {
    "TRUST_EXEC", "PROCESS_BINDING", "SOURCE_BACKUP", "STAGE_CALLBACK",
    "UI_CONTRACT", "RECOVERY_FREEZE", "ROLLBACK", "RUNTIME_ACCEPTANCE",
    "ACTIVATION_APPROVAL",
}


class ProductionTrustReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_contract_stays_a_proposal_without_mutation_authority(self):
        data = self.review
        self.assertEqual(data["schemaVersion"], 1)
        self.assertEqual(data["milestone"], "M11t")
        self.assertEqual(data["classification"],
                         "PROPOSED_PRODUCTION_TRUST_ROLLBACK_CONTRACT_ONLY")
        self.assertEqual(data["predecessorContracts"],
                         ["M11k", "M11q", "M11r", "M11s"])
        self.assertEqual(data["authorizations"]["contractProposalOnly"], True)
        self.assertTrue(all(value is False for key, value
                            in data["authorizations"].items()
                            if key != "contractProposalOnly"))
        self.assertTrue(all(value is False for value
                            in data["changedByM11t"].values()))
        self.assertTrue(all(value is False for value
                            in data["testOnlyLimits"].values()))

    def test_operator_synthetic_native_evidence_is_not_promoted_to_prod(self):
        ev = self.review["operatorNativeEvidence"]
        self.assertEqual(ev["classification"],
            "OBSERVED_SYNTHETIC_QML_PLUS_INDEPENDENT_READ_ONLY_JOURNAL")
        self.assertFalse(ev["rawScreenshotsInRepository"])
        self.assertFalse(ev["inspectorObservedNativeCallbacks"])
        self.assertFalse(ev["originalM11sBatchAggregateClaimedComplete"])
        self.assertTrue(ev["finalSettlementCaseUsesSeparateReplacementFixture"])
        cases = ev["cases"]
        self.assertEqual(len(cases), 4)
        self.assertEqual({c["fault"] for c in cases}, set(FAULTS))
        for case in cases:
            with self.subTest(fault=case["fault"]):
                self.assertIs(case["nativeScreenObserved"], True)
                self.assertIs(
                    case["inspectorExpectationMetBeforeAndAfterExisting"], True)
                counter, pending, stage, match = FAULTS[case["fault"]]
                for key, phase, epoch in (
                        ("before", "JSON_ACTIVE", 0),
                        ("afterExisting", "RECOVERY_REVIEW", 1)):
                    snap = case[key]
                    self.assertEqual(set(snap), {
                        "counter", "epoch", "phase", "pending",
                        "stageState", "sourceHashMatchesJournal"})
                    self.assertEqual(snap["counter"], counter)
                    self.assertEqual(snap["epoch"], epoch)
                    self.assertEqual(snap["phase"], phase)
                    self.assertIs(snap["pending"], pending)
                    self.assertEqual(snap["stageState"], stage)
                    self.assertIs(snap["sourceHashMatchesJournal"], match)
        m11s = (ROOT / "tests/tasks/fixtures/TaskNativeFaultMatrixM11s.py"
                ).read_text(encoding="utf-8")
        inspector = (ROOT / "tests/tasks/fixtures/TaskNativeFaultInspectorM11r.py"
                     ).read_text(encoding="utf-8")
        self.assertIn('"nativeCallbacksObservedByThisTool":False', m11s)
        self.assertIn('"nativeCallbackTraceObserved": False', inspector)
        self.assertIn("mode=ro", inspector)
        self.assertIn("RECOVERY_REVIEW", inspector)

    def test_production_source_remains_single_legacy_writer(self):
        source = self.review["existingProduction"]
        self.assertEqual(source["fileViewCount"], 1)
        self.assertEqual(source["mutationMethodCount"], 9)
        self.assertFalse(source["legacyHasOSOwnedLock"])
        self.assertFalse(source["legacyFileViewSavedIsDurableSettled"])
        store = (ROOT / source["singleton"]).read_text(encoding="utf-8")
        policy = (ROOT / source["policy"]).read_text(encoding="utf-8")
        shell = (ROOT / "shell.qml").read_text(encoding="utf-8")
        self.assertIn(source["guardFlag"], store)
        self.assertIn('Quickshell.dataDir + "/apollo-hub-todo-v1.json"', store)
        self.assertEqual(len(re.findall(r"\\bFileView\\s*\\{", store)), 1)
        self.assertEqual(store.count("todoFile.setText("), 1)
        self.assertEqual(store.count("return stage(TodoPolicy."), 9)
        self.assertIn("function stage(result)", store)
        self.assertIn("if (guardedWriterEnabled)", store)
        self.assertIn("todo.document = todo.pendingDocument;", store)
        self.assertIn("TodoPolicy.view(storageState, document, errorCode)", store)
        self.assertEqual(source["publicStates"], [
            "loading", "saving", "ready", "empty", "error", "unsupported"])
        for state in source["publicStates"]:
            self.assertIn('"' + state + '"', policy)
        for prohibited in ("TaskJsonGateHostBridgeM11m",
                           "TaskJsonGateTransportM11m",
                           "TaskJsonNativeCallbackGuardM11q"):
            self.assertNotIn(prohibited, store)
            self.assertNotIn(prohibited, shell)

    def test_test_host_remains_test_only_and_nonce_is_not_auth(self):
        bridge = (ROOT / "services/projects/TaskJsonGateHostBridgeM11m.qml"
                  ).read_text(encoding="utf-8")
        transport = (ROOT / "tests/tasks/fixtures/TaskJsonGateTransportM11m.py"
                     ).read_text(encoding="utf-8")
        candidate = (ROOT / "services/projects/TaskJsonGateCandidateM11l.py"
                     ).read_text(encoding="utf-8")
        self.assertIn('fixturePath.endsWith("/m11l-tasks-copy/todo-copy.json")',
                      bridge)
        self.assertIn("readonly property bool liveWriterAuthorized: false",
                      bridge)
        self.assertIn("readonly property bool productionActivation: false",
                      bridge)
        self.assertIn("sessionGeneration", bridge)
        self.assertIn("Qt.callLater(function()", bridge)
        self.assertIn("secrets.token_hex(24)", transport)
        self.assertIn("sessionId", transport)
        self.assertIn("JOURNAL_SCHEMA = 2", candidate)
        self.assertIn("fcntl.flock", candidate)
        self.assertNotIn("apollo-hub-todo-v1.json", bridge + transport)
        self.assertIn("m11l-tasks-copy", candidate)

    def test_all_production_gates_remain_open_and_not_self_certifying(self):
        gates = self.review["gates"]
        self.assertEqual(len(gates), len(GATES))
        self.assertEqual({x["id"] for x in gates}, GATES)
        for gate in gates:
            self.assertEqual(gate["state"], "OPEN", gate["id"])
            self.assertGreater(len(gate["required"]), 35)

    def test_report_links_provenance_and_hospital_sections(self):
        doc = DOC.read_text(encoding="utf-8")
        for title in ("IMPLEMENTATION", "HOW TO USE", "VERIFY",
                      "WATCH OUT FOR", "CHECKLIST", "NEXT", "DECISIONS"):
            self.assertIn("## " + title, doc)
        for milestone in ("M11k", "M11q", "M11r", "M11s"):
            self.assertIn(milestone, doc)
        for fault in FAULTS:
            self.assertIn(fault, doc)
        for gate in GATES:
            self.assertIn(gate, doc)
        self.assertIn("PROPOSED CONTRACT ONLY", doc)
        self.assertIn("new one-off replacement fixture", doc)
        self.assertIn("a draft/CI pass".lower(), doc.lower().replace(" is not", " is not")
                      if "a draft/CI pass" in doc.lower()
                      else "A draft/CI pass".lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
