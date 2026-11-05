"""Contract for M14's isolated Fedora build and opt-in launch script."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "experiments/company-vector-qt/fedora_lab_m14.sh"


class FedoraM14Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.lab = self.home / "postapollo-vector-lab"
        self.repo = self.home / "quickshell"
        self.bin = self.home / "bin"
        self.bin.mkdir()
        (self.bin / "pkg-config").write_text("#!/bin/sh\nprintf '6.11.2\\n'\n")
        (self.bin / "pkg-config").chmod(0o755)
        (self.bin / "cmake").write_text("#!/bin/sh\nexit 0\n")
        (self.bin / "cmake").chmod(0o755)
        self.env = {**os.environ, "HOME": str(self.home), "POST_APOLLO_REPO": str(self.repo),
                    "POST_APOLLO_VECTOR_LAB": str(self.lab),
                    "PATH": f"{self.bin}:{os.environ['PATH']}"}

    def run_script(self, action):
        return subprocess.run(["bash", str(SCRIPT), action], env=self.env,
                              text=True, capture_output=True, timeout=5)

    def fixture(self):
        source = self.repo / "experiments/company-vector-qt"
        source.mkdir(parents=True)
        for name in ("CMakeLists.txt", "main.cpp", "main.qml", "style-fixture.json",
                     "style-post-apollo-online.json"):
            (source / name).touch()
        for path in ("lib64/cmake/QMapLibre/QMapLibreConfig.cmake",
                     "lib64/libQMapLibre.so.3.0.0",
                     "lib64/libQMapLibreLocation.so.3.0.0",
                     "qml/MapLibre/qmldir",
                     "plugins/geoservices/libqtgeoservices_maplibre.so"):
            p = self.lab / "maplibre-install" / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.touch()
        build = self.lab / "company-vector-build"
        build.mkdir()
        (build / "company-vector-probe").write_text("#!/bin/sh\nprintf 'PROBE_ARGS %s\\n' \"$*\"\n")
        (build / "company-vector-probe").chmod(0o700)

    def test_missing_install_fails_closed_and_writes_nothing(self):
        result = self.run_script("check")
        self.assertEqual(result.returncode, 2)
        self.assertIn("M14_BLOCKED", result.stderr)
        self.assertFalse(self.lab.exists())
        self.assertFalse(self.repo.exists())

    def test_offline_runs_without_any_online_switch(self):
        self.fixture()
        result = self.run_script("run-offline")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("M14_PREFLIGHT_PASSED", result.stdout)
        self.assertIn("PROBE_ARGS", result.stdout)
        self.assertNotIn("--styled-online", result.stdout)
        self.assertNotIn("M14_ONLINE_CONSENT", result.stderr)

    def test_online_requires_separate_explicit_action(self):
        self.fixture()
        result = self.run_script("run-online")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--styled-online", result.stdout)
        self.assertIn("M14_ONLINE_CONSENT", result.stderr)

    def test_unknown_action_refused(self):
        result = self.run_script("install")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.lab.exists())
        self.assertFalse(self.repo.exists())


if __name__ == "__main__":
    unittest.main()
