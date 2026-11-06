"""M16 QtLocation-only bundle: fail-closed source, staging, rollback and bridge."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "experiments" / "company-vector-qt"


def import_file(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bundle = import_file("company_m16_bundle", "CompanyQtLocationBundleM16.py")
bridge = import_file("company_m16_bridge", "CompanyVectorHostBridge.py")


class BundleM16Tests(unittest.TestCase):
    def setUp(self):
        if os.getuid() == 0:
            self.skipTest("Must run unprivileged, as in GitHub CI.")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.source = self.home / "fake-location.so"
        self.source.write_bytes(bytes.fromhex("7f454c46") + b"test-only-QtLocation-binary")

    def lab(self):
        p = self.home / "postapollo-vector-lab"
        p.mkdir(exist_ok=True)
        return p

    def stage(self):
        self.lab()
        with patch.object(bundle, "verified_source", return_value=True):
            return bundle.operation("stage", self.home, self.source)

    def test_missing_bundle_check_is_read_only(self):
        self.assertEqual(bundle.operation("check", self.home)["status"], "NOT_STAGED")
        self.assertEqual(sorted(p.name for p in self.home.iterdir()), ["fake-location.so"])

    def test_missing_lab_refused(self):
        with patch.object(bundle, "verified_source", return_value=True):
            self.assertEqual(bundle.operation("stage", self.home, self.source)["status"], "UNSAFE_LAB")

    def test_source_integrity_required(self):
        self.lab()
        with patch.object(bundle, "verified_source", return_value=False):
            self.assertEqual(bundle.operation("stage", self.home, self.source)["status"], "SOURCE_UNVERIFIED")
        self.assertFalse((self.lab() / "qtlocation-runtime").exists())

    def test_staged_bundle_is_valid_and_explicitly_removable(self):
        self.assertEqual(self.stage()["status"], "STAGED")
        path = bundle.bundle_dir(self.home)
        self.assertTrue(bundle.valid_bundle(self.home))
        self.assertEqual(bundle.operation("check", self.home)["status"], "STAGED")
        self.assertEqual(stat.S_IMODE((path / bundle.LIBRARY).stat().st_mode), 0o600)
        self.assertEqual(bundle.operation("stage", self.home, self.source)["status"], "ALREADY_STAGED")
        self.assertEqual(bundle.operation("remove", self.home)["status"], "REMOVED")
        self.assertFalse(path.exists())
        self.assertTrue(self.lab().exists())

    def test_content_tamper_refuses_removal(self):
        self.stage()
        path = bundle.bundle_dir(self.home) / bundle.LIBRARY
        path.write_bytes(bytes.fromhex("7f454c46") + b"tampered")
        self.assertEqual(bundle.operation("check", self.home)["status"], "UNVERIFIED_BUNDLE")
        self.assertEqual(bundle.operation("remove", self.home)["status"], "REFUSED_UNVERIFIED_BUNDLE")
        self.assertTrue(path.exists())

    def test_extra_file_refuses_removal(self):
        self.stage()
        path = bundle.bundle_dir(self.home)
        (path / "foreign").write_text("keep")
        self.assertEqual(bundle.operation("remove", self.home)["status"], "REFUSED_EXTRA_FILES")
        self.assertTrue((path / "foreign").exists())

    def test_symlink_target_is_never_overwritten(self):
        lab = self.lab()
        outside = self.home / "elsewhere"
        outside.mkdir()
        (lab / "qtlocation-runtime").symlink_to(outside, target_is_directory=True)
        with patch.object(bundle, "verified_source", return_value=True):
            self.assertEqual(bundle.operation("stage", self.home, self.source)["status"], "REFUSED_EXISTING")
        self.assertEqual(list(outside.iterdir()), [])

    def test_unknown_action_refused(self):
        self.assertEqual(bundle.operation("install", self.home)["status"], "INVALID_ACTION")


class HostBridgeM16Tests(unittest.TestCase):
    def setUp(self):
        if os.getuid() == 0:
            self.skipTest("Must run unprivileged.")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        for parts in bridge.LAB_FILES:
            path = self.home.joinpath(*parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(bytes.fromhex("7f454c46") + b"placeholder")
            if parts == bridge.LAB_FILES[0]:
                path.chmod(0o700)
        runtime = self.home.joinpath(*bridge.BUNDLE_PARTS)
        runtime.parent.mkdir(parents=True, exist_ok=True)
        runtime.write_bytes(bytes.fromhex("7f454c46") + b"bundled-example")
        runtime.chmod(0o600)
        manifest = self.home.joinpath(*bridge.MANIFEST_PARTS)
        manifest.write_text(json.dumps({
            "schema": bridge.BUNDLE_SCHEMA,
            "version": bridge.EXPECTED_QT_VERSION,
            "sha256": hashlib.sha256(runtime.read_bytes()).hexdigest()
        }))
        manifest.chmod(0o600)

    def test_bridge_verifies_bundle_and_detects_tamper(self):
        self.assertTrue(bridge._bundle_valid(self.home))
        self.home.joinpath(*bridge.BUNDLE_PARTS).write_bytes(b"wrong")
        self.assertFalse(bridge._bundle_valid(self.home))

    def test_bundle_directory_precedes_maplibre(self):
        env = bridge.runtime_environment(self.home)
        value = env["LD_LIBRARY_PATH"]
        self.assertEqual(value.split(":")[0], str(self.home.joinpath(*bridge.BUNDLE_PARTS[:-1])))
        self.assertEqual(value.split(":")[1], str(self.home / "postapollo-vector-lab/maplibre-install/lib64"))

    def test_probe_refuses_bundle_tamper(self):
        self.home.joinpath(*bridge.BUNDLE_PARTS).write_bytes(b"wrong")
        with patch.object(bridge, "_check_host_qt", return_value=True):
            self.assertEqual(bridge.probe(self.home)["status"], "QTLOCATION_BUNDLE_UNVERIFIED")

    def test_runtime_ldd_requires_bundle_for_all_artifacts(self):
        expected = str(self.home.joinpath(*bridge.BUNDLE_PARTS))
        def result(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0,
                stdout="libQt6Location.so.6 => " + expected + " (0x7f000)\n", stderr="")
        with patch.object(bridge.subprocess, "run", side_effect=result) as fake:
            self.assertTrue(bridge._dependencies_resolved(self.home, bridge.runtime_environment(self.home)))
            self.assertEqual(fake.call_count, 4)

    def test_runtime_ldd_rejects_wrong_library(self):
        result = subprocess.CompletedProcess([], 0,
            stdout="libQt6Location.so.6 => /other/Qt6Location.so (0x7f000)\n", stderr="")
        with patch.object(bridge.subprocess, "run", return_value=result):
            self.assertFalse(bridge._dependencies_resolved(self.home, bridge.runtime_environment(self.home)))

    def test_probe_ready_only_with_all_runtime_checks(self):
        with patch.object(bridge, "_check_host_qt", return_value=True), patch.object(
                bridge, "_dependencies_resolved", return_value=True):
            self.assertEqual(bridge.probe(self.home)["status"], "READY")

    def test_controller_has_bundle_failure_display(self):
        source = (ROOT / "services/company/CompanyVectorSidecarController.qml").read_text()
        self.assertIn("QTLOCATION_BUNDLE_UNVERIFIED", source)
        self.assertIn("QTLOCATION BUNDLE UNVERIFIED", source)


if __name__ == "__main__":
    unittest.main()
