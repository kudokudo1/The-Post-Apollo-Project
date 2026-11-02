#!/usr/bin/env python3
"""M12u: prove PASS requires both expected native markers and disk evidence.

Uses only TemporaryDirectory fixtures. Never starts Quickshell, touches
real tasks, changes test env, or imports a production data file.
"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "tests/tasks/fixtures/TaskNativeSelfReportRunnerM12u.py"
spec = importlib.util.spec_from_file_location("m12u_report", MODULE)
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


class SelfReportEvidence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="m12u-source-test-")
        self.path = Path(self.tmp.name) / report.SOURCE
        self.data = {
            "version": 3, "nextId": 2, "nextProjectId": 1,
            "projects": [],
            "tasks": [{
                "id": "t1", "title": report.TITLE, "done": False,
                "createdAtMs": 1000, "updatedAtMs": 1000,
                "priority": "none", "description": "", "dueDate": None,
                "projectId": None,
            }],
        }
        self.write()
        self.events = [
            f"WARN: M12U_STAGE|{s}|PASS\n" for s in report.EXPECTED
        ] + ["WARN: M12U_RESULT|PASS|NATIVE_SEQUENCE\n"]

    def tearDown(self):
        self.tmp.cleanup()

    def write(self):
        self.path.write_text(json.dumps(self.data), encoding="utf-8")

    def check(self, events=None):
        return report.evidence(
            self.events if events is None else events, self.path)

    def test_only_full_native_and_disk_sequence_passes(self):
        result = self.check()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["reason"], "NATIVE_AND_DISK_AGREE")
        self.assertEqual(result["count"], 1)
        self.assertEqual(len(result["sha256"]), 64)

    def test_saved_disk_alone_cannot_pass(self):
        self.assertEqual(self.check([])["reason"],
                         "NATIVE_STAGE_SEQUENCE_MISSING")

    def test_ticket_refusal_and_reload_must_both_be_observed(self):
        for name in report.EXPECTED:
            reduced = [line for line in self.events if name not in line]
            self.assertEqual(self.check(reduced)["status"], "FAIL")

    def test_native_failure_and_duplicate_terminal_reports_fail(self):
        self.assertEqual(self.check(self.events[:-1]+[
            "WARN: M12U_RESULT|FAIL|NATIVE_CALLBACK_TIMEOUT\n"
        ])["reason"], "NATIVE_RESULT_NOT_CONFIRMED")
        self.assertEqual(self.check(self.events+self.events[-1:])["status"],
                         "FAIL")
        swapped = self.events[:]
        swapped[0], swapped[1] = swapped[1], swapped[0]
        self.assertEqual(self.check(swapped)["status"], "FAIL")

    def test_disk_changed_after_native_report_cannot_pass(self):
        self.data["tasks"][0]["title"] = "external-edit"
        self.write()
        self.assertEqual(self.check()["reason"], "UNEXPECTED_SYNTHETIC_TASK")

    def test_malformed_duplicate_key_and_unsupported_version_fail(self):
        self.path.write_text('{"version":3,"version":3}\n', encoding="utf-8")
        self.assertEqual(self.check()["status"], "FAIL")
        self.data["version"] = 999
        self.write()
        self.assertEqual(self.check()["reason"], "INVALID_TASKS_VERSION")

    def test_extra_task_and_missing_file_fail(self):
        self.data["tasks"].append(dict(self.data["tasks"][0]))
        self.write()
        self.assertEqual(self.check()["reason"], "UNEXPECTED_TASK_COUNT")
        self.path.unlink()
        self.assertEqual(self.check()["reason"], "FIXTURE_READBACK_UNAVAILABLE")

    def test_symlink_and_hardlink_fail(self):
        target = Path(self.tmp.name) / "elsewhere.json"
        target.write_text(json.dumps(self.data), encoding="utf-8")
        self.path.unlink()
        self.path.symlink_to(target)
        self.assertEqual(self.check()["reason"], "UNSAFE_FIXTURE_SOURCE")
        self.path.unlink()
        self.path.hardlink_to(target)
        self.assertEqual(self.check()["reason"], "UNSAFE_FIXTURE_SOURCE")

    def test_unmounted_qml_with_guarded_private_data_root(self):
        root_qml = (ROOT / "TaskNativeSelfReportM12u.qml").read_text()
        shell = (ROOT / "shell.qml").read_text()
        store = (ROOT / "services/hub/ApolloHubTodoStore.qml").read_text()
        self.assertIn("//@ pragma DataDir $BASE/post-apollo-m12u-fixture",
                      root_qml)
        self.assertIn("//@ pragma StateDir $BASE/post-apollo-m12u-state",
                      root_qml)
        self.assertIn("POST_APOLLO_M12U_DISPOSABLE", root_qml)
        self.assertIn("readonly property bool safe:", root_qml)
        self.assertIn("isolatedPath", root_qml)
        self.assertIn("!ApolloHubTodoStore.ticketProducerEnabled", root_qml)
        self.assertIn("!ApolloHubTodoStore.guardedWriterEnabled", root_qml)
        self.assertIn("ApolloHubTodoStore.addTask(", root_qml)
        self.assertIn("ApolloHubTodoStore.reloadFromDisk(", root_qml)
        self.assertNotIn("TaskNativeSelfReportM12u", shell)
        self.assertNotIn("FileView {", root_qml)
        self.assertNotIn("Process {", root_qml)
        self.assertEqual(store.count("FileView {"), 1)
        self.assertIn("readonly property bool ticketProducerEnabled: false",
                      store)
        self.assertIn("readonly property bool guardedWriterEnabled: false",
                      store)


if __name__ == "__main__":
    unittest.main()
