"""Autoscroll Stage 3: input-transparent anchored overlay, stop-channel gate."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
OVERLAY = (ROOT / "widgets/cpuplus/AutoscrollAnchorOverlay.qml").read_text()
BACKEND = (ROOT / "services/input/AutoscrollEvdevBackend.py").read_text()
STOP = (ROOT / "services/input/AutoscrollStopChannel.py").read_text()
CLI = (ROOT / "services/input/AutoscrollStop.py").read_text()
FIXTURE = (ROOT / "tests/cpuplus/fixtures/MouseScrollNative.qml").read_text()


class OverlayStopContracts(unittest.TestCase):
    def test_overlay_is_hidden_without_coordinates_and_runtime_authority(self):
        for marker in (
            "property bool authorized: false",
            "property bool coordinateVerified: false",
            "property bool runtimeVerified: false",
            "property real anchorX: -1",
            "property real anchorY: -1",
            "readonly property bool safeToShow:",
            "visible: safeToShow",
            "verifiedOutput === String(overlay.screen.name)",
            "anchorOutput === String(overlay.screen.name)",
        ):
            self.assertIn(marker, OVERLAY)
        self.assertIn("Number.isFinite(anchorX)", OVERLAY)
        self.assertIn("Number.isFinite(anchorY)", OVERLAY)

    def test_overlay_never_intercepts_pointer_or_keyboard(self):
        self.assertIn("PanelWindow {", OVERLAY)
        self.assertIn("mask: Region {}", OVERLAY)
        self.assertIn("focusable: false", OVERLAY)
        self.assertIn("exclusionMode: ExclusionMode.Ignore", OVERLAY)
        self.assertIn("color: \"transparent\"", OVERLAY)
        self.assertNotIn("MouseArea {", OVERLAY)
        self.assertNotIn("TapHandler {", OVERLAY)
        self.assertNotIn("Keys.onPressed:", OVERLAY)
        self.assertNotIn("grab()", OVERLAY)

    def test_driver_cannot_run_without_socket_health(self):
        self.assertIn("from AutoscrollStopChannel import StopServer", BACKEND)
        self.assertIn("stop_server = StopServer()", BACKEND)
        self.assertIn("stop_server.__enter__()", BACKEND)
        self.assertIn("if not stop_server.healthy():", BACKEND)
        self.assertIn("if stop_server.poll():", BACKEND)
        self.assertIn("stop_server.close()", BACKEND)
        self.assertIn('engine.cancel("external_stop")', BACKEND)
        self.assertIn('engine.cancel("stop_channel_lost")', BACKEND)

    def test_same_uid_private_socket_and_manual_stop_only(self):
        self.assertIn("socket.AF_UNIX", STOP)
        self.assertIn("socket.SO_PEERCRED", STOP)
        self.assertIn("uid != os.getuid()", STOP)
        self.assertIn("SOCKET_NAME = \"autoscroll-stop-v1.sock\"", STOP)
        self.assertIn('STOP_COMMAND = b"STOP\\n"', STOP)
        self.assertIn("def healthy(self):", STOP)
        self.assertIn("def send_stop():", STOP)
        self.assertIn('args != ["--stop"]', CLI)
        for forbidden in ("systemctl", "sudo ", "pkexec", "chmod 666",
                          "GlobalShortcut", "Keyboard", "socket.AF_INET"):
            self.assertNotIn(forbidden, STOP + CLI)

    def test_native_disposable_overlay_confirmation(self):
        self.assertIn("AutoscrollAnchorOverlay {", FIXTURE)
        self.assertIn("AUTOSCROLL_OVERLAY_NATIVE_PASS", FIXTURE)
        self.assertIn("OVERLAY_PREMATURELY_ACTIVE", FIXTURE)
        self.assertIn("OVERLAY_REVOCATION_FAILED", FIXTURE)


if __name__ == "__main__":
    unittest.main()
