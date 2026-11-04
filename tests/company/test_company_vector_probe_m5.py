"""M5 contracts: standalone vector renderer, offline default, authority boundaries."""
from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "experiments/company-vector-qt"


class VectorProbeContracts(unittest.TestCase):
    def test_v3_qt_quick_integration(self):
        cmake = (PROBE / "CMakeLists.txt").read_text()
        cpp = (PROBE / "main.cpp").read_text()
        qml = (PROBE / "main.qml").read_text()
        self.assertIn("find_package(Qt6 6.5 REQUIRED", cmake)
        self.assertIn("find_package(QMapLibre 3.0 REQUIRED COMPONENTS Location)", cmake)
        self.assertIn("qmaplibre_location_setup_plugins(company-vector-probe)", cmake)
        self.assertIn("QMapLibre::Location", cmake)
        self.assertIn("QSGRendererInterface::OpenGLRhi", cpp)
        self.assertIn("QQuickWindow::setGraphicsApi", cpp)
        self.assertIn("import QtLocation 6.5", qml)
        self.assertIn("import QtPositioning 6.5", qml)
        self.assertIn("import MapLibre 3.0", qml)
        self.assertIn('name: "maplibre"', qml)
        self.assertIn('name: "maplibre.map.styles"', qml)
        self.assertIn("MapView {", qml)

    def test_offline_default_only_explicit_online_opt_in(self):
        cpp = (PROBE / "main.cpp").read_text()
        self.assertIn('args.contains("--online")', cpp)
        self.assertIn('args.contains("--capture")', cpp)
        self.assertIn("QUrl::fromLocalFile(localPath)", cpp)
        self.assertIn('QStringLiteral("https://tiles.openfreemap.org/styles/liberty")', cpp)
        self.assertIn('setContextProperty("probeOnline", online)', cpp)
        self.assertIn("engine.rootObjects().isEmpty()", cpp)
        self.assertIn("window->grabWindow()", cpp)
        fixture = json.loads((PROBE / "style-fixture.json").read_text())
        self.assertNotIn("http", json.dumps(fixture).lower())
        self.assertNotIn("glyphs", fixture)
        self.assertNotIn("sprite", fixture)

    def test_fixture_synthetic_with_postapollo_layers(self):
        fixture = json.loads((PROBE / "style-fixture.json").read_text())
        self.assertEqual(fixture["version"], 8)
        self.assertTrue(fixture["metadata"]["not-real-streets"])
        self.assertTrue(fixture["metadata"]["post-apollo-fixture"])
        self.assertEqual(set(fixture["sources"]), {"probe-features"})
        self.assertEqual(fixture["sources"]["probe-features"]["type"], "geojson")
        self.assertGreaterEqual(len(fixture["sources"]["probe-features"]["data"]["features"]), 4)
        self.assertIn("line", {layer["type"] for layer in fixture["layers"]})
        self.assertIn("fill", {layer["type"] for layer in fixture["layers"]})
        self.assertEqual(fixture["layers"][0]["paint"]["background-color"], "#1B0623")
        qml = (PROBE / "main.qml").read_text()
        self.assertIn("SYNTHETIC VECTOR GEOMETRY", qml)
        self.assertIn("NOT REAL STREETS OR COMPANY COVERAGE", qml)
        self.assertIn("© OpenStreetMap contributors", qml)

    def test_no_live_shell_hook_or_credentials(self):
        shell = (ROOT / "shell.qml").read_text()
        company = (ROOT / "widgets/CompanyCoveragePane.qml").read_text()
        self.assertNotIn("company-vector-probe", shell)
        self.assertNotIn("company-vector-probe", company)
        qml = (PROBE / "main.qml").read_text()
        for forbidden in ("CompanyHubStore", "SocialIdentity", "QtWebEngine",
                          "clientName", "employeeId", "maps.googleapis.com"):
            self.assertNotIn(forbidden, qml)

    def test_preflight_is_read_only(self):
        preflight = (PROBE / "probe_environment.py").read_text()
        for forbidden in ("pip install", "dnf install", "rm -rf", "systemctl restart",
                          "quickshell --restart", "subprocess.Popen", "write_text(",
                          "mkdir(", "os.unlink(", "shutil.rmtree("):
            self.assertNotIn(forbidden, preflight)
        self.assertIn("shutil.which", preflight)
        self.assertIn("pkg-config", preflight)


if __name__ == "__main__":
    unittest.main()
