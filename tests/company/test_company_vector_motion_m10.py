"""M10: read-only synthetic marker feed and bounded motion instrument contracts."""
from pathlib import Path
import json
import unittest
ROOT=Path(__file__).resolve().parents[2]
APP=ROOT/"experiments/company-vector-qt"
CPP=(APP/"main.cpp").read_text()
QML=(APP/"main.qml").read_text()
CMAKE=(APP/"CMakeLists.txt").read_text()
WORKFLOW=(ROOT/".github/workflows/company-network-vector-probe-m5.yml").read_text()

class MotionAndFixtureBridgeContracts(unittest.TestCase):
    def test_fixture_is_small_and_synthetic(self):
        doc=json.loads((APP/"fixture-hubs.json").read_text())
        self.assertEqual(doc["schema"],"post-apollo.company-hubs.fixture.v1")
        self.assertEqual(len(doc["records"]),3)
        for record in doc["records"]:
            self.assertEqual(set(record),{"id","label","latitude","longitude"})
            self.assertTrue(record["id"].startswith("fixture-"))
            self.assertTrue(record["label"].startswith("DEMO NODE"))
            self.assertTrue(43.64 < record["latitude"] < 43.67)
            self.assertTrue(-79.40 < record["longitude"] < -79.36)

    def test_fixture_is_explicit_and_never_reads_user_hub_directory(self):
        self.assertIn('args.contains("--fixture-hubs")',CPP)
        self.assertIn("fixtureHubs && !anyOnline",CPP)
        self.assertIn("COMPANY_PROBE_HUB_FIXTURE_PATH",CMAKE)
        self.assertIn("QJsonDocument::fromJson",CPP)
        self.assertIn("FIXTURE_FIELD_REFUSED",CPP)
        self.assertIn("FIXTURE_SCHEMA_REFUSED",CPP)
        self.assertIn("FIXTURE_COORDINATES_REFUSED",CPP)
        self.assertIn("fixture.size() > 4096",CPP)
        self.assertIn('setContextProperty("probeFixtureHubs", fixtureRecords)',CPP)
        self.assertNotIn("hubs-v1.json",CPP)
        self.assertNotIn("CompanyHubDirectory.py",QML)
        for source in (CPP,QML):
            for private in ("XDG_DATA_HOME", "clientName", "employeeId", "apiKey"):
                self.assertNotIn(private,source)

    def test_item_is_anchored_on_map_and_selectable(self):
        self.assertIn("id: fixtureHubTemplate",QML)
        self.assertIn("MapQuickItem {",QML)
        self.assertIn("coordinate: QtPositioning.coordinate(record.latitude,record.longitude)",QML)
        self.assertIn("mapView.map.addMapItem(instance)",QML)
        self.assertIn("FIXTURE_MARKERS_ADDED count=",QML)
        self.assertIn("FIXTURE_MARKER_SELECTED",QML)
        self.assertIn("mapView.map.mapReady",QML)

    def test_frame_timing_uses_swap_signal_not_assumed_fps(self):
        self.assertIn('args.contains("--bench-pan-zoom")',CPP)
        self.assertIn("QQuickWindow::frameSwapped",CPP)
        self.assertIn("QElapsedTimer",CPP)
        self.assertIn("BENCH_FRAME_PACING",CPP)
        self.assertIn('"p50_ms"',CPP)
        self.assertIn('"p95_ms"',CPP)
        self.assertIn('"max_ms"',CPP)
        self.assertIn('"frame_intervals"',CPP)
        self.assertIn("software-renderer scheduling",CPP)
        self.assertIn("interval: 33",QML)
        self.assertIn("interval: 8000",QML)
        self.assertIn("BENCH_MOTION_DONE steps=",QML)
        self.assertIn("mapView.map.zoomLevel=15.6+0.25*Math.sin(t/2)",QML)
        self.assertIn("QtPositioning.coordinate(",QML)

    def test_default_offline_and_existing_company_unmodified(self):
        self.assertIn('args.contains("--styled-online")',CPP)
        self.assertIn("QUrl::fromLocalFile(localPath)",CPP)
        self.assertIn("fixtureHubs && !anyOnline",CPP)
        shell=(ROOT/"shell.qml").read_text()
        current=(ROOT/"widgets/CompanyCoveragePane.qml").read_text()
        for term in ("probeFixtureHubs","probeBenchMotion","fixture-hubs.json"):
            self.assertNotIn(term,shell)
            self.assertNotIn(term,current)

    def test_ci_requests_only_public_toronto_view_and_fixture(self):
        self.assertIn("--bench-pan-zoom",WORKFLOW)
        self.assertIn("--fixture-hubs",WORKFLOW)
        self.assertIn("--sample=NEIGHBORHOOD",WORKFLOW)
        self.assertIn("BENCH_FRAME_PACING",WORKFLOW)
        self.assertIn("FIXTURE_MARKERS_ADDED count=3",WORKFLOW)
        self.assertNotIn("$XDG_DATA_HOME",WORKFLOW)

if __name__=="__main__":
    unittest.main()
