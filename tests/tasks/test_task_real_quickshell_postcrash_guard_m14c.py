#!/usr/bin/env python3
"""M14c guard: the real Quickshell CI entrypoint cannot reach live TASKS."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
ROOT_QML = ROOT / "TaskPostCrashNativeSmokeM14c.qml"
RUNNER = ROOT / "tests/tasks/native_quickshell_postcrash_smoke_m14c.py"
M14B = ROOT / "tests/tasks/fixtures/TaskPostCrashReviewLabM14b.qml"
SHELL = ROOT / "shell.qml"
STORE = ROOT / "services/hub/ApolloHubTodoStore.qml"
RECOVERY = ROOT / "widgets/tasks/TaskRecoveryStatusPaneM13q.qml"
CONNECTIONS = ROOT / "services/connections/ConnectionsBroker.qml"


def runner():
    spec = importlib.util.spec_from_file_location("m14c_guard_runner", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class M14cNativeIsolationGuard(unittest.TestCase):
    def test_unmounted_qml_root_and_exact_disposable_gate(self):
        qml = ROOT_QML.read_text()
        self.assertIn("ShellRoot {", qml)
        self.assertIn("TaskPostCrashReviewLabM14b {", qml)
        self.assertIn("CI_DISPOSABLE_ONLY", qml)
        self.assertIn("POST_APOLLO_TASKS_M14C_NATIVE", qml)
        self.assertIn("POST_APOLLO_TASKS_M14C_FIXTURE", qml)
        self.assertIn("POST_APOLLO_TASKS_M14C_SCENARIO", qml)
        self.assertIn("if(!smoke.armed", qml)
        self.assertIn("if(!reviewLab.inspectOnce())", qml)
        self.assertIn("readonly property bool armed:", qml)
        self.assertIn("M14C_NATIVE_PASS_", qml)
        self.assertIn("M14C_NATIVE_TIMEOUT", qml)
        self.assertIn("Qt.quit()", qml)
        self.assertIn("Quickshell.watchFiles=false", qml)
        self.assertNotIn(ROOT_QML.name, SHELL.read_text())
        self.assertNotIn(ROOT_QML.name, STORE.read_text())
        self.assertNotIn(ROOT_QML.name, RECOVERY.read_text())
        for disabled in ("FileView {", "Process {", ".setText(",
                         "Qt.openUrlExternally", "writeFile("):
            self.assertNotIn(disabled, qml)

    def test_real_m14b_component_is_reused_and_not_a_second_writer(self):
        lab = M14B.read_text()
        self.assertIn("TaskPostCrashSourceReviewM13y.py", lab)
        self.assertIn("ReviewPolicy.syntheticResult(value)", lab)
        self.assertIn("onClicked: lab.inspectOnce()", lab)
        self.assertEqual(lab.count("Process {"), 1)
        self.assertEqual(lab.count("FileView {"), 0)
        self.assertIn("draftDeletionAuthorized: false", lab)
        self.assertIn("realTaskDataAccessAuthorized: false", lab)
        store = STORE.read_text()
        self.assertEqual(store.count("FileView {"), 1)
        self.assertEqual(store.count("todoFile.setText("), 1)
        self.assertIn("readonly property bool encryptedRecoveryEnabled: false", store)
        self.assertIn("readonly property bool ticketProducerEnabled: false", store)
        self.assertIn("readonly property bool credentialActionsEnabled: false",
                      CONNECTIONS.read_text())

    def test_runner_refuses_non_ci_without_even_looking_for_quickshell(self):
        mod = runner()
        previous_github = os.environ.pop("GITHUB_ACTIONS", None)
        previous_gate = os.environ.pop("POST_APOLLO_M14C_DISPOSABLE_CI", None)
        try:
            with self.assertRaisesRegex(RuntimeError,
                                        "M14C_REFUSES_NON_CI_NATIVE_LAUNCH"):
                mod.run("baseline")
        finally:
            if previous_github is not None:
                os.environ["GITHUB_ACTIONS"] = previous_github
            if previous_gate is not None:
                os.environ["POST_APOLLO_M14C_DISPOSABLE_CI"] = previous_gate

    def test_fixture_requires_owner_private_tree_and_real_synthetic_receipts(self):
        mod = runner()
        with tempfile.TemporaryDirectory(prefix="m14c-real-qs-") as tmp:
            base = Path(tmp)
            directory = base / "m11e-fileview-test"
            db, source, owner = mod.create_fixture(directory, "baseline")
            try:
                mod.assert_disposable(db, base)
                self.assertTrue(source.is_file())
                initial = mod.snapshot(db)
                self.assertEqual(len(initial[0]), 1)
                self.assertEqual(len(initial[1]), 1)
                self.assertEqual(initial[1][0][-1], "RESERVED")
            finally:
                if owner is not None:
                    owner.close()

    def test_no_live_source_path_or_credentials_in_runner(self):
        text = RUNNER.read_text()
        self.assertIn('os.environ.get("GITHUB_ACTIONS")', text)
        self.assertIn("POST_APOLLO_M14C_DISPOSABLE_CI", text)
        self.assertIn("TemporaryDirectory(prefix=\"m14c-real-qs-\")", text)
        self.assertIn('"QT_QPA_PLATFORM": "offscreen"', text)
        self.assertIn('"WAYLAND_DISPLAY": ""', text)
        self.assertIn('"DISPLAY": ""', text)
        self.assertIn("XDG_DATA_HOME", text)
        self.assertIn("XDG_RUNTIME_DIR", text)
        self.assertIn("before_journal = snapshot(db)", text)
        self.assertIn("snapshot(db) != before_journal", text)
        self.assertIn("M14C_SOURCE_WAS_MODIFIED_BY_INSPECTION", text)
        for bad in (
            "apollo-hub-todo-v1.json", "secret-tool", "systemctl",
            "sudo ", "pkill", "killall", "os.system(", "shell=True",
        ):
            self.assertNotIn(bad, text)


if __name__ == "__main__":
    unittest.main()
