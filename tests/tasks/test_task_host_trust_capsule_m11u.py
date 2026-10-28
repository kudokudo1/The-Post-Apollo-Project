#!/usr/bin/env python3
"""M11u private synthetic script-identity, replacement and seal regressions.

All writes target TemporaryDirectory fixtures. No real TASKS data or local UI.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import importlib.util
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tests/tasks/fixtures/TaskHostTrustCapsuleM11u.py"
spec = importlib.util.spec_from_file_location("m11u_capsule_test", SOURCE)
capsule = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = capsule
spec.loader.exec_module(capsule)

GOOD = b'# M11U SYNTHETIC HOST ONLY\nprint("M11U_SYNTHETIC_OK")\n'
BAD_REPLY = b'# M11U SYNTHETIC HOST ONLY\nprint("UNEXPECTED_OUTPUT")\n'


class HostTrustCapsuleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name) / "m11u-host-copy"
        self.folder.mkdir(mode=0o700)
        self.source = self.folder / "synthetic-host.py"
        self.put(GOOD)

    def tearDown(self):
        self.temp.cleanup()

    def put(self, data):
        self.source.write_bytes(data)
        self.source.chmod(0o600)

    def digest(self, raw=GOOD):
        return hashlib.sha256(raw).hexdigest()

    def snapshot(self, sha=None):
        return capsule.capture_synthetic_script(
            self.folder, self.digest() if sha is None else sha)

    def test_verified_private_source_executes_sealed_synthetic_only(self):
        snap = self.snapshot()
        self.assertEqual(snap.sha256, self.digest())
        self.assertEqual(capsule.run_sealed_synthetic(snap),
                         "SYNTHETIC_CAPSULE_OK")
        self.assertEqual(self.source.read_bytes(), GOOD)
        self.assertEqual(self.source.stat().st_mode & 0o777, 0o600)

    def test_source_replaced_after_capture_does_not_change_sealed_execution(self):
        snap = self.snapshot()
        staging = self.folder / "replacement.py"
        staging.write_bytes(BAD_REPLY)
        staging.chmod(0o600)
        os.replace(staging, self.source)
        self.assertEqual(self.source.read_bytes(), BAD_REPLY)
        with self.assertRaisesRegex(capsule.TrustRefusal,
                                    "PINNED_CONTENT_MISMATCH"):
            self.snapshot()
        # Execution consumes captured and sealed bytes, never the replaced path.
        self.assertEqual(capsule.run_sealed_synthetic(snap),
                         "SYNTHETIC_CAPSULE_OK")

    def test_untrusted_digest_and_synthetic_marker_fail_closed(self):
        with self.assertRaisesRegex(capsule.TrustRefusal,
                                    "PINNED_CONTENT_MISMATCH"):
            self.snapshot("0" * 64)
        with self.assertRaisesRegex(capsule.TrustRefusal,
                                    "PINNED_DIGEST_REQUIRED"):
            self.snapshot("not-a-digest")
        unmarked = b'print("M11U_SYNTHETIC_OK")\n'
        self.put(unmarked)
        with self.assertRaisesRegex(capsule.TrustRefusal,
                                    "NOT_A_SYNTHETIC_SCRIPT"):
            self.snapshot(self.digest(unmarked))

    def test_symlink_leaf_and_directory_denied(self):
        linked_target = Path(self.temp.name) / "elsewhere.py"
        linked_target.write_bytes(GOOD)
        linked_target.chmod(0o600)
        self.source.unlink()
        self.source.symlink_to(linked_target)
        with self.assertRaises(capsule.TrustRefusal):
            self.snapshot()
        self.source.unlink()
        self.put(GOOD)
        moved = Path(self.temp.name) / "actual-private"
        self.folder.rename(moved)
        self.folder.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(capsule.TrustRefusal):
            self.snapshot()

    def test_hardlink_and_excess_permissions_denied(self):
        another = self.folder / "other.py"
        os.link(self.source, another)
        with self.assertRaisesRegex(capsule.TrustRefusal,
                                    "PRIVATE_SYNTHETIC_FILE_REQUIRED"):
            self.snapshot()
        another.unlink()
        self.source.chmod(0o644)
        with self.assertRaisesRegex(capsule.TrustRefusal,
                                    "PRIVATE_SYNTHETIC_FILE_REQUIRED"):
            self.snapshot()
        self.source.chmod(0o600)
        self.folder.chmod(0o755)
        with self.assertRaisesRegex(capsule.TrustRefusal,
                                    "PRIVATE_DIRECTORY_REQUIRED"):
            self.snapshot()
        self.folder.chmod(0o700)

    def test_missing_source_wrong_folder_and_oversize_denied(self):
        with self.assertRaisesRegex(capsule.TrustRefusal,
                                    "SYNTHETIC_DIRECTORY_REQUIRED"):
            capsule.capture_synthetic_script(Path(self.temp.name),
                                            self.digest())
        self.source.unlink()
        with self.assertRaises(capsule.TrustRefusal):
            self.snapshot()
        too_large = b"# M11U SYNTHETIC HOST ONLY\n" + b"x" * 65536
        self.put(too_large)
        with self.assertRaisesRegex(capsule.TrustRefusal,
                                    "PRIVATE_SYNTHETIC_FILE_REQUIRED"):
            self.snapshot(self.digest(too_large))

    def test_stdout_is_not_host_authentication(self):
        self.put(BAD_REPLY)
        snap = self.snapshot(self.digest(BAD_REPLY))
        with self.assertRaisesRegex(capsule.TrustRefusal,
                                    "SYNTHETIC_HOST_REFUSED"):
            capsule.run_sealed_synthetic(snap)
        # Even a matching marker does not authenticate interpreter/host identity.

    def test_path_and_python_env_poisoning_do_not_select_a_shell_command(self):
        fake_bin = Path(self.temp.name) / "fake-bin"
        fake_bin.mkdir(mode=0o700)
        fake_python = fake_bin / "python3"
        fake_python.write_text("#!/bin/sh\nexit 99\n")
        fake_python.chmod(0o700)
        with patch.dict(os.environ, {"PATH": str(fake_bin),
                                     "PYTHONPATH": str(fake_bin),
                                     "PYTHONHOME": str(fake_bin)}):
            self.assertEqual(capsule.run_sealed_synthetic(self.snapshot()),
                             "SYNTHETIC_CAPSULE_OK")

    def test_snapshots_cannot_be_modified_silently(self):
        snap = self.snapshot()
        with self.assertRaisesRegex(capsule.TrustRefusal,
                                    "INVALID_PINNED_SNAPSHOT"):
            capsule.run_sealed_synthetic(
                replace(snap, script=BAD_REPLY))

    def test_no_production_entrypoint_or_real_data_path(self):
        text = SOURCE.read_text(encoding="utf-8")
        store = (ROOT / "services/hub/ApolloHubTodoStore.qml").read_text()
        shell = (ROOT / "shell.qml").read_text()
        for forbidden in ("apollo-hub-todo-v1.json", "Quickshell.dataDir",
                          "TaskJsonGateCandidateM11l", "TaskJsonGateTransportM11m",
                          "TaskJsonGateHostBridgeM11m"):
            self.assertNotIn(forbidden, text)
        self.assertIn("readonly property bool guardedWriterEnabled: false",
                      store)
        self.assertNotIn("TaskHostTrustCapsuleM11u", store + shell)
        self.assertEqual(store.count("FileView {"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
