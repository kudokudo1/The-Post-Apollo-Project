"""Zoom installation button safety: synthetic only, no network or host package changes."""
from pathlib import Path
import importlib.util
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
PANEL = (ROOT / "widgets/CameraW.qml").read_text()
spec = importlib.util.spec_from_file_location(
    "camera_zoom_install_contract", ROOT / "scripts/camera/camera_cli.py")
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)


class CameraZoomInstallTests(unittest.TestCase):
    def test_ui_has_two_explicit_install_buttons_and_cancel(self):
        self.assertIn('label: "INSTALL DOWNLOADED OFFICIAL RPM"', PANEL)
        self.assertIn('onLeftClicked: camera.prepareZoomInstall("official-rpm")', PANEL)
        self.assertIn('label: "INSTALL COMMUNITY FLATPAK"', PANEL)
        self.assertIn('onLeftClicked: camera.prepareZoomInstall("community-flatpak")', PANEL)
        self.assertIn('id: zoomInstallConfirm', PANEL)
        self.assertIn('visible: camera.zoomInstallChoice !== ""', PANEL)
        self.assertIn('label: "CONFIRM INSTALL"', PANEL)
        self.assertIn('onLeftClicked: camera.confirmZoomInstall()', PANEL)
        self.assertIn('onLeftClicked: camera.zoomInstallChoice = ""', PANEL)
        self.assertIn('CONFIRM_ZOOM_INSTALL', PANEL)
        self.assertIn('zoomInstallNotice =', PANEL)
        # Only explicit user interaction may invoke package installation.
        passive = PANEL.split('function openZoomMode()', 1)[1].split(
            'function prepareZoomInstall()', 1)[0] if 'function prepareZoomInstall()' in PANEL else (
            PANEL.split('function openZoomMode()', 1)[1].split(
                'function prepareZoomInstall(choice)', 1)[0])
        self.assertNotIn('zoom-install', passive)
        self.assertNotIn('confirmZoomInstall()', passive)
        self.assertIn('available: !camera.busy', PANEL)

    def test_confirmation_and_method_guard_prevent_side_effects(self):
        with patch.object(backend, "zoom_client_command", return_value=None):
            with patch.object(backend, "_zoom_install_command") as execute:
                self.assertEqual(
                    backend.zoom_install_client("community-flatpak", "INCORRECT")["error"],
                    "INSTALL_CONFIRMATION_REQUIRED")
                self.assertEqual(
                    backend.zoom_install_client("random-method", "CONFIRM_ZOOM_INSTALL")["error"],
                    "INSTALL_METHOD_UNSUPPORTED")
                execute.assert_not_called()
        with patch.object(backend, "zoom_client_command", return_value=["/usr/bin/zoom"]):
            with patch.object(backend, "_zoom_install_command") as execute:
                result = backend.zoom_install_client("community-flatpak", "CONFIRM_ZOOM_INSTALL")
                self.assertEqual(result["error"], "ZOOM_ALREADY_INSTALLED")
                execute.assert_not_called()

    def test_flatpak_user_install_explicit_repo_and_status_verify(self):
        calls = []
        def fake(argv, timeout):
            calls.append(argv)
            return Mock(returncode=0)
        with patch.object(backend, "zoom_client_command", return_value=None):
            with patch.object(backend.shutil, "which", return_value="/usr/bin/flatpak"):
                with patch.object(backend, "_zoom_install_command", side_effect=fake):
                    result = backend.zoom_install_client("community-flatpak", "CONFIRM_ZOOM_INSTALL")
        self.assertTrue(result["ok"])
        self.assertFalse(result["restartRequired"])
        self.assertTrue(result["installed"])
        self.assertEqual(calls, [
            ["/usr/bin/flatpak", "remote-add", "--user", "--if-not-exists", "flathub",
             "https://dl.flathub.org/repo/flathub.flatpakrepo"],
            ["/usr/bin/flatpak", "install", "--user", "--noninteractive", "--assumeyes",
             "flathub", "us.zoom.Zoom"],
            ["/usr/bin/flatpak", "info", "--user", "us.zoom.Zoom"],
        ])
        self.assertTrue(all("sudo" not in call and "pkexec" not in call for call in calls))

    def test_failed_remote_or_install_never_claims_success(self):
        with patch.object(backend, "zoom_client_command", return_value=None):
            with patch.object(backend.shutil, "which", return_value="/usr/bin/flatpak"):
                with patch.object(backend, "_zoom_install_command",
                                  return_value=Mock(returncode=1)) as execute:
                    result = backend.zoom_install_client("community-flatpak", "CONFIRM_ZOOM_INSTALL")
                    self.assertEqual(result["error"], "FLATHUB_REMOTE_FAILED")
                    self.assertEqual(execute.call_count, 1)
                with patch.object(backend, "_zoom_install_command",
                                  side_effect=[Mock(returncode=0), Mock(returncode=1)]) as execute:
                    result = backend.zoom_install_client("community-flatpak", "CONFIRM_ZOOM_INSTALL")
                    self.assertEqual(result["error"], "FLATPAK_INSTALL_FAILED")
                    self.assertEqual(execute.call_count, 2)
                with patch.object(backend, "_zoom_install_command",
                                  side_effect=[Mock(returncode=0), None]) as execute:
                    result = backend.zoom_install_client("community-flatpak", "CONFIRM_ZOOM_INSTALL")
                    self.assertEqual(result["error"], "FLATPAK_INSTALL_TIMEOUT_CHECK_STATUS")

    def test_official_rpm_refuses_missing_file_and_symlink(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            (home / "Downloads").mkdir()
            with patch.object(backend, "home", return_value=home):
                with patch.object(backend, "zoom_client_command", return_value=None):
                    with patch.object(backend, "_zoom_install_command") as execute:
                        self.assertEqual(
                            backend.zoom_install_client("official-rpm", "CONFIRM_ZOOM_INSTALL")["error"],
                            "ZOOM_RPM_NOT_DOWNLOADED")
                        execute.assert_not_called()
                other = home / "file.rpm"
                other.write_bytes(b"fixture")
                (home / "Downloads" / "zoom_x86_64.rpm").symlink_to(other)
                self.assertEqual(
                    backend._zoom_official_rpm()[1], "ZOOM_RPM_UNSAFE_FILE")

    def test_signed_official_rpm_stages_only_after_package_check(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            folder = home / "Downloads"
            folder.mkdir()
            file = folder / "zoom_x86_64.rpm"
            file.write_bytes(b"mock synthetic RPM" * 400)
            file.chmod(0o600)
            calls = []
            def fake(argv, timeout):
                calls.append(argv)
                if argv[0] == "/usr/bin/rpm":
                    return Mock(returncode=0, stdout=b"zoom x86_64", stderr=b"")
                if argv[0] == "/usr/bin/rpmkeys":
                    return Mock(returncode=0, stdout=b"digests signatures OK", stderr=b"")
                return Mock(returncode=0, stdout=b"", stderr=b"")
            def which(name):
                return "/usr/bin/" + name
            with patch.object(backend, "home", return_value=home):
                with patch.object(backend, "zoom_client_command", return_value=None):
                    with patch.object(backend.shutil, "which", side_effect=which):
                        with patch.object(backend, "_zoom_install_command", side_effect=fake):
                            result = backend.zoom_install_client("official-rpm", "CONFIRM_ZOOM_INSTALL")
            self.assertTrue(result["ok"])
            self.assertTrue(result["staged"])
            self.assertFalse(result["installed"])
            self.assertTrue(result["restartRequired"])
            self.assertEqual(calls[0][1:3], ["-qp", "--queryformat"])
            self.assertEqual(calls[1][1], "--checksig")
            self.assertEqual(calls[2], ["/usr/bin/pkexec", "/usr/bin/rpm-ostree",
                                        "install", str(file)])
            self.assertNotIn("sudo", calls[2])

    def test_unverified_rpm_signature_prevents_install(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            folder = home / "Downloads"
            folder.mkdir()
            file = folder / "zoom_x86_64.rpm"
            file.write_bytes(b"mock synthetic RPM" * 400)
            file.chmod(0o600)
            calls = []
            def fake(argv, timeout):
                calls.append(argv)
                if argv[0] == "/usr/bin/rpm":
                    return Mock(returncode=0, stdout=b"zoom x86_64", stderr=b"")
                return Mock(returncode=0, stdout=b"digests signatures NOKEY", stderr=b"")
            with patch.object(backend, "home", return_value=home):
                with patch.object(backend, "zoom_client_command", return_value=None):
                    with patch.object(backend.shutil, "which", side_effect=lambda n: "/usr/bin/" + n):
                        with patch.object(backend, "_zoom_install_command", side_effect=fake):
                            result = backend.zoom_install_client("official-rpm", "CONFIRM_ZOOM_INSTALL")
            self.assertEqual(result["error"], "ZOOM_RPM_SIGNATURE_UNVERIFIED")
            self.assertEqual(len(calls), 2)

    def test_no_shell_or_arbitrary_package_arg(self):
        with patch.object(backend.subprocess, "run", return_value=Mock(returncode=0)) as run:
            backend._zoom_install_command(["/usr/bin/flatpak", "info", "us.zoom.Zoom"], timeout=5)
            self.assertIs(run.call_args.kwargs["stdin"], backend.subprocess.DEVNULL)
            self.assertNotIn("shell", run.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()
