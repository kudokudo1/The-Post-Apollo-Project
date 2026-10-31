#!/usr/bin/env python3
"""M12b read-only disabled-production-integration preflight contract tests.

Tests only repository source and a synthetic review record. This does not
access any user's Quickshell data, OS host, real task JSON, or task journal.
Passing checks do not authenticate or activate a production integration.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "tests/tasks/fixtures/task_disabled_integration_preflight_m12b.json"
REPORT = ROOT / "docs/tasks-disabled-production-integration-preflight-m12b.md"
GATES = {
    "RELEASE_TRUST", "OS_HOST_OWNER", "REAL_SOURCE_AUTHORIZATION",
    "INDEPENDENT_BACKUP", "NATIVE_STAGE_ATTRIBUTION",
    "ASYNC_UI_ACCEPTANCE", "RESTART_AND_FREEZE", "CODE_ONLY_ROLLBACK",
    "NATIVE_RUNTIME_ACCEPTANCE", "ACTIVATION_DECISION",
}
STAGES = (
    "TRUSTED_RELEASE", "AUTHENTICATED_OS_HOST", "EXACT_SOURCE_PERMISSION",
    "SOURCE_AND_SCHEMA_PREFLIGHT", "BYTE_EXACT_BACKUP_READBACK",
    "JOURNAL_OWNER_ATTACH", "CANDIDATE_VALIDATE", "DURABLE_STAGE_RESERVE",
    "SINGLE_FILEVIEW_WRITE", "NATIVE_DEFERRED_READBACK", "DURABLE_OS_SETTLE",
    "CONFIRMED_UI_PUBLISH", "FREEZE_OR_RECOVERY_REVIEW", "CODE_ONLY_ROLLBACK",
)


class DisabledIntegrationPreflight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_contract_is_disabled_and_does_not_self_certify(self):
        r = self.review
        self.assertEqual(r["schemaVersion"], 1)
        self.assertEqual(r["milestone"], "M12b")
        self.assertEqual(r["classification"],
                         "PROPOSED_DISABLED_ONLY_PRODUCTION_INTEGRATION_PREFLIGHT")
        self.assertTrue(r["preflight"]["testOnly"])
        self.assertTrue(all(value is False for key, value in r["preflight"].items()
                            if key != "testOnly"))
        gates = r["independentChecks"]
        self.assertEqual(len(gates), len(GATES))
        self.assertEqual({gate["id"] for gate in gates}, GATES)
        self.assertTrue(all(gate["status"] == "OPEN" for gate in gates))
        for gate in gates:
            self.assertGreater(len(gate["evidence"]), 45)
            self.assertGreater(len(gate["testLineage"]), 10)

    def test_production_store_remains_one_unmodified_legacy_writer(self):
        r = self.review["entrypoints"]
        code = (ROOT / r["singleton"]).read_text(encoding="utf-8")
        policy = (ROOT / r["policy"]).read_text(encoding="utf-8")
        shell = (ROOT / "shell.qml").read_text(encoding="utf-8")
        self.assertIn(r["legacyGuardConstant"], code)
        self.assertEqual(len(re.findall(r"\bFileView\s*\{", code)), 1)
        self.assertEqual(code.count("todoFile.setText("), 1)
        self.assertEqual(code.count("return stage(TodoPolicy."), 9)
        self.assertIn("function stage(result)", code)
        self.assertIn("if (guardedWriterEnabled)\n            return false;", code)
        self.assertIn('Quickshell.dataDir + "/apollo-hub-todo-v1.json"', code)
        self.assertEqual(r["actualSourceSuffix"], "/apollo-hub-todo-v1.json")
        self.assertTrue(r["oneFileView"])
        self.assertTrue(r["nineMutationRoutes"])
        self.assertFalse(r["hostActuallyConnected"])
        self.assertTrue(r["existingNativeOnSavedPublishesPending"])
        self.assertIn("todo.document = todo.pendingDocument;", code)
        self.assertIn("onSaved:", code)
        self.assertIn("function view(storageState, doc, issue)", policy)
        for path in ("TaskIntegrationPreflightM12b", "M12bHost", "TaskGuardedCompletionModelM12a"):
            self.assertNotIn(path, shell + code)

    def test_source_parser_and_test_only_host_restriction_unmodified(self):
        code = (ROOT / "services/projects/TaskJsonGateCandidateM11l.py"
                ).read_text(encoding="utf-8")
        self.assertIn('path.name == "m11l-tasks-copy"', code)
        self.assertIn('self.source = folder / "todo-copy.json"', code)
        self.assertIn("def parse_task_document(raw):", code)
        self.assertNotIn("apollo-hub-todo-v1.json", code)
        later = (ROOT / "tests/tasks/fixtures/TaskSyntheticBackupRollbackM11z.py"
                 ).read_text(encoding="utf-8")
        self.assertIn('FOLDER = "m11z-synthetic-copy"', later)
        self.assertNotIn("Quickshell.dataDir", later)

    def test_ordering_explicitly_excludes_unverified_callback_promotion(self):
        stages = self.review["bindingOrder"]
        self.assertEqual(tuple(stages), STAGES)
        self.assertLess(stages.index("EXACT_SOURCE_PERMISSION"),
                        stages.index("SOURCE_AND_SCHEMA_PREFLIGHT"))
        self.assertLess(stages.index("BYTE_EXACT_BACKUP_READBACK"),
                        stages.index("DURABLE_STAGE_RESERVE"))
        self.assertLess(stages.index("DURABLE_STAGE_RESERVE"),
                        stages.index("SINGLE_FILEVIEW_WRITE"))
        self.assertLess(stages.index("SINGLE_FILEVIEW_WRITE"),
                        stages.index("NATIVE_DEFERRED_READBACK"))
        self.assertLess(stages.index("NATIVE_DEFERRED_READBACK"),
                        stages.index("DURABLE_OS_SETTLE"))
        self.assertLess(stages.index("DURABLE_OS_SETTLE"),
                        stages.index("CONFIRMED_UI_PUBLISH"))
        self.assertGreaterEqual(len(self.review["failClosedCases"]), 20)
        for key in ("LATE_ONSAVED", "AMBIGUOUS_CALLBACK",
                    "SETTLED_WITHOUT_UI_ACK", "AUTO_DATA_RESTORE",
                    "REVIEW_ERASES_CONFIRMED", "SYNTHETIC_OWNER_AS_REAL"):
            self.assertIn(key, self.review["failClosedCases"])

    def test_synthetic_proofs_cannot_be_promoted_to_live_authority(self):
        claims = self.review["syntheticOnlyCannotAuthorize"]
        self.assertGreaterEqual(len(claims), 8)
        self.assertIn("boolean:journalSettled", claims)
        self.assertIn("status:GitHubCIPassed", claims)
        self.assertIn("pidfd:untrustedLauncher", claims)
        self.assertIn("signed:CIOnlyEphemeralKey", claims)
        # All 10 external checks remain independently OPEN even with tests green.
        for gate in self.review["independentChecks"]:
            self.assertEqual(gate["status"], "OPEN")

    def test_ui_decision_not_presumed_accepted(self):
        ui = self.review["currentUI"]
        self.assertEqual(ui["mutationReturn"], "SYNCHRONOUS_BOOLEAN")
        self.assertEqual(ui["meaningOfTrue"],
                         "LEGACY_FILEVIEW_WRITE_STARTED_NOT_DURABLE")
        self.assertEqual(set(ui["proposedChoices"]),
                         {"BOOLEAN_MEANS_QUEUED_ONLY",
                          "TICKET_PLUS_EXPLICIT_COMPLETION"})
        self.assertFalse(ui["choiceAccepted"])
        self.assertFalse(ui["lastConfirmedOverlayImplemented"])
        self.assertTrue(ui["errorViewMayHideConfirmed"])
        self.assertEqual(ui["knownStates"],
                         ["loading","saving","ready","empty","error","unsupported"])
        policy = (ROOT / self.review["entrypoints"]["policy"]).read_text()
        self.assertIn("var safe = available ? clone(doc) : emptyDocument();", policy)
        self.assertIn('writable:state === "ready" || state === "empty"', policy)
        self.assertEqual(len(ui["consumers"]), 4)
        for p in ui["consumers"]:
            self.assertTrue((ROOT / p).is_file(), p)

    def test_future_patch_contract_keeps_decisions_and_scope_open(self):
        names = [x["name"] for x in self.review["futurePatchSequence"]]
        self.assertEqual(names, ["M12c", "M12d", "M12e"])
        self.assertTrue(all(x["state"] == "PROPOSED"
                            for x in self.review["futurePatchSequence"]))
        forbidden = set(self.review["forbiddenByM12bChanges"])
        self.assertTrue({"services/hub/ApolloHubTodoStore.qml",
                         "services/hub/ApolloHubTodoPolicy.js", "shell.qml",
                         "operator_machine", "real_TASKS_data"} <= forbidden)
        report = REPORT.read_text(encoding="utf-8")
        for section in ("IMPLEMENTATION", "HOW TO USE", "VERIFY",
                        "WATCH OUT FOR", "CHECKLIST", "NEXT", "DECISIONS"):
            self.assertIn("## " + section, report)
        for token in ("M11x", "M11y", "M11z", "M12a",
                      "M12b", "OPEN", "production", "source",
                      "onSaved", "operator"):
            self.assertIn(token.lower(), report.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
