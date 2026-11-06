"""M17 QtLocation library + QML plugin staging, integrity and bridge contracts."""
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


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bundle = load("company_qtlocation_bundle_m17", "CompanyQtLocationBundleM16.py")
bridge = load("company_vector_bridge_m17", "CompanyVectorHostBridge.py")
QML_DESC = b"module QtLocation\nplugin declarative_locationplugin\ntypeinfo plugins.qmltypes\n"


class BundleTests(unittest.TestCase):
    def setUp(self):
        if os.getuid() == 0:
            self.skipTest("Non-root runtime and CI only")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.src = self.home / "fake-location.so"
        self.src.write_bytes(bytes.fromhex("7f454c46") + b"synthetic library")
        self.qml = self.home / "fixture-qml"
        self.qml.mkdir()
        (self.qml / bundle.QML_FILES[0]).write_bytes(
            bytes.fromhex("7f454c46") + b"synthetic plugin")
        (self.qml / "MapView.qml").write_text("import QtQuick\nItem {}")
        (self.qml / "plugins.qmltypes").write_text("module FakeQmlTypes {}")
        (self.qml / "qmldir").write_bytes(QML_DESC)

    def lab(self):
        path = self.home / "postapollo-vector-lab"
        path.mkdir(exist_ok=True)
        return path

    def stage(self, allowed=True):
        self.lab()
        with patch.object(bundle, "verified_source", return_value=allowed):
            return bundle.operation("stage", self.home, self.src, self.qml)

    def test_read_only_check_no_bundle(self):
        self.assertEqual(bundle.operation("check", self.home)["status"], "NOT_STAGED")
        self.assertFalse(self.lab().joinpath("qtlocation-runtime").exists())

    def test_source_refusal_does_not_create_bundle(self):
        self.assertEqual(self.stage(False)["status"], "SOURCE_UNVERIFIED")
        self.assertFalse(self.lab().joinpath("qtlocation-runtime").exists())

    def test_stage_checks_all_five_files_and_remove(self):
        self.assertEqual(self.stage()["status"], "STAGED")
        base = self.lab() / "qtlocation-runtime"
        self.assertTrue(bundle.valid_bundle(self.home))
        self.assertEqual(bundle.operation("check", self.home)["status"], "STAGED")
        self.assertEqual(set(p.name for p in (base / "qml" / "QtLocation").iterdir()),
                         set(bundle.QML_FILES))
        self.assertEqual(stat.S_IMODE((base / "lib64" / bundle.LIBRARY).stat().st_mode), 0o600)
        self.assertEqual(bundle.operation("stage", self.home)["status"], "ALREADY_STAGED")
        self.assertEqual(bundle.operation("remove", self.home)["status"], "REMOVED")
        self.assertFalse(base.exists())
        self.assertTrue(self.lab().exists())

    def test_bad_qml_manifest_refused(self):
        self.stage()
        base = self.lab() / "qtlocation-runtime"
        manifest = base / "lib64" / bundle.MANIFEST
        doc = json.loads(manifest.read_text())
        doc["sha256"].pop("qml/QtLocation/MapView.qml")
        manifest.write_text(json.dumps(doc))
        self.assertFalse(bundle.valid_bundle(self.home))
        self.assertEqual(bundle.operation("remove", self.home)["status"], "REFUSED_UNVERIFIED_BUNDLE")

    def test_each_qml_file_tamper_refuses_rollback(self):
        for name in bundle.QML_FILES:
            with self.subTest(name=name):
                self.stage()
                p = self.lab() / "qtlocation-runtime" / "qml" / "QtLocation" / name
                p.write_bytes(p.read_bytes() + b"extra")
                self.assertFalse(bundle.valid_bundle(self.home))
                self.assertEqual(bundle.operation("remove", self.home)["status"], "REFUSED_UNVERIFIED_BUNDLE")
                # Dispose this synthetic test tree; never part of the product path.
                import shutil
                shutil.rmtree(self.lab() / "qtlocation-runtime")

    def test_unexpected_additional_plugin_fails_closed(self):
        self.stage()
        base = self.lab() / "qtlocation-runtime" / "qml" / "QtLocation"
        (base / "evil-plugin.so").write_text("not ours")
        self.assertFalse(bundle.valid_bundle(self.home))
        self.assertEqual(bundle.operation("remove", self.home)["status"], "REFUSED_UNVERIFIED_BUNDLE")
        self.assertTrue((base / "evil-plugin.so").exists())

    def test_symlink_qml_plugin_refused(self):
        self.stage()
        path = self.lab() / "qtlocation-runtime" / "qml" / "QtLocation" / bundle.QML_FILES[0]
        path.unlink()
        path.symlink_to(self.src)
        self.assertFalse(bundle.valid_bundle(self.home))

    def test_old_library_only_manifest_refused(self):
        self.stage()
        manifest = self.lab() / "qtlocation-runtime" / "lib64" / bundle.MANIFEST
        doc = json.loads(manifest.read_text())
        doc["schema"] = "post-apollo.company.qtlocation-runtime.v1"
        manifest.write_text(json.dumps(doc))
        self.assertFalse(bundle.valid_bundle(self.home))

    def test_preexisting_bundle_no_overwrite(self):
        base = self.lab() / "qtlocation-runtime"
        base.mkdir()
        (base / "foreign").write_text("preserve")
        self.assertEqual(self.stage()["status"], "REFUSED_EXISTING")
        self.assertEqual((base / "foreign").read_text(), "preserve")

    def test_missing_qml_source_cleanup(self):
        (self.qml / "MapView.qml").unlink()
        self.assertEqual(self.stage()["status"], "STAGE_FAILED")
        self.assertFalse(self.lab().joinpath("qtlocation-runtime").exists())

    def test_qmldir_requires_declared_plugin(self):
        self.assertTrue(bundle._module_descriptor_valid(QML_DESC))
        self.assertFalse(bundle._module_descriptor_valid(b"module QtLocation\n"))
        self.assertFalse(bundle._module_descriptor_valid(b"module QtLocation\nplugin unrelated\n"))

    def test_unknown_action_refused(self):
        self.assertEqual(bundle.operation("install", self.home)["status"], "INVALID_ACTION")


