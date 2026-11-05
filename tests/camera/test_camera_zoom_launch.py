"""Camera Zoom launcher verification: synthetic only; no Flatpak or Sway actions."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
PANEL = (ROOT / "widgets/CameraW.qml").read_text()
spec = importlib.util.spec_from_file_location(
    "camera_zoom_launch_contract", ROOT / "scripts/camera/camera_cli.py")
camera = importlib.util.module_from_spec(spec)
spec.loader.exec_module(camera)


class CameraZoomLaunchTests(unittest.TestCase):
    def test_zoom_button_does_not_claim_window_before_read_only_check(self):
        self.assertIn('function checkZoomWindow()', PANEL)
        self.assertIn('["zoom-launch-check"]', PANEL)
        self.assertIn('id: zoomLaunchCheckTimer', PANEL)
        self.assertIn('interval: 4000', PANEL)
        self.assertIn('zoomLaunchCheckTimer.restart();', PANEL)
        self.assertIn('label: "CHECK ZOOM WINDOW / PROCESS"', PANEL)
        self.assertIn('onLeftClicked: camera.checkZoomWindow()', PANEL)
        self.assertIn('ZOOM // LAUNCH SUBMITTED // WINDOW NOT VERIFIED YET', PANEL)
        self.assertNotIn('ZOOM // OPEN REQUESTED // SIGN IN THROUGH ZOOM CLIENT', PANEL)
        self.assertIn('ZOOM // NO WINDOW FOUND // SEE TERMINAL DIAGNOSTICS', PANEL)
        self.assertIn('flatpak run --user us.zoom.Zoom', PANEL)
        self.assertIn('flatpak run --system us.zoom.Zoom', PANEL)
        self.assertIn('readOnly: true', PANEL)
        self.assertIn('NO AUTOMATIC PERMISSION CHANGES.', PANEL)

    def test_nonzero_launch_exit_is_error_not_accepted(self):
        p = Mock(poll=Mock(return_value=2))
        with patch.object(camera, "zoom_client_command", return_value=["/usr/bin/flatpak", "run", "--user", "us.zoom.Zoom"]):
            with patch.object(camera.subprocess, "Popen", return_value=p) as launched:
                output = camera.zoom_client_open()
        self.assertFalse(output["ok"])
        self.assertEqual(output["error"], "ZOOM_START_EXITED_NONZERO")
        self.assertEqual(output["exitCode"], 2)
        self.assertEqual(launched.call_args.args[0], ["/usr/bin/flatpak", "run", "--user", "us.zoom.Zoom"])
        self.assertNotIn("shell", launched.call_args.kwargs)
        self.assertIs(launched.call_args.kwargs["stderr"], camera.subprocess.DEVNULL)

    def test_exit_zero_still_does_not_verify_window(self):
        with patch.object(camera, "zoom_client_command", return_value=["/usr/bin/zoom"]):
            with patch.object(camera.subprocess, "Popen", return_value=Mock(poll=Mock(return_value=0))):
                result = camera.zoom_client_open()
        self.assertTrue(result["ok"])
        self.assertEqual(result["launchState"], "HANDOFF_UNVERIFIED")
        self.assertNotIn("windowVisible", result)

    def test_user_scope_preferred_and_system_scope_fallback(self):
        with patch.object(camera.shutil, "which", side_effect=lambda n: "/usr/bin/flatpak" if n == "flatpak" else None):
            with patch.object(camera.subprocess, "run",
                              side_effect=[Mock(returncode=1), Mock(returncode=0)]) as run:
                argv = camera.zoom_client_command()
        self.assertEqual(argv, ["/usr/bin/flatpak", "run", "--system", "us.zoom.Zoom"])
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].args[0],
                         ["/usr/bin/flatpak", "info", "--user", "us.zoom.Zoom"])
        self.assertEqual(run.call_args_list[1].args[0],
                         ["/usr/bin/flatpak", "info", "--system", "us.zoom.Zoom"])

    def test_sway_class_match_uses_no_titles_or_content(self):
        tree = {
            "nodes": [{"app_id": None, "window_properties": {"class": "zoom"},
                       "name": "Private meeting title must never appear",
                       "visible": True, "nodes": [], "floating_nodes": []}],
            "floating_nodes": []}
        with patch.object(camera.shutil, "which", return_value="/usr/bin/swaymsg"):
            with patch.object(camera.subprocess, "run",
                              return_value=Mock(returncode=0, stdout=json.dumps(tree).encode())):
                self.assertEqual(camera._zoom_sway_window_state(), "VISIBLE")
        tree["nodes"][0]["visible"] = False
        with patch.object(camera.shutil, "which", return_value="/usr/bin/swaymsg"):
            with patch.object(camera.subprocess, "run",
                              return_value=Mock(returncode=0, stdout=json.dumps(tree).encode())):
                self.assertEqual(camera._zoom_sway_window_state(), "OTHER_WORKSPACE")

    def test_zoom_probe_returns_only_runtime_flags(self):
        tree = {"nodes": [], "floating_nodes": []}
        def which(cmd):
            return "/usr/bin/swaymsg" if cmd == "swaymsg" else None
        with patch.object(camera, "zoom_client_command", return_value=[
                "/usr/bin/flatpak", "run", "--user", "us.zoom.Zoom"]):
            with patch.object(camera.shutil, "which", side_effect=which):
                with patch.object(camera.subprocess, "run", side_effect=[
                    Mock(returncode=0, stdout=b"Application\nus.zoom.Zoom\n"),
                    Mock(returncode=0, stdout=json.dumps(tree).encode())]) as run:
                    status = camera.zoom_launch_check()
        self.assertEqual(status, {"ok": True, "kind": "zoom-launch-check",
                                  "installed": True, "windowState": "NOT_FOUND",
                                  "flatpakRunning": True})
        self.assertEqual(run.call_args_list[0].args[0],
                         ["/usr/bin/flatpak", "ps", "--columns=application"])
        self.assertEqual(run.call_args_list[1].args[0],
                         ["/usr/bin/swaymsg", "-t", "get_tree"])

    def test_direct_open_focuses_existing_exact_zoom_window(self):
        tree = {"nodes": [
            {"id": 5, "app_id": "other-app", "name": "Zoom meeting", "nodes": [], "floating_nodes": []},
            {"id": 203, "app_id": "us.zoom.Zoom", "name": "Private", "nodes": [], "floating_nodes": []}
        ], "floating_nodes": []}
        with patch.object(camera, "zoom_client_command",
                          return_value=["/usr/bin/flatpak", "run", "--system", "us.zoom.Zoom"]):
            with patch.object(camera.shutil, "which", return_value="/usr/bin/swaymsg"):
                with patch.object(camera.subprocess, "run", side_effect=[
                        Mock(returncode=0, stdout=json.dumps(tree).encode()),
                        Mock(returncode=0)]) as run:
                    with patch.object(camera, "zoom_client_open") as launch:
                        result = camera.zoom_activate_client()
        self.assertTrue(result["ok"])
        self.assertEqual(result["activation"], "WINDOW_FOCUSED")
        self.assertTrue(result["windowVerified"])
        self.assertEqual(run.call_args_list[1].args[0],
                         ["/usr/bin/swaymsg", "[con_id=203]", "focus"])
        launch.assert_not_called()

    def test_direct_open_attempts_launch_even_with_background_process(self):
        with patch.object(camera, "zoom_client_command",
                          return_value=["/usr/bin/flatpak", "run", "--system", "us.zoom.Zoom"]):
            with patch.object(camera, "_zoom_native_focus", return_value=False):
                with patch.object(camera, "zoom_client_open", return_value={
                        "ok": True, "launchRequested": True, "launchState": "HANDOFF_UNVERIFIED"
                        }) as launch:
                    result = camera.zoom_activate_client()
        self.assertTrue(result["ok"])
        self.assertEqual(result["activation"], "LAUNCH_REQUESTED_WINDOW_UNVERIFIED")
        self.assertFalse(result["windowVerified"])
        launch.assert_called_once_with()
        self.assertIn('label: "OPEN / FOCUS ZOOM APP"', PANEL)
        self.assertIn('onLeftClicked: camera.openZoomDirectly()', PANEL)

    def test_direct_open_fails_closed_if_not_installed(self):
        with patch.object(camera, "zoom_client_command", return_value=None):
            with patch.object(camera, "zoom_client_open") as launch:
                result = camera.zoom_activate_client()
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "ZOOM_CLIENT_NOT_INSTALLED")
        launch.assert_not_called()

    def test_focus_rejects_window_title_spoofing_and_invalid_con_id(self):
        tree = {"nodes": [{"id": "12; exec malicious", "app_id": "us.zoom.Zoom",
                           "nodes": [], "floating_nodes": []},
                          {"id": 13, "app_id": "unrelated", "name": "Zoom",
                           "nodes": [], "floating_nodes": []}],
                "floating_nodes": []}
        with patch.object(camera.shutil, "which", return_value="/usr/bin/swaymsg"):
            with patch.object(camera.subprocess, "run",
                              return_value=Mock(returncode=0, stdout=json.dumps(tree).encode())) as run:
                self.assertFalse(camera._zoom_native_focus())
        self.assertEqual(run.call_count, 1)
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_no_sway_probe_is_unknown_not_missing_window(self):
        with patch.object(camera.shutil, "which", return_value=None):
            self.assertEqual(camera._zoom_sway_window_state(), "UNKNOWN")
        with patch.object(camera, "zoom_client_command", return_value=None):
            result = camera.zoom_launch_check()
        self.assertFalse(result["installed"])
        self.assertFalse(result["flatpakRunning"])


if __name__ == "__main__":
    unittest.main()
