#!/usr/bin/env python3
"""M11x source-only proposed production-host and UI architecture review.

Does not read Quickshell dataDir, user task JSON, any live SQLite DB, or
the operator's modified Fedora checkout. An asserted source contract is
NOT authorization, executable attestation or native runtime acceptance.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "tests/tasks/fixtures/task_production_architecture_review_m11x.json"
REPORT = ROOT / "docs/tasks-production-host-architecture-m11x.md"
GATES = {"TRUST_EXEC","PROCESS_BINDING","SOURCE_BACKUP","STAGE_CALLBACK",
         "UI_CONTRACT","RECOVERY_FREEZE","ROLLBACK","RUNTIME_ACCEPTANCE",
         "ACTIVATION_APPROVAL"}
DECISIONS = {"INDEPENDENT_TRUST_ANCHOR","SOURCE_BACKUP_BOUNDARY",
             "ASYNC_MUTATION_RESULT","GUARDED_LAST_CONFIRMED_SNAPSHOT",
             "ROLLBACK_AND_RECOVERY"}


class ArchitectureContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.report = REPORT.read_text(encoding="utf-8")

    def test_review_does_not_self_authorize(self):
        data = self.data
        self.assertEqual(data["schemaVersion"], 1)
        self.assertEqual(data["milestone"], "M11x")
        self.assertEqual(data["classification"], "PROPOSED_ARCHITECTURE_REVIEW_ONLY")
        self.assertEqual(data["inherits"], ["M11k","M11t","M11w"])
        self.assertIs(data["permission"]["architectureReview"], True)
        self.assertTrue(all(value is False for key, value in data["permission"].items()
                            if key != "architectureReview"))
        self.assertTrue(all(value is False for value in data["changedByM11x"].values()))
        self.assertEqual({v["id"] for v in data["gates"]}, GATES)
        self.assertTrue(all(v["state"] == "OPEN" for v in data["gates"]))
        self.assertEqual({v["id"] for v in data["architectureDecisions"]}, DECISIONS)
        for decision in data["architectureDecisions"]:
            self.assertEqual(decision["decision"], "OPEN")
            self.assertGreaterEqual(len(decision["choices"]), 2)
            self.assertGreaterEqual(len(decision["unacceptable"]), 2)
        self.assertGreaterEqual(len(data["failureTestsPending"]), 15)

    def test_exact_live_singleton_remains_unactivated_and_unfenced(self):
        record = self.data["authority"]
        store = (ROOT / record["path"]).read_text(encoding="utf-8")
        self.assertIn(record["hardDisabledFlag"], store)
        self.assertIn('Quickshell.dataDir + "/apollo-hub-todo-v1.json"', store)
        self.assertEqual(record["storageSuffix"], "/apollo-hub-todo-v1.json")
        self.assertEqual(len(re.findall(r"\bFileView\s*\{", store)), 1)
        self.assertEqual(store.count("todoFile.setText("), 1)
        self.assertEqual(store.count("return stage(TodoPolicy."), 9)
        self.assertIn("function stage(result)", store)
        self.assertIn("pendingDocument = result.document", store)
        self.assertIn("todo.document = todo.pendingDocument;", store)
        self.assertIn("onSaved:", store)
        self.assertIn("return true;", store)
        self.assertTrue(record["publicMutationReturnsSynchronousBoolean"])
        self.assertTrue(record["onSavedPublishesWithoutHostReadback"])
        self.assertFalse(record["hostProductionIntegrationImplemented"])
        self.assertFalse(record["taskSqliteMigrationImplemented"])
        for test_name in ("TaskBoundJournalChildM11w",
                          "TaskBoundJournalProbeM11w",
                          "TaskJsonGateHostBridgeM11m"):
            self.assertNotIn(test_name, store)
            self.assertNotIn(test_name, (ROOT / "shell.qml").read_text())

    def test_all_current_mutator_callers_recorded(self):
        callers = self.data["callerContracts"]
        inventory = json.loads(
            (ROOT / "tests/tasks/fixtures/task_writer_gate_inventory_m11d.json"
             ).read_text(encoding="utf-8"))
        self.assertEqual(set(callers["mutationMethods"]),
                         set(inventory["mutationMethods"]))
        self.assertEqual(set(callers["mutationCallers"]),
                         set(inventory["callers"]))
        for name, methods in callers["mutationCallers"].items():
            self.assertEqual(set(methods), set(inventory["callers"][name]))
            source = (ROOT / name).read_text(encoding="utf-8")
            for method in methods:
                with self.subTest(file=name, method=method):
                    self.assertRegex(source,
                          r"\btodoStore\s*\.\s*" + re.escape(method) + r"\s*\(")
        self.assertEqual(set(callers["readonlyConsumers"]),
                         set(inventory["readOnlySurfaces"]))
        self.assertTrue(callers["schedulingCreateAndDateAreSeparateActions"])
        schedule = (ROOT / "widgets/tasks/TaskPlannerSchedulePane.qml"
                    ).read_text(encoding="utf-8")
        self.assertIn("todoStore.addTask(clean)", schedule)
        self.assertIn("todoStore.updateTaskDetails(plan.id, plan.priority", schedule)
        self.assertIn("Never claim both writes were atomic", schedule)

    def test_last_confirmed_visibility_hazard_grounded_in_policy(self):
        view = (ROOT / "services/hub/ApolloHubTodoPolicy.js"
                ).read_text(encoding="utf-8")
        callers = self.data["callerContracts"]
        self.assertEqual(callers["publicStates"],
            ["loading","saving","ready","empty","error","unsupported"])
        self.assertTrue(callers["publicErrorViewMayHideConfirmedRows"])
        self.assertTrue(callers["guardedRecoveryMustPreserveConfirmedRowsAndDrafts"])
        self.assertIn("function view(storageState, doc, issue)", view)
        self.assertIn("var safe = available ? clone(doc) : emptyDocument();", view)
        self.assertIn('writable:state === "ready" || state === "empty"', view)
        for state in callers["publicStates"]:
            self.assertIn('"'+state+'"', view)
        for name in callers["mutationCallers"]:
            self.assertIn("todoSnapshot", (ROOT / name).read_text())

    def test_stage_sequence_and_failure_protection_are_review_only(self):
        required = self.data["requiredOrderedStages"]
        self.assertEqual(len(required), 11)
        self.assertEqual(required[0], "TRUST_PRECHECK")
        self.assertEqual(required[-1], "CODE_ONLY_ROLLBACK")
        self.assertLess(required.index("STAGE_RESERVE"),
                        required.index("SINGLE_FILEVIEW_WRITE"))
        self.assertLess(required.index("HOST_VERIFY_SETTLE"),
                        required.index("CONFIRMED_PUBLISH"))
        self.assertLess(required.index("EXACT_BACKUP"),
                        required.index("STAGE_RESERVE"))
        self.assertIn("WRONG_UI_COMMIT_CONFIRMATION",
                      self.data["failureTestsPending"])
        self.assertIn("DATA_RESTORE_REQUIRES_OPERATOR",
                      self.data["failureTestsPending"])

    def test_hospital_report_and_unresolved_options_are_explicit(self):
        report = self.report
        for title in ("IMPLEMENTATION","HOW TO USE","VERIFY","WATCH OUT FOR",
                      "CHECKLIST","NEXT","DECISIONS"):
            self.assertIn("## "+title, report)
        for prior in ("M11k","M11t","M11u","M11v","M11w"):
            self.assertIn(prior, report)
        for decision in DECISIONS:
            # The human-facing report uses plain-language headings instead
            # of repeating machine IDs in prose, but all decisions stay OPEN.
            self.assertTrue(decision in str(self.data))
        for text in ("Option A", "Option B", "PROPOSED ARCHITECTURE ONLY",
                     "source backup", "last confirmed", "not saved",
                     "operator"):
            self.assertIn(text.lower(), report.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
