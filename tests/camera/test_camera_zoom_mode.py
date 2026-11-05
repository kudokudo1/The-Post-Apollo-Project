"""Camera Zoom mode entry + connection indicators, all tests mocked and offline."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
PANEL = (ROOT / "widgets/CameraW.qml").read_text()
spec = importlib.util.spec_from_file_location(
    "camera_zoom_mode_contract", ROOT / "scripts/camera/camera_cli.py")
camera = importlib.util.module_from_spec(spec)
spec.loader.exec_module(camera)


class ZoomModeTests(unittest.TestCase):
    def test_zoom_entry_auto_opens_without_a_manual_check_button(self):
        self.assertIn('function openZoomMode()', PANEL)
        entry = PANEL.split('function openZoomMode()', 1)[1].split(
            'function prepareZoomInstall(choice)', 1)[0]
        self.assertIn('run("zoomEnter", ["zoom-enter"])', entry)
        self.assertIn('camera.openZoomMode();', PANEL)
        self.assertIn('label: "↓ DOWNLOAD"', PANEL)
        self.assertIn('id: zoomStatusRail', PANEL)
        self.assertIn('name: "ZOOM CHECK"', PANEL)
        self.assertIn('name: "WEB CHECK"', PANEL)
        self.assertIn('name: "LOGIN", value: "UNKNOWN"', PANEL)
        self.assertIn('ZOOM SIGN-IN // UNVERIFIED', PANEL)
        self.assertIn('visible: camera.zoomLaunchState === "FAILED"', PANEL)
        self.assertIn('label: "OPEN / FOCUS ZOOM APP"', PANEL)
        self.assertIn('onLeftClicked: camera.openZoomDirectly()', PANEL)
        self.assertNotIn('label: "CHECK ZOOM"', PANEL)
        self.assertNotIn('label: "OPEN ZOOM CLIENT"', PANEL)

    def test_no_autoinstall_no_background_web_indicator_flickering(self):
        self.assertNotIn('id: zoomStatusRefreshTimer', PANEL)
        self.assertNotIn('interval: 90000', PANEL)
        self.assertIn('run("zoomConnectivity", ["zoom-connectivity"])', PANEL)
        self.assertIn('zoomSetupVisible = payload.installed !== true;', PANEL)
        self.assertIn('zoomLaunchState = "NOT_INSTALLED"', PANEL)
        # The normal mode entry remains the only automatic Zoom launcher.
        self.assertIn('run("zoomEnter", ["zoom-enter"])', PANEL)

    def test_missing_client_leaves_mode_open_and_never_spawns(self):
        with patch.object(camera, "zoom_launch_check",
                          return_value={"installed": False, "windowState": "NOT_FOUND",
                                        "flatpakRunning": False}):
            with patch.object(camera, "zoom_client_open") as launch:
                r = camera.zoom_enter_mode()
        self.assertTrue(r["ok"])
        self.assertFalse(r["installed"])
        self.assertEqual(r["launch"], "NOT_INSTALLED")
        self.assertEqual(r["account"], "UNKNOWN")
        launch.assert_not_called()

    def test_existing_window_or_process_is_not_duplicated(self):
        for view, running in (("VISIBLE", False), ("OTHER_WORKSPACE", False),
                              ("NOT_FOUND", True)):
            with self.subTest(view=view, running=running):
                with patch.object(camera, "zoom_launch_check", return_value={
                        "installed": True, "windowState": view,
                        "flatpakRunning": running}):
                    with patch.object(camera, "zoom_client_command", return_value=[
                            "/usr/bin/flatpak", "run", "--system", "us.zoom.Zoom"]):
                        with patch.object(camera, "zoom_client_open") as launch:
                            r = camera.zoom_enter_mode()
                self.assertTrue(r["ok"])
                self.assertEqual(r["launch"], "ALREADY_RUNNING")
                self.assertEqual(r["installation"], "system")
                launch.assert_not_called()

    def test_entry_starts_client_once_and_does_not_claim_window_or_signin(self):
        with patch.object(camera, "zoom_launch_check", return_value={
                "installed": True, "windowState": "NOT_FOUND", "flatpakRunning": False}):
            with patch.object(camera, "zoom_client_command", return_value=[
                    "/usr/bin/flatpak", "run", "--system", "us.zoom.Zoom"]):
                with patch.object(camera, "zoom_client_open", return_value={
                        "ok": True, "launchState": "PROCESS_RUNNING_UNVERIFIED"}) as launch:
                    r = camera.zoom_enter_mode()
        self.assertTrue(r["ok"])
        self.assertEqual(r["launch"], "SUBMITTED_UNVERIFIED")
        self.assertFalse(r["embedded"])
        self.assertEqual(r["account"], "UNKNOWN")
        launch.assert_called_once_with()

    def test_failed_entry_exposes_error_but_does_not_block_mode(self):
        with patch.object(camera, "zoom_launch_check", return_value={
                "installed": True, "windowState": "NOT_FOUND", "flatpakRunning": False}):
            with patch.object(camera, "zoom_client_command", return_value=[
                    "/usr/bin/flatpak", "run", "--system", "us.zoom.Zoom"]):
                with patch.object(camera, "zoom_client_open", return_value={
                        "ok": False, "error": "ZOOM_START_EXITED_NONZERO"}):
                    r = camera.zoom_enter_mode()
        self.assertTrue(r["ok"])
        self.assertEqual(r["launch"], "FAILED")
        self.assertEqual(r["launchError"], "ZOOM_START_EXITED_NONZERO")

    def test_https_checks_are_independent_and_never_assert_login(self):
        with patch.object(camera, "_camera_https_reachable",
                          side_effect=[True, False]) as probe:
            r = camera.zoom_connectivity()
        self.assertEqual(r["internet"], "REACHABLE")
        self.assertEqual(r["zoomService"], "UNVERIFIED")
        self.assertEqual(r["account"], "UNKNOWN")
        self.assertEqual(probe.call_args_list[0].args[0],
                         "https://example.com/")
        self.assertEqual(probe.call_args_list[1].args[0],
                         "https://zoom.us/")
        self.assertIn("checkedAt", r)

    def test_https_probe_is_head_only_no_personal_fields(self):
        response = Mock()
        response.status = 200
        context = Mock()
        context.__enter__ = Mock(return_value=response)
        context.__exit__ = Mock(return_value=None)
        with patch.object(camera.urllib.request, "urlopen", return_value=context) as go:
            self.assertTrue(camera._camera_https_reachable("https://zoom.us/"))
        request = go.call_args.args[0]
        self.assertEqual(request.get_method(), "HEAD")
        self.assertEqual(request.full_url, "https://zoom.us/")
        self.assertEqual(go.call_args.kwargs["timeout"], 3)
        self.assertNotIn("Authorization", request.headers)
        with patch.object(camera.urllib.request, "urlopen", side_effect=OSError):
            self.assertFalse(camera._camera_https_reachable("https://zoom.us/"))


if __name__ == "__main__":
    unittest.main()
