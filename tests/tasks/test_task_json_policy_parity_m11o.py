#!/usr/bin/env python3
"""M11o direct JS-vs-Python TASKS JSON admission and test-only fault matrix.

Never reads the operator's task file. All disk tests are fresh, private copies.
Node executes the real ApolloHubTodoPolicy.js, not a rewritten Python oracle.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / "services/projects/TaskJsonGateCandidateM11l.py"
ORACLE = ROOT / "tests/tasks/fixtures/task_json_policy_oracle_m11o.cjs"
spec = importlib.util.spec_from_file_location("m11o_owner", HOST)
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)


def baseline(version=3):
    task = {
        "id": "t1", "title": "Example", "done": False,
        "createdAtMs": 1000, "updatedAtMs": 1000
    }
    doc = {"version": version, "nextId": 2, "tasks": [task]}
    if version >= 2:
        task.update(priority="none", description="", dueDate=None)
    if version == 3:
        task["projectId"] = "p1"
        doc["nextProjectId"] = 2
        doc["projects"] = [{
            "id": "p1", "name": "Example Project",
            "createdAtMs": 900, "updatedAtMs": 900
        }]
    return doc


def encode(doc):
    return json.dumps(doc, ensure_ascii=True, separators=(",", ":"))


def changed(version=3, *, root=None, task=None, project=None):
    doc = baseline(version)
    if root:
        root(doc)
    if task:
        task(doc["tasks"][0])
    if project:
        project(doc["projects"][0])
    return encode(doc)


class PolicyComparisonTests(unittest.TestCase):
    def test_true_js_oracle_matches_or_is_explicitly_stricter(self):
        cases = []
        strict_allowlist = set()

        def add(label, raw, *, strict=False):
            self.assertNotIn(label, [name for name, _ in cases])
            cases.append((label, raw))
            if strict:
                strict_allowlist.add(label)

        for version in (1, 2, 3):
            add(f"canonical_v{version}", encode(baseline(version)))
        add("empty_v3", encode({"version":3, "nextId":1,
                               "nextProjectId":1, "projects":[], "tasks":[]}))
        add("valid_float_integer_version", changed(root=lambda d:d.update(
            version=3.0)))
        add("valid_float_integer_counters", changed(root=lambda d:d.update(
            nextId=2.0, nextProjectId=2.0)))
        add("valid_float_integer_timestamp", changed(task=lambda t:t.update(
            createdAtMs=1000.0, updatedAtMs=1000.0)))
        add("valid_emoji_title_limit", changed(task=lambda t:t.update(title="😀"*80)))
        add("invalid_emoji_title_over_limit", changed(task=lambda t:t.update(title="😀"*81)))
        add("valid_emoji_description_limit", changed(task=lambda t:t.update(
            description="😀"*1000)))
        add("invalid_emoji_description_over_limit", changed(task=lambda t:t.update(
            description="😀"*1001)))
        add("valid_unicode_regular", changed(task=lambda t:t.update(title="Café 中華")))
        add("valid_description_multiline", changed(task=lambda t:t.update(
            description="one\ttwo\nthree\rfour")))
        add("invalid_description_vertical_tab", changed(task=lambda t:t.update(
            description="one\vtwo")))
        add("invalid_title_control", changed(task=lambda t:t.update(title="a\u0001b")))
        add("invalid_title_newline", changed(task=lambda t:t.update(title="a\nb")))
        add("invalid_leading_js_trim_bom", changed(task=lambda t:t.update(
            title="\ufeffExample")))
        add("invalid_trailing_js_trim_nbsp", changed(task=lambda t:t.update(
            title="Example\u00a0")))
        add("invalid_project_name_trim_bom", changed(project=lambda p:p.update(
            name="\ufeffExample")))
        add("valid_leap_day", changed(task=lambda t:t.update(dueDate="2028-02-29")))
        add("invalid_nonleap_day", changed(task=lambda t:t.update(dueDate="2026-02-29")))
        add("invalid_year_zero", changed(task=lambda t:t.update(dueDate="0000-10-26")))
        add("valid_year_0001", changed(task=lambda t:t.update(dueDate="0001-02-03")))
        add("invalid_date_integer", changed(task=lambda t:t.update(dueDate=20261026)))
        add("invalid_missing_project_id", changed(task=lambda t:t.pop("projectId")))
        add("invalid_project_id_array", changed(task=lambda t:t.update(projectId=["p1"])))
        add("invalid_project_id_object", changed(task=lambda t:t.update(
            projectId={"id":"p1"})))
        add("invalid_unknown_project", changed(task=lambda t:t.update(projectId="p2")))
        add("invalid_project_id_zero", changed(project=lambda p:p.update(id="p0")))
        add("invalid_project_id_leading_zero", changed(project=lambda p:p.update(
            id="p01")))
        add("invalid_task_id_zero", changed(task=lambda t:t.update(id="t0")))
        add("invalid_task_id_leading_zero", changed(task=lambda t:t.update(id="t01")))
        add("invalid_task_next_id", changed(root=lambda d:d.update(nextId=1)))
        add("invalid_project_next_id", changed(root=lambda d:d.update(nextProjectId=1)))
        add("invalid_boolean_counter", changed(root=lambda d:d.update(nextId=True)))
        add("invalid_fractional_counter", changed(root=lambda d:d.update(nextId=2.5)))
        add("invalid_negative_time", changed(task=lambda t:t.update(updatedAtMs=-1)))
        add("invalid_future_version", changed(root=lambda d:d.update(version=4)))
        add("invalid_missing_tasks", changed(root=lambda d:d.pop("tasks")))
        add("invalid_priority", changed(task=lambda t:t.update(priority="no")))
        add("invalid_completed_string", changed(task=lambda t:t.update(done="false")))
        add("invalid_duplicate_task_ids", changed(root=lambda d:(
            d.update(nextId=3), d["tasks"].append(copy.deepcopy(d["tasks"][0])))))
        add("invalid_duplicate_project_names", changed(root=lambda d:(
            d.update(nextProjectId=3),
            d["projects"].append({
                "id":"p2","name":"EXAMPLE PROJECT",
                "createdAtMs":900,"updatedAtMs":900
            }))))
        add("invalid_over_capacity", changed(root=lambda d:(
            d.update(nextId=203), d.update(tasks=[
                {"id":"t"+str(i+1),"title":"Test","done":False,
                 "createdAtMs":1,"updatedAtMs":1,"priority":"none",
                 "description":"","dueDate":None,"projectId":None}
                for i in range(201)
            ]))))
        add("valid_extra_unrecognized_fields", changed(
            root=lambda d:d.update(extraSafeData="not persisted by JS clone"),
            task=lambda t:t.update(extraTaskData="not persisted")))
        add("invalid_raw_json", "{oops")
        add("invalid_empty_raw", "")
        add("invalid_nonstandard_nan", encode(baseline())[:-1]+',"unused":NaN}')
        add("invalid_nonstandard_inf", encode(baseline())[:-1]+',"unused":Infinity}')
        add("invalid_nonstandard_negative_inf",
            encode(baseline())[:-1]+',"unused":-Infinity}')
        add("invalid_nonstandard_nan_timestamp",
            encode(baseline()).replace('"updatedAtMs":1000',
                                       '"updatedAtMs":NaN', 1))

        # Non-multiline JavaScript end anchors reject terminal line breaks,
        # exactly as Python fullmatch does. These MUST NOT be marked as
        # deliberate host-only rejections.
        add("invalid_task_id_trailing_lf",
            changed(1, task=lambda t:t.update(id="t1\n")))
        add("invalid_project_id_trailing_lf",
            changed(root=lambda d:(
                d["projects"][0].update(id="p1\n"),
                d["tasks"][0].update(projectId="p1\n")
            )))
        add("invalid_due_date_trailing_lf",
            changed(task=lambda t:t.update(dueDate="2026-10-26\n")))

        # Production JSON.parse last-key-wins; OS-host refuses duplicate keys.
        add("host_stricter_duplicate_json_keys",
            encode(baseline()).replace('"version":3',
                                       '"version":3,"version":3', 1),
            strict=True)

        raw_items = [text for _, text in cases]
        oracle = subprocess.run(
            ["node", str(ORACLE)], input=json.dumps(raw_items),
            cwd=ROOT, encoding="utf-8", capture_output=True,
            check=True, timeout=15
        )
        js = json.loads(oracle.stdout)
        self.assertEqual(len(js), len(cases))
        observed_strict = set()
        for (label, raw), actual in zip(cases, js):
            try:
                host.parse_task_document(raw.encode("utf-8"))
                owner_ok = True
            except host.GateError:
                owner_ok = False
            self.assertFalse(owner_ok and not actual["ok"],
                             f"UNSAFE OWNER FALSE ACCEPT: {label} ({actual})")
            if actual["ok"] and not owner_ok:
                self.assertIn(label, strict_allowlist,
                              f"UNEXPECTED PARITY DIVERGENCE: {label}")
                observed_strict.add(label)
            elif label in strict_allowlist:
                self.fail(f"Expected explicit strict-only discrepancy not present: {label}")
            else:
                self.assertEqual(owner_ok, actual["ok"], label)
        self.assertEqual(observed_strict, strict_allowlist)
        print(f"M11o JS/Python parity: {len(cases)} cases, "
              f"{len(strict_allowlist)} explicitly strict-only denials; "
              "no Python-only acceptance")


def write_private(path, content):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


class RecoveryFailureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name) / "m11l-tasks-copy"
        self.folder.mkdir(mode=0o700)
        self.source = self.folder / "todo-copy.json"
        self.original = encode(baseline()).encode("utf-8")
        write_private(self.source, self.original)
        self.writer = "m11o-disposable-owner-0001"

    def tearDown(self):
        self.temp.cleanup()

    def owner(self, bootstrap=False):
        return host.CandidateOwner(self.folder, self.writer, bootstrap=bootstrap)

    def assertDenied(self, reason, callback):
        with self.assertRaises(host.GateError) as ctx:
            callback()
        self.assertEqual(str(ctx.exception), reason)

    def test_malformed_source_never_bootstraps_or_backs_up(self):
        self.source.unlink()
        invalid = encode(baseline())[:-1] + ',"extra":NaN}'
        write_private(self.source, invalid.encode())
        self.assertDenied("INVALID_JSON_DOCUMENT",
                          lambda:self.owner(bootstrap=True))
        self.assertFalse((self.folder / "gate-review.db").exists())
        self.assertFalse((self.folder / "source-before-gate.bak").exists())

    def test_nonregular_source_and_overlarge_source_fail_closed(self):
        other = self.folder / "other.json"
        write_private(other, self.original)
        self.source.unlink()
        self.source.symlink_to(other)
        self.assertDenied("UNSAFE_FILE_IDENTITY",
                          lambda:self.owner(bootstrap=True))
        self.source.unlink()
        write_private(self.source, b"x" * (host.MAX_BYTES + 1))
        self.assertDenied("INVALID_SOURCE_SIZE",
                          lambda:self.owner(bootstrap=True))

    def test_hardlinked_and_overpermissive_source_refused(self):
        sibling = self.folder / "unexpected-hardlink.json"
        os.link(self.source, sibling)
        self.assertDenied("UNSAFE_FILE_IDENTITY",
                          lambda:self.owner(bootstrap=True))
        sibling.unlink()
        self.source.chmod(0o644)
        self.assertDenied("UNSAFE_FILE_IDENTITY",
                          lambda:self.owner(bootstrap=True))

    def test_stale_reopen_requires_recovery_with_external_change(self):
        with self.owner(bootstrap=True) as old:
            self.assertEqual(old.state()["phase"], "JSON_ACTIVE")
        self.source.unlink()
        changed_source = encode(changed_document()).encode()
        write_private(self.source, changed_source)
        with self.owner() as fresh:
            self.assertEqual(fresh.state()["phase"], "RECOVERY_REVIEW")
            self.assertFalse(fresh.state()["pending"])
            self.assertDenied(
                "STAGE_NOT_ADMISSIBLE",
                lambda:fresh.reserve("m11o-after-reopen-01", self.original)
            )
        self.assertEqual(self.source.read_bytes(), changed_source)

    def test_unknown_journal_version_denied_without_source_write(self):
        with self.owner(bootstrap=True):
            pass
        db = self.folder / "gate-review.db"
        with sqlite3.connect(db) as con:
            con.execute("PRAGMA user_version=999")
            con.commit()
        self.assertDenied("UNKNOWN_JOURNAL_SCHEMA", lambda:self.owner())
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_pending_mismatch_survives_owner_exit(self):
        expected = changed_document()
        with self.owner(bootstrap=True) as current:
            current.reserve("m11o-pending-review-01", encode(expected).encode())
            self.assertDenied("READBACK_MISMATCH",
                              lambda:current.verify("m11o-pending-review-01", 0))
            self.assertTrue(current.state()["pending"])
        with self.owner() as later:
            self.assertEqual(later.state()["phase"], "RECOVERY_REVIEW")
            self.assertTrue(later.state()["pending"])
            self.assertDenied("STAGE_NOT_ADMISSIBLE",
                              lambda:later.reserve("m11o-pending-review-02",
                                                   encode(expected).encode()))
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_test_host_remains_unmounted(self):
        store = (ROOT / "services/hub/ApolloHubTodoStore.qml").read_text()
        shell = (ROOT / "shell.qml").read_text()
        self.assertIn("readonly property bool guardedWriterEnabled: false",store)
        self.assertEqual(store.count("FileView {"), 1)
        self.assertEqual(store.count("todoFile.setText("), 1)
        self.assertNotIn("TaskJsonGateTransportM11m", store + shell)
        self.assertNotIn("TaskJsonGateCandidateM11l", store + shell)


def changed_document():
    doc = baseline()
    doc["tasks"][0]["title"] = "Pending"
    return doc


if __name__ == "__main__":
    unittest.main(verbosity=2)
