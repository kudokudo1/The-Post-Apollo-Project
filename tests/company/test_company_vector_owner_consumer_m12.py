"""M12: opt-in native map consumer accepts only M11 owner-local projection."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
APP=ROOT/"experiments/company-vector-qt"
CPP=(APP/"main.cpp").read_text()
QML=(APP/"main.qml").read_text()
CMAKE=(APP/"CMakeLists.txt").read_text()
WORKFLOW=(ROOT/".github/workflows/company-network-vector-probe-m5.yml").read_text()

class OwnerLocalConsumerContracts(unittest.TestCase):
    def test_explicit_one_shot_owner_only_opt_in(self):
        self.assertIn('args.contains("--owner-local-hubs")',CPP)
        self.assertIn("QProcess ownerReader",CPP)
        self.assertIn("COMPANY_OWNER_MAP_READONLY_SCRIPT",CMAKE)
        self.assertIn('QStringLiteral("--owner-local-view")',CPP)
        self.assertIn("ownerReader.waitForFinished(4000)",CPP)
        self.assertIn("OWNER_LOCAL_PROJECTION_REFUSED",CPP)
        self.assertIn("OWNER_LOCAL_PROJECTION_UNAVAILABLE",CPP)
        self.assertIn('setContextProperty("probeOwnerLocalMode", ownerLocalHubs)',CPP)
        self.assertIn('setContextProperty("probeOwnerLocalHubs", ownerRecords)',CPP)

    def test_consumer_strictly_parses_small_allowed_fields(self):
        self.assertIn('stdoutData.size()>32768',CPP)
        self.assertIn('post-apollo.company-map.owner-local-v1',CPP)
        self.assertIn('OWNER_LOCAL_ONLY_NOT_ORGANIZATION_GRANT',CPP)
        self.assertIn('hub.size()!=4',CPP)
        self.assertIn('QRegularExpression',CPP)
        self.assertIn('seen.contains(id)',CPP)
        self.assertIn('hub.value("reported")!=QJsonValue(true)',CPP)
        self.assertIn('hubs.size()>150',CPP)
        self.assertIn('lat < -85.05112878',CPP)
        self.assertIn('lon < -180',CPP)
        self.assertIn('ownerRecords.append(QVariantMap{',CPP)
        self.assertIn('"longitude", lon',CPP)
        self.assertNotIn('ownerReader.readAllStandardError()',CPP)
        self.assertNotIn('ownerReader.setStandardOutputFile(',CPP)

    def test_owner_markers_are_generic_not_named_or_exfiltrating(self):
        self.assertIn('id: ownerReportedHubTemplate',QML)
        self.assertIn('MapQuickItem {',QML)
        self.assertIn('coordinate: QtPositioning.coordinate(record.latitude,record.longitude)',QML)
        self.assertIn('mapView.map.addMapItem(instance)',QML)
        self.assertIn('text: "REPORTED HUB"',QML)
        self.assertIn('OWNER-LOCAL REPORTED HUBS // NOT VERIFIED',QML)
        self.assertIn('OWNER_LOCAL_MARKERS_ADDED count=',QML)
        self.assertIn('OWNER_LOCAL_REPORTED_MARKER_SELECTED',QML)
        self.assertNotIn('console.log(record.latitude)',QML)
        self.assertNotIn('console.log(record.longitude)',QML)
        self.assertNotIn('text: record.label',QML)
        self.assertNotIn('root.goToSample(record',QML)

    def test_synthetic_and_existing_shell_remain_separate(self):
        shell=(ROOT/"shell.qml").read_text()
        company=(ROOT/"widgets/CompanyCoveragePane.qml").read_text()
        for term in ("probeOwnerLocalHubs","COMPANY_OWNER_MAP_READONLY_SCRIPT",
                     "OWNER_LOCAL_MARKERS_ADDED"):
            self.assertNotIn(term,shell)
            self.assertNotIn(term,company)
        self.assertIn('args.contains("--fixture-hubs")',CPP)
        self.assertIn('args.contains("--styled-online")',CPP)
        self.assertIn('QUrl::fromLocalFile(localPath)',CPP)

    def test_ci_uses_disposable_private_nonpersonal_file_and_offline_window(self):
        self.assertIn("company-owner-test",WORKFLOW)
        self.assertIn("CompanyHubDirectory",WORKFLOW)
        self.assertIn("XDG_DATA_HOME",WORKFLOW)
        self.assertIn("--owner-local-hubs --capture",WORKFLOW)
        self.assertIn("OWNER_LOCAL_PROJECTION_VALIDATED 1",WORKFLOW)
        self.assertIn("OWNER_LOCAL_MARKERS_ADDED count=1",WORKFLOW)
        self.assertIn("company-vector-owner-local.png",WORKFLOW)
        self.assertIn("test_company_vector_owner_consumer_m12.py",WORKFLOW)
        self.assertNotIn("curl -X POST",WORKFLOW)

if __name__=="__main__":
    unittest.main()
