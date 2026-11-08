"""M30v: Qt CPU readback metadata is NOT an attested Wayland buffer.

The native Qt6 C++ harness is exercised separately in the M30v Actions job.
This source contract verifies the CLI evidence is opt-in/offline-only,
does not change Company's managed QProcess launcher, and cannot smuggle
Qt image pitch into actual selected wl_buffer custody.
"""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
PROBE=ROOT / "experiments/company-vector-qt"
CPP=(PROBE/"main.cpp").read_text()
HEADER=(PROBE/"CompanyVectorReadbackEvidence.h").read_text()
SIDE=(ROOT/"services/company/CompanyVectorSidecarController.qml").read_text()
LAUNCH=(ROOT/"services/company/CompanyVectorSidecarLaunch.py").read_text()
POLICY=(ROOT/"widgets/CompanyVectorPhysicalBackingPolicy.js").read_text()
COMPANY=(ROOT/"widgets/CompanyNetworkW.qml").read_text()
BRIDGE=(ROOT/"widgets/CompanyVectorBridgeLink.qml").read_text()


class CompanyReadbackM30vTests(unittest.TestCase):
    def test_one_shot_only_explicit_flag_and_offline_input(self):
        self.assertIn('args.contains("--readback-evidence")',CPP)
        self.assertIn('args.size() != 2',CPP)
        self.assertIn('args.at(1) != QStringLiteral("--readback-evidence")',CPP)
        for guard in ("anyOnline", "capture", "mockHub", "fixtureHubs",
                      "benchMotion", "ownerLocalHubs", "!sample.isEmpty()"):
            self.assertIn(guard,CPP)
        self.assertIn('M30V_READBACK_ARGUMENTS_REFUSED',CPP)
        self.assertLess(
            CPP.index('M30V_READBACK_ARGUMENTS_REFUSED'),
            CPP.index('const QUrl styleUrl'),
            "refusal happens before online style selection")
        self.assertLess(
            CPP.index('M30V_READBACK_ARGUMENTS_REFUSED'),
            CPP.index('QVariantList ownerRecords'),
            "refusal happens before owner-local records")

    def test_actual_qt_window_grab_but_no_pixel_persistence(self):
        self.assertIn('const QImage pixels = window->grabWindow();',CPP)
        self.assertIn('CompanyVectorReadbackEvidence::inspect(',CPP)
        self.assertIn('window->devicePixelRatio()',CPP)
        self.assertIn('COMPANY_M30V_QT_READBACK_EVIDENCE',CPP)
        self.assertIn('QTimer::singleShot(5500, &app, [&app, window]()',CPP)
        self.assertIn('OBSERVED_QT_READBACK',CPP)
        self.assertIn('? 0 : 17',CPP)
        self.assertNotIn('readbackEvidence && capture',CPP)

    def test_qimage_pitch_is_observed_not_compositor_pitch(self):
        for marker in ('image.bytesPerLine()', 'image.depth()', 'image.format()',
                       'readbackDevicePixelRatio', 'readbackBytesPerLine',
                       'readbackMinimumStrideBytes', 'readbackRowPaddingBytes',
                       'QT_CPU_READBACK_ONLY', 'QQuickWindow::grabWindow',
                       'requiresIndependentHostBufferEvidence'):
            self.assertIn(marker,HEADER,marker)
        self.assertIn('actualStride < minimumStride',HEADER)
        self.assertIn('image.isNull()',HEADER)
        self.assertIn('std::isfinite(windowDevicePixelRatio)',HEADER)
        self.assertIn('INVALID_OR_UNBOUNDED_READBACK_GEOMETRY',HEADER)
        self.assertIn('INCONSISTENT_CPU_READBACK_STRIDE',HEADER)

    def test_unknown_native_buffer_fields_are_null_not_guessed(self):
        for field in ('nativeBufferFormat','nativeBufferStrideBytes',
                      'nativeBufferModifier','nativeBufferAllocationKind',
                      'nativeSurfaceScale'):
            self.assertIn('{"'+field+'", QJsonValue(QJsonValue::Null)}',HEADER)
        self.assertIn('{"productionAuthority", false}',HEADER)
        self.assertIn('{"selectedNativeActorVerified", false}',HEADER)
        self.assertIn('{"waylandBufferAttested", false}',HEADER)
        self.assertIn('"readyForNativeBufferImport"), false',HEADER)
        self.assertNotIn('wl_buffer_get',HEADER)
        self.assertNotIn('zwp_linux_dmabuf',HEADER)

    def test_original_quickshell_attached_lifecycle_not_modified(self):
        self.assertIn('property bool vectorBridgeOptIn: false',COMPANY)
        self.assertIn('property bool bridgeEnabled: false',BRIDGE)
        self.assertIn('vectorRunner.command = ["/usr/bin/python3"',SIDE)
        self.assertIn('signal nativeChildStarted(int pid)',SIDE)
        self.assertIn('os.execv(str(executable)',LAUNCH)
        self.assertNotIn('--readback-evidence',SIDE)
        self.assertNotIn('--readback-evidence',LAUNCH)
        self.assertNotIn('CompanyVectorReadbackEvidence',COMPANY)
        self.assertIn('productionAuthority: false',POLICY)

    def test_full_native_maplibre_ci_executes_offline_readback_and_refuses_online(self):
        workflow=(ROOT/".github/workflows/company-network-vector-probe-m5.yml").read_text()
        self.assertIn("timeout 20s ./company-vector-probe --readback-evidence",
                      workflow)
        self.assertIn('COMPANY_M30V_QT_READBACK_EVIDENCE ',workflow)
        self.assertIn('report["readbackBytesPerLine"]',workflow)
        self.assertIn('report["nativeBufferStrideBytes"] is None',workflow)
        self.assertIn('--readback-evidence --styled-online',workflow)
        self.assertIn('test "$m30v_rc" -eq 16',workflow)
        self.assertIn('test ! -e company-vector-probe.png',workflow)
        self.assertIn('company-vector-probe --styled-online',workflow)
        self.assertIn('company-m30v-readback.log',workflow)

    def test_evidence_helper_is_pure_no_launch_network_or_personal_data(self):
        for forbidden in ('QProcess','QFile','QTcpSocket','QNetworkAccessManager',
                          'CompanyHubStore','SocialIdentity','QQuickWindow::show',
                          'swaymsg','post_apollo_selected_actor','owner-local',
                          'employeeId','customerId','std::system('):
            self.assertNotIn(forbidden,HEADER,forbidden)


if __name__=="__main__":
    unittest.main()