class BridgeTests(BundleTests):
    def setUp(self):
        super().setUp()
        for parts in bridge.LAB_FILES:
            p = self.home.joinpath(*parts)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(bytes.fromhex("7f454c46") + b"pretend MapLibre")
            if parts == bridge.LAB_FILES[0]:
                p.chmod(0o700)
        self.stage()

    def test_full_bundle_and_qml_import_precedence(self):
        self.assertTrue(bridge._bundle_valid(self.home))
        env = bridge.runtime_environment(self.home)
        self.assertEqual(env["QML_IMPORT_PATH"].split(":")[0],
                         str(self.home / "postapollo-vector-lab/qtlocation-runtime/qml"))
        self.assertEqual(env["QML2_IMPORT_PATH"].split(":")[0],
                         str(self.home / "postapollo-vector-lab/qtlocation-runtime/qml"))
        self.assertEqual(env["LD_LIBRARY_PATH"].split(":")[0],
                         str(self.home / "postapollo-vector-lab/qtlocation-runtime/lib64"))

    def test_bridge_rejects_qml_tampering(self):
        p = self.lab() / "qtlocation-runtime/qml/QtLocation/MapView.qml"
        p.write_text("different data")
        self.assertFalse(bridge._bundle_valid(self.home))
        with patch.object(bridge, "_check_host_qt", return_value=True):
            self.assertEqual(bridge.probe(self.home)["status"], "QTLOCATION_BUNDLE_UNVERIFIED")

    def test_bridge_ldd_checks_plugin_as_well(self):
        bundled = str(self.home.joinpath(*bridge.BUNDLE_PARTS))
        fake = subprocess.CompletedProcess([], 0,
            "libQt6Location.so.6 => " + bundled + " (0x123)\n", "")
        with patch.object(bridge.subprocess, "run", return_value=fake) as mocked:
            self.assertTrue(bridge._dependencies_resolved(
                self.home, bridge.runtime_environment(self.home)))
            self.assertEqual(mocked.call_count, 5)
            self.assertIn(str(self.home.joinpath(*bridge.QML_BUNDLE_PATHS[0])),
                          [call.args[0][1] for call in mocked.call_args_list])

    def test_bridge_rejects_wrong_location_library_resolution(self):
        fake = subprocess.CompletedProcess([], 0,
            "libQt6Location.so.6 => /unrelated/libQt6Location.so.6 (0x123)\n", "")
        with patch.object(bridge.subprocess, "run", return_value=fake):
            self.assertFalse(bridge._dependencies_resolved(
                self.home, bridge.runtime_environment(self.home)))

    def test_full_readiness_requires_runtime_link_checks(self):
        with patch.object(bridge, "_check_host_qt", return_value=True), \
             patch.object(bridge, "_dependencies_resolved", return_value=True):
            self.assertEqual(bridge.probe(self.home)["status"], "READY")


if __name__ == "__main__":
    unittest.main()
