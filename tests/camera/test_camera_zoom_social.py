"""Offline Camera Zoom/Social integration contracts: no authentication or client launch."""
from pathlib import Path
import importlib.util
import unittest
from unittest.mock import Mock, patch
import sys

ROOT = Path(__file__).resolve().parents[2]
PANEL = (ROOT / "widgets/CameraW.qml").read_text()
SOCIAL_UI = (ROOT / "widgets/messanger/AppSelector.qml").read_text()
SOCIAL_STORE = (ROOT / "services/social/SocialAccountDetails.py").read_text()
CATALOG = (ROOT / "services/messaging/SocialAccountCatalog.py").read_text()

spec = importlib.util.spec_from_file_location("camera_zoom_contract", ROOT / "scripts/camera/camera_cli.py")
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)


class CameraZoomSocialTests(unittest.TestCase):
    def test_zoom_has_its_own_camera_mode_and_shared_social_read_model(self):
        self.assertIn('{id: "zoom", label: "ZOOM"}', PANEL)
        self.assertIn('id: zoomPage', PANEL)
        self.assertIn('import qs.services.social', PANEL)
        self.assertIn('SocialIdentityStore.snapshot', PANEL)
        self.assertIn('SocialAccountDetailsStore.accountNamesFor(zoomIdentityId, "zoom")', PANEL)
        self.assertIn('onZoomIdentityIdChanged: selectedZoomAccountId = ""', PANEL)
        self.assertIn('onLeftClicked: camera.openZoomDirectly()', PANEL)
        self.assertIn('run("zoomEnter", ["zoom-enter"])', PANEL)
        self.assertIn('onLeftClicked: camera.run("zoomStatus", ["zoom-status"])', PANEL)
        self.assertIn('EMBEDDED VIDEO // NOT YET CONNECTED', PANEL)

    def test_missing_zoom_shows_setup_in_same_mode_without_silent_install(self):
        self.assertIn('property bool zoomSetupVisible: false', PANEL)
        self.assertIn('zoomSetupVisible = !payload.available;', PANEL)
        self.assertIn('id: zoomInstallGuide', PANEL)
        self.assertIn('visible: camera.zoomSetupVisible', PANEL)
        self.assertIn('label: "↓ DOWNLOAD"', PANEL)
        self.assertIn('id: zoomStatusRail', PANEL)
        self.assertIn('ONE WEB CHECK ON ENTRY', PANEL)
        self.assertIn('available: !camera.busy', PANEL)
        self.assertIn('camera.zoomSetupVisible = !camera.zoomSetupVisible;', PANEL)
        self.assertIn('ZOOM_CLIENT_NOT_INSTALLED', PANEL)
        self.assertIn('zoomSetupVisible = true;', PANEL)
        self.assertIn('RECHECK ZOOM AFTER INSTALL', PANEL)
        self.assertIn('https://zoom.us/download?os=linux', PANEL)
        self.assertIn('sudo rpm-ostree install ~/Downloads/zoom_x86_64.rpm', PANEL)
        self.assertIn('flatpak install flathub us.zoom.Zoom', PANEL)
        self.assertIn('community-maintained and unverified by Zoom', PANEL)
        self.assertIn('readOnly: true', PANEL)
        self.assertIn('No installation is automatic', PANEL)
        # Installation and browser navigation are never triggered by tab entry.
        entry = PANEL.split('function openZoomMode()', 1)[1].split(
            'function launchZoomClient()', 1)[0]
        self.assertNotIn('openUrlExternally', entry)
        self.assertNotIn('zoom-open', entry)
        self.assertNotIn('flatpak install', entry)

    def test_social_zoom_aliases_reuse_private_store_without_rail_expansion(self):
        self.assertIn('EXTERNAL_ACCOUNT_LABEL_SERVICES = frozenset({"zoom"})', SOCIAL_STORE)
        self.assertIn('service not in KNOWN_ACCOUNT_LABEL_SERVICES', SOCIAL_STORE)
        self.assertIn('appSelector.selectAccountService("zoom")', SOCIAL_UI)
        self.assertIn('ZOOM SIGN-IN // UNVERIFIED', PANEL)
        self.assertEqual(CATALOG.count('("zoom", "ZOOM"'), 0)
        self.assertIn('? "▾ CHOOSE APP (32)"', SOCIAL_UI)
        sys.path.insert(0, str(ROOT / "services/social"))
        try:
            module_spec = importlib.util.spec_from_file_location(
                "camera_social_account_contract", ROOT / "services/social/SocialAccountDetails.py")
            details = importlib.util.module_from_spec(module_spec)
            module_spec.loader.exec_module(details)
            doc = details.new_document()
            doc["identities"]["identity-1"] = {
                "email": "", "phone": "",
                "accounts": {"zoom": [{"id": "account-1", "label": "Work"}]}
            }
            self.assertEqual(details.validate_document(doc)["identities"]["identity-1"]["accounts"]["zoom"][0]["label"], "Work")
            doc["identities"]["identity-1"]["accounts"]["other-unknown"] = "Unsafe"
            with self.assertRaises(details.StoreError):
                details.validate_document(doc)
        finally:
            sys.path.remove(str(ROOT / "services/social"))

    def test_zoom_status_fail_closed_without_client(self):
        with patch.object(backend.shutil, "which", return_value=None):
            status = backend.zoom_client_status()
            self.assertFalse(status["available"])
            self.assertEqual(status["authentication"], "UNKNOWN")
            self.assertFalse(status["socialAuthShared"])
            with patch.object(backend.subprocess, "Popen") as launch:
                self.assertEqual(backend.zoom_client_open()["error"], "ZOOM_CLIENT_NOT_INSTALLED")
                launch.assert_not_called()

    def test_zoom_launch_is_explicit_native_only_no_shell_or_credentials(self):
        with patch.object(backend.shutil, "which", side_effect=lambda n: "/usr/bin/zoom" if n == "zoom" else None):
            with patch.object(backend.subprocess, "Popen",
                              return_value=Mock(poll=Mock(return_value=0))) as launch:
                result = backend.zoom_client_open()
        self.assertTrue(result["ok"])
        self.assertTrue(result["launchRequested"])
        self.assertEqual(result["launchState"], "HANDOFF_UNVERIFIED")
        self.assertEqual(result["authentication"], "UNKNOWN")
        self.assertEqual(launch.call_args.args[0], ["/usr/bin/zoom"])
        self.assertNotIn("shell", launch.call_args.kwargs)
        self.assertTrue(launch.call_args.kwargs["start_new_session"])

    def test_zoom_flatpak_is_checked_read_only_before_launch(self):
        def which(name):
            return "/usr/bin/flatpak" if name == "flatpak" else None
        with patch.object(backend.shutil, "which", side_effect=which):
            with patch.object(backend.subprocess, "run", return_value=Mock(returncode=0)) as run:
                self.assertEqual(backend.zoom_client_command(), ["/usr/bin/flatpak", "run", "--user", "us.zoom.Zoom"])
                self.assertEqual(run.call_args.args[0], ["/usr/bin/flatpak", "info", "--user", "us.zoom.Zoom"])
                self.assertIs(run.call_args.kwargs["stdin"], backend.subprocess.DEVNULL)


if __name__ == "__main__":
    unittest.main()
