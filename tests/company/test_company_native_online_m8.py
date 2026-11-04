"""M8: native screenshot smoke is public-only, bounded and opt-in by flag."""
from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[2]
APP=ROOT/"experiments/company-vector-qt"
WORKFLOW=ROOT/".github/workflows/company-network-vector-probe-m5.yml"


class OnlineNativeSmokeTests(unittest.TestCase):
    def test_unchanged_offline_default_and_explicit_online(self):
        cpp=(APP/"main.cpp").read_text()
        self.assertIn('args.contains("--online")',cpp)
        self.assertIn('args.contains("--styled-online")',cpp)
        self.assertIn("const bool anyOnline = online || styledOnline",cpp)
        self.assertIn("QUrl::fromLocalFile(localPath)",cpp)
        self.assertIn("QUrl::fromLocalFile(styledPath)",cpp)
        self.assertIn('setContextProperty("probeSample", sample)',cpp)
        self.assertIn("INVALID_OR_OFFLINE_SAMPLE",cpp)
        self.assertIn("!allowedSamples.contains(sample)",cpp)
        self.assertIn("!sample.isEmpty() && !anyOnline",cpp)

    def test_public_regression_places_cover_metro_rural_and_cross_border(self):
        cpp=(APP/"main.cpp").read_text()
        qml=(APP/"main.qml").read_text()
        for label in ("USA", "RURAL", "CANADA", "MEXICO", "ALASKA", "HAWAII"):
            self.assertIn('QStringLiteral("'+label+'")',cpp)
            self.assertIn('label:"'+label+'"',qml)
        self.assertIn('if (probeOnline && probeSample !== "")',qml)
        self.assertIn("root.goToSample(probeSample)",qml)
        self.assertIn("map.center: probeOnline ? root.nationwide : root.flint",qml)

    def test_native_ci_reuses_one_build_and_limits_to_three_viewports(self):
        text=WORKFLOW.read_text()
        self.assertIn("git clone --depth 1 --branch v3.0.0",text)
        self.assertIn("-DMLN_QT_WITH_INTERNAL_ICU=ON",text)
        self.assertIn("qmaplibre",text.lower())
        self.assertIn("for sample in USA RURAL CANADA NEIGHBORHOOD VILLAGE BORDER;",text)
        self.assertIn("--styled-online",text)
        self.assertIn('timeout 45s ./company-vector-probe',text)
        self.assertIn('cp company-vector-probe.png "$GITHUB_WORKSPACE/company-vector-offline.png"',text)
        self.assertIn("company-vector-*.png",text)
        self.assertNotIn("quickshell --restart",text)
        self.assertNotIn("dnf install",text)
        self.assertNotIn("--sample=$USER",text)
        self.assertNotIn("$HOME/.config/quickshell",text)

    def test_capture_logs_geometry_without_claiming_real_coverage(self):
        cpp=(APP/"main.cpp").read_text()
        self.assertIn("CAPTURE_CREATED",cpp)
        self.assertIn("CAPTURE_DIAGNOSTIC",cpp)
        self.assertIn("non-purple-samples",cpp)
        self.assertIn("const int settleMilliseconds = anyOnline ? 15000 : 5500;",cpp)
        style=json.loads((APP/"style-post-apollo-online.json").read_text())
        self.assertEqual(style["metadata"]["service-coverage"],"none")
        self.assertEqual(style["sources"]["openmaptiles"]["url"],
                         "https://tiles.openfreemap.org/planet")
        self.assertNotIn("bounds",style["sources"]["openmaptiles"])

    def test_nothing_hooks_experiment_into_live_company_or_shell(self):
        shell=(ROOT/"shell.qml").read_text()
        widget=(ROOT/"widgets/CompanyCoveragePane.qml").read_text()
        self.assertNotIn("company-vector-probe",shell)
        self.assertNotIn("company-vector-probe",widget)
        self.assertNotIn("style-post-apollo-online",widget)


if __name__=="__main__":
    unittest.main()
