#!/usr/bin/env python3
"""M15a: real filesystem tests, disposable TASKS-shaped data only."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / "services/hub/TaskLocalSourceInspectM15a.py"
_spec = importlib.util.spec_from_file_location("m15a_source_reader", HOST)
subject = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(subject)
FALSE_KEYS = [
    "writerAuthenticated", "savedAcknowledged", "sourceRevisionVerified",
    "encryptedDraftRecoveryEnabled", "writeAuthorized",
    "restoreAuthorized", "draftClearAuthorized", "keyReleaseAuthorized"
]


def json_doc(version=3, title="SYNTHETIC_PRIVATE_NOTE_DO_NOT_LEAK"):
    task = {"id": "t1", "title": title, "done": False,
            "createdAtMs": 1700000000000, "updatedAtMs": 1700000000000}
    if version >= 2:
        task.update({"priority": "none", "description": "PRIVATE_DRAFT_CONTENT",
                     "dueDate": None})
    if version >= 3:
        task["projectId"] = None
    doc = {"version": version, "nextId": 2, "tasks": [task]}
    if version == 3:
        doc.update({"nextProjectId": 1, "projects": []})
    return doc


class LocalSourceInspectM15aTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="m15a-real-file-")
        self.root = Path(self.tmp.name)
        self.folder = self.root / "quickshell"
        self.folder.mkdir(mode=0o700)
        self.source = self.folder / "apollo-hub-todo-v1.json"

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, content: bytes, mode=0o600):
        self.source.write_bytes(content)
        self.source.chmod(mode)

    def encoded(self, doc):
        return (json.dumps(doc, separators=(",", ":")) + "\n").encode("utf-8")

    def inspect(self, expected):
        data = subject.check(self.source)
        self.assertEqual(data["status"], expected, data)
        self.assertEqual(data["protocol"], 1)
        self.assertEqual(data["kind"], "TASKS_LOCAL_SOURCE_CHECK_M15A")
        self.assertIs(data["readOnly"], True)
        for field in FALSE_KEYS:
            self.assertIs(data[field], False, field)
        text = json.dumps(data)
        for secret in ("SYNTHETIC_PRIVATE_NOTE_DO_NOT_LEAK",
                       "PRIVATE_DRAFT_CONTENT", self.tmp.name,
                       "sourcePath", "taskId", "sourceHash"):
            self.assertNotIn(secret, text)
        return data

    def test_real_json_structural_check_and_no_mutation(self):
        self.write(self.encoded(json_doc()))
        before = self.source.read_bytes()
        before_stat = self.source.stat()
        old_listing = sorted(self.folder.iterdir())
        result = self.inspect("SOURCE_STRUCTURALLY_READABLE")
        self.assertTrue(result["sourcePresent"])
        self.assertEqual(result["taskCount"], 1)
        self.assertEqual(result["projectCount"], 0)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(self.source.stat().st_ino, before_stat.st_ino)
        self.assertEqual(self.source.stat().st_mtime_ns, before_stat.st_mtime_ns)
        self.assertEqual(sorted(self.folder.iterdir()), old_listing)

    def test_previous_v1_v2_read_without_mutation_or_migration(self):
        for version in (1, 2):
            with self.subTest(version=version):
                self.write(self.encoded(json_doc(version)))
                result = self.inspect("SOURCE_STRUCTURALLY_READABLE")
                self.assertEqual(result["projectCount"], 0)
                self.assertEqual(json.loads(self.source.read_text())["version"],
                                 version)

    def test_missing_source_never_bootstraps_or_creates(self):
        result = self.inspect("SOURCE_MISSING")
        self.assertFalse(result["sourcePresent"])
        self.assertIsNone(result["taskCount"])
        self.assertFalse(self.source.exists())
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_unsafe_source_symlink_and_hardlink_are_not_followed(self):
        secret = self.folder / "private-dont-read.txt"
        secret.write_text("PRIVATE_DRAFT_CONTENT", encoding="utf-8")
        secret.chmod(0o600)
        self.source.symlink_to(secret)
        self.inspect("SOURCE_UNSAFE")
        self.assertEqual(secret.read_text(), "PRIVATE_DRAFT_CONTENT")
        self.source.unlink()
        os.link(secret, self.source)
        self.inspect("SOURCE_UNSAFE")
        self.assertEqual(self.source.stat().st_nlink, 2)

    def test_nonprivate_source_is_flagged_without_opening_or_fixing(self):
        self.write(self.encoded(json_doc()), mode=0o644)
        before = self.source.read_bytes()
        r = self.inspect("SOURCE_PERMISSION_REVIEW")
        self.assertTrue(r["sourcePresent"])
        self.assertIsNone(r["taskCount"])
        self.assertEqual(self.source.stat().st_mode & 0o777, 0o644)
        self.assertEqual(self.source.read_bytes(), before)

    def test_invalid_json_utf8_duplicate_keys_and_nonfinite(self):
        for data in (b"{bad", b"\xff\xfe", b'{"version":3,"version":3}',
                     b'{"version":NaN}'):
            with self.subTest(data=data):
                self.write(data)
                self.inspect("SOURCE_INVALID_JSON")

    def test_invalid_structure_and_future_version_are_not_repaired(self):
        for doc, code in [
            (json_doc(4), "SOURCE_UNSUPPORTED_VERSION"),
            ({"version": 3, "nextId": 1, "projects": [],
              "nextProjectId": 1, "tasks": "bad"}, "SOURCE_INVALID_STRUCTURE"),
            ({"version": 3, "nextId": 1, "projects": [],
              "nextProjectId": 1, "tasks": [{"id": "t1", "title": "a",
                                              "done": False},
                                             {"id": "t1", "title": "b",
                                              "done": True}]},
             "SOURCE_INVALID_STRUCTURE"),
        ]:
            with self.subTest(code=code):
                self.write(self.encoded(doc))
                before = self.source.read_bytes()
                self.inspect(code)
                self.assertEqual(self.source.read_bytes(), before)

    def test_oversized_source_and_empty_source(self):
        self.write(b"x" * (subject.MAX_BYTES+1))
        self.inspect("SOURCE_TOO_LARGE")
        self.write(b"")
        self.inspect("SOURCE_TOO_LARGE")

    def test_path_refuses_other_names_or_relative_and_symlink_parent(self):
        for path in (self.folder/"other.json",
                     Path("apollo-hub-todo-v1.json"),
                     self.folder/".."/"quickshell"/subject.FILENAME):
            self.assertEqual(subject.check(path)["status"],
                             "SOURCE_PATH_REFUSED", str(path))
        bad_parent = self.root/"linked-data"
        bad_parent.symlink_to(self.folder, target_is_directory=True)
        target=bad_parent/subject.FILENAME
        self.assertEqual(subject.check(target)["status"], "SOURCE_UNSAFE")

    def test_fenced_read_detects_replacement_during_open(self):
        self.write(self.encoded(json_doc()))
        prior_read = subject.os.read
        called = [0]

        def mutate(fd, n):
            result = prior_read(fd, n)
            if not called[0]:
                called[0] += 1
                # New inode at same source pathname during inspection.
                temp = self.folder / ".replace"
                temp.write_bytes(self.encoded(json_doc(title="CHANGED_SYNTHETIC")))
                temp.chmod(0o600)
                os.replace(temp, self.source)
            return result

        with patch.object(subject.os, "read", side_effect=mutate):
            self.inspect("SOURCE_CHANGED")

    def test_cli_real_process_no_path_or_task_contents_in_stdout(self):
        self.write(self.encoded(json_doc()))
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(HOST), "--source", str(self.source)],
            capture_output=True, text=True, timeout=8)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 1)
        payload = json.loads(lines[0])
        self.assertEqual(payload["status"], "SOURCE_STRUCTURALLY_READABLE")
        self.assertEqual(payload["taskCount"], 1)
        self.assertEqual(payload["projectCount"], 0)
        for forbidden in (self.tmp.name, "PRIVATE_DRAFT_CONTENT",
                          "SYNTHETIC_PRIVATE_NOTE_DO_NOT_LEAK"):
            self.assertNotIn(forbidden, result.stdout)
            self.assertNotIn(forbidden, result.stderr)

    def test_no_import_of_writer_or_credential_store(self):
        code = HOST.read_text()
        for illegal in [
            "os.replace(", "os.rename(", "os.unlink(", "os.remove(",
            "os.chmod(", "os.chown(", "open(source, 'w'",
            "secret-tool", "keyring", "ConnectionsBroker", "TaskEncryptedDraft",
            "apollo-hub-todo-v1.json.tmp", "subprocess.Popen"
        ]:
            self.assertNotIn(illegal, code)


if __name__ == "__main__":
    unittest.main()
