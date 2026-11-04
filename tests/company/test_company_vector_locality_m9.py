"""M9 finer-detail map and synthetic geographic marker source contract tests."""
from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"experiments/company-vector-qt"
QML=(BASE/"main.qml").read_text(encoding="utf-8")
CPP=(BASE/"main.cpp").read_text(encoding="utf-8")
WORKFLOW=(ROOT/".github/workflows/company-network-vector-probe-m5.yml").read_text(encoding="utf-8")

class LocalityMarkerTest(unittest.TestCase):
    def test_sample_places_are_exemplars_not_source_bounds(self):
        for name in ("SUBURB","VILLAGE","NEIGHBORHOOD","BORDER"):
            self.assertIn('label:"'+name+'"',QML)
            self.assertIn('QStringLiteral("'+name+'")',CPP)
        self.assertIn('zoom:16',QML)
        self.assertIn('zoom:15',QML)
        self.assertIn('zoom:14',QML)
        style=json.loads((BASE/"style-post-apollo-online.json").read_text())
        self.assertNotIn("bounds",style["sources"]["openmaptiles"])
        self.assertIn("https://tiles.openfreemap.org/planet",
                      style["sources"]["openmaptiles"]["url"])

    def test_demo_marker_is_map_geographic_item_not_screen_pixel_paint(self):
        self.assertIn("MapQuickItem {",QML)
        self.assertIn("QtPositioning.coordinate(43.655, -79.383)",QML)
        self.assertIn("mapView.map.addMapItem(item)",QML)
        self.assertIn("mapView.map.mapReady",QML)
        self.assertIn('console.log("SYNTHETIC_MARKER_ADDED")',QML)
        self.assertIn("sourceItem: Item {",QML)
        self.assertIn('text: "DEMO HUB"',QML)
        self.assertIn('border.color: "#ED981A"',QML)
        self.assertIn('border.color: "#C74EC7"',QML)
        self.assertIn("if (!probeMockHub",QML)

    def test_marker_is_explicit_opt_in_and_never_real_identity_data(self):
        self.assertIn('args.contains("--mock-hub")',CPP)
        self.assertIn("mockHub && !anyOnline",CPP)
        self.assertIn("MOCK_HUB_REQUIRES_EXPLICIT_ONLINE_MODE",CPP)
        self.assertIn('setContextProperty("probeMockHub", mockHub)',CPP)
        for sensitive in ("clientName","employeeId","password","apiKey",
                          "CompanyHubStore","SocialIdentityStore"):
            self.assertNotIn(sensitive,QML)

    def test_camera_controls_scroll_instead_of_covering_viewport(self):
        self.assertIn("Flickable {",QML)
        self.assertIn("id: cameraRail",QML)
        self.assertIn("contentHeight: cameraColumn.implicitHeight",QML)
        self.assertIn("clip: true",QML)
        self.assertIn("Flickable.VerticalFlick",QML)
        self.assertIn("Math.min(18,mapView.map.zoomLevel+1)",QML)
        self.assertIn("Math.max(2,mapView.map.zoomLevel-1)",QML)

    def test_capture_diagnostics_exclude_ui_regions(self):
        self.assertIn('"MAP_PALETTE_SAMPLES"',CPP)
        self.assertIn('"cyan" << cyanPixels',CPP)
        self.assertIn('"magenta" << violetPixels',CPP)
        self.assertIn('"orange" << orangePixels',CPP)
        self.assertIn("screenshot.width() - 110",CPP)
        self.assertIn("screenshot.height() - 48",CPP)

    def test_native_gate_demand_marker_registration(self):
        self.assertIn("NEIGHBORHOOD VILLAGE BORDER",WORKFLOW)
        self.assertIn("mock+=(--mock-hub)",WORKFLOW)
        self.assertIn("SYNTHETIC_MARKER_ADDED",WORKFLOW)
        self.assertIn("company-vector-*.png",WORKFLOW)
        self.assertIn("xvfb-run",WORKFLOW)

    def test_isolated_probe_not_in_live_shell(self):
        shell=(ROOT/"shell.qml").read_text()
        company=(ROOT/"widgets/CompanyCoveragePane.qml").read_text()
        for name in ("company-vector-probe","MapQuickItem","probeMockHub"):
            self.assertNotIn(name,shell)
            self.assertNotIn(name,company)


if __name__=="__main__":
    unittest.main()
