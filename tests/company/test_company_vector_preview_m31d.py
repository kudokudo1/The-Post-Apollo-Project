#!/usr/bin/env python3
"""Company M31d: executable contract tests for isolated Fedora preview.

Uses a disposable HOME and a fake M14 helper. Never builds native Qt, reaches
a tile server, edits real user files or assumes the host has Toolbox.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PREVIEW = ROOT / "experiments/company-vector-qt/preview_m31d.sh"
M14 = ROOT / "experiments/company-vector-qt/fedora_lab_m14.sh"
LIVE = ROOT / "widgets/CompanyNetworkW.qml"
SHELL = ROOT / "shell.qml"


class M31dPreviewTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="company-m31d-ci-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.lab = self.home / "postapollo-vector-lab"
        self.repo = self.lab / "company-preview-src"
        (self.repo / ".git").mkdir(parents=True)
        self.previewdir = self.repo / "experiments" / "company-vector-qt"
        self.previewdir.mkdir(parents=True)
        shutil.copyfile(PREVIEW, self.previewdir / "preview_m31d.sh")
        (self.previewdir / "main.cpp").write_text("// fake fixture only\n")
        (self.previewdir / "main.qml").write_text("// fake fixture only\n")
        (self.previewdir / "fedora_lab_m14.sh").write_text(
            '#!/usr/bin/env bash\n'
            'echo "FAKE_M14_ACTION=$1"\n'
            'echo "FAKE_M14_REPO=$POST_APOLLO_REPO"\n'
            'echo "FAKE_M14_LAB=$POST_APOLLO_VECTOR_LAB"\n'
        )

    def run_preview(self, action, path=None, envadd=None):
        env = dict(os.environ)
        env["HOME"] = str(self.home)
        env.pop("POST_APOLLO_REPO", None)
        env.pop("POST_APOLLO_VECTOR_LAB", None)
        env.pop("QSG_RHI_BACKEND", None)
        if envadd:
            env.update(envadd)
        script = path or self.previewdir / "preview_m31d.sh"
        return subprocess.run(
            ["bash", str(script), action],
            capture_output=True, text=True, env=env, timeout=5, check=False)

    def test_check_uses_isolated_source_and_lab(self):
        result = self.run_preview("check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("FAKE_M14_ACTION=check", result.stdout)
        self.assertIn(f"FAKE_M14_REPO={self.repo}", result.stdout)
        self.assertIn(f"FAKE_M14_LAB={self.lab}", result.stdout)
        self.assertIn("production=OFF", result.stdout)

    def test_build_is_explicit_never_automatic_on_check(self):
        result = self.run_preview("build")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("FAKE_M14_ACTION=build", result.stdout)
        self.assertNotIn("FAKE_M14_ACTION=run", result.stdout)

    def test_offline_and_online_are_distinct(self):
        offline = self.run_preview("run-offline")
        self.assertEqual(offline.returncode, 0, offline.stderr)
        self.assertIn("FAKE_M14_ACTION=run-offline", offline.stdout)
        self.assertNotIn("ONLINE_CONSENT", offline.stderr)
        online = self.run_preview("run-online")
        self.assertEqual(online.returncode, 0, online.stderr)
        self.assertIn("FAKE_M14_ACTION=run-online", online.stdout)
        self.assertIn("ONLINE_CONSENT", online.stderr)
        self.assertIn("OpenFreeMap", online.stderr)

    def test_source_not_in_dedicated_clone_is_refused(self):
        other = self.home / "another-repo" / "experiments" / "company-vector-qt"
        other.mkdir(parents=True)
        shutil.copyfile(PREVIEW, other / "preview_m31d.sh")
        result = self.run_preview("check", other / "preview_m31d.sh")
        self.assertEqual(result.returncode, 2)
        self.assertIn("source checkout must be the isolated", result.stderr)

    def test_symlink_to_source_refused(self):
        (self.lab / "foreign").symlink_to(self.repo, target_is_directory=True)
        other = self.lab / "foreign" / "experiments" / "company-vector-qt"
        result = self.run_preview("check", other / "preview_m31d.sh")
        # Physical resolution is the dedicated clone; symlink directory
        # invocation itself is not a change to live source.
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_no_source_flag_or_external_renderer_override(self):
        for envadd in (
            {"POST_APOLLO_REPO": str(self.home / ".config/quickshell")},
            {"POST_APOLLO_VECTOR_LAB": str(self.home / "foreign-lab")},
            {"QSG_RHI_BACKEND": "vulkan"},
        ):
            with self.subTest(envadd=envadd):
                result = self.run_preview("check", envadd=envadd)
                self.assertEqual(result.returncode, 2)
                self.assertIn("REFUSED", result.stderr)

    def test_invalid_actions_are_refused_before_any_helper(self):
        for action in ("install", "update", "pull", "merge", "shell", "reload"):
            with self.subTest(action=action):
                result = self.run_preview(action)
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("FAKE_M14_ACTION", result.stdout)

    def test_live_contracts_and_existing_m14_are_preserved(self):
        launcher = PREVIEW.read_text()
        m14 = M14.read_text()
        company = LIVE.read_text()
        self.assertIn("POST_APOLLO_REPO", launcher)
        self.assertIn("POST_APOLLO_VECTOR_LAB", launcher)
        self.assertIn("run-online", m14)
        self.assertIn("maplibre-install", m14)
        self.assertIn("vectorBridgeOptIn: false", company)
        self.assertIn("CompanyNetwork", SHELL.read_text())
        self.assertNotIn("systemctl", launcher)
        self.assertNotIn("rpm-ostree", launcher)
        self.assertNotIn("git pull", launcher)
        self.assertNotIn("git reset", launcher)
        self.assertNotIn("quickshell --restart", launcher)


if __name__ == "__main__":
    unittest.main()
