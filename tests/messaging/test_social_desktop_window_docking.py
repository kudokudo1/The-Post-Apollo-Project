"""Offline safety/behavior contracts for opt-in native desktop docking.

No Sway compositor, provider account, browser or installed desktop application
is required. Every mutating Sway command is mocked and inspected.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "services/messaging/DesktopWindowBridge.py"
PANEL = ROOT / "widgets/messanger/ProviderAccessPanel.qml"
SOCIAL = ROOT / "widgets/messanger/MessagingW.qml"
SPEC = importlib.util.spec_from_file_location("desktop_window_contract", HELPER)
window = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(window)


def sample_tree(*, two=False, marked=False, social_visible=True):
    def provider(pid, con_id, service_marked=marked):
        return {
            "id": con_id, "pid": pid, "name": "Private chat title, never log",
            "app_id": "unverified-provider-client",
            "marks": [window.MARK_PREFIX + "signal"] if service_marked else [],
            "visible": True, "rect": {"x": 0, "y": 0, "width": 700, "height": 500},
        }
    apps = [provider(4201, 88)]
    if two:
        apps.append(provider(4202, 89))
    return {
        "id": 1, "nodes": [
            {"id": 45, "name": "QS_SOCIAL_MENU", "visible": social_visible,
             "rect": {"x": 100, "y": 50, "width": 1100, "height": 800}},
            *apps,
        ],
    }


def fake_image(pid):
    return {4201: "signal-desktop", 4202: "signal-desktop",
            4300: "firefox", 4500: "viber"}.get(pid, "")


class NativeDesktopDockingContracts(unittest.TestCase):
    def test_only_executable_identity_and_unique_view_count(self):
        tree = sample_tree()
        self.assertEqual(window.unique_window(tree, "signal", fake_image)["id"], 88)
        self.assertIsNone(window.unique_window(tree, "viber", fake_image))
        self.assertIsNone(window.unique_window(sample_tree(two=True), "signal", fake_image))
        self.assertEqual(set(window.EXECUTABLE_NAMES), {"signal", "viber", "wechat"})
        for name in ("line", "kakaotalk", "messenger", "whatsapp", "missing"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                window.candidates(tree, name, fake_image)

    def test_probe_only_reads_no_window_mutation(self):
        called = Mock()
        result = window.operation("probe", "signal", tree=sample_tree(),
                                  name_reader=fake_image, execute=called)
        called.assert_not_called()
        self.assertTrue(result["windowAvailable"])
        self.assertFalse(result["docked"])
        self.assertFalse(result["changed"])
        self.assertNotIn("Private chat title", json.dumps(result))

    def test_ambiguous_or_unidentified_window_fails_closed(self):
        called = Mock()
        a = window.operation("dock", "signal", tree=sample_tree(two=True),
                             name_reader=fake_image, execute=called)
        b = window.operation("dock", "signal", tree=sample_tree(),
                             name_reader=lambda pid: "firefox", execute=called)
        called.assert_not_called()
        self.assertTrue(a["ambiguous"])
        self.assertFalse(a["changed"])
        self.assertFalse(b["windowAvailable"])

    def test_dock_is_exact_con_id_explicit_and_bounded_to_social(self):
        commands = []
        result = window.operation("dock", "signal", tree=sample_tree(),
                                  name_reader=fake_image, execute=commands.append)
        self.assertTrue(result["changed"])
        self.assertTrue(result["docked"])
        self.assertEqual(len(commands), 1)
        command = commands[0]
        self.assertIn("[con_id=88] floating enable", command)
        self.assertIn("[con_id=88] resize set width 988 px height 798 px", command)
        self.assertIn("[con_id=88] move absolute position 211 px 51 px", command)
        self.assertIn("[con_id=88] mark --add post-apollo-social-desktop-signal", command)
        self.assertIn("[con_id=88] focus", command)
        for forbidden in ("kill", "exec", "[app_id=", "[class=", "password", "Private chat"):
            self.assertNotIn(forbidden, command)

    def test_dock_cannot_use_hidden_or_too_small_social(self):
        calls = []
        hidden = window.operation("dock", "signal", tree=sample_tree(social_visible=False),
                                  name_reader=fake_image, execute=calls.append)
        self.assertFalse(hidden["changed"])
        tree = sample_tree()
        tree["nodes"][0]["rect"]["width"] = 250
        with self.assertRaises(ValueError):
            window.operation("dock", "signal", tree=tree,
                             name_reader=fake_image, execute=calls.append)
        self.assertEqual(calls, [])

    def test_hide_only_window_explicitly_marked_by_post_apollo(self):
        calls = []
        unmarked = window.operation("hide", "signal", tree=sample_tree(marked=False),
                                    name_reader=fake_image, execute=calls.append)
        self.assertFalse(unmarked["changed"])
        managed = window.operation("hide", "signal", tree=sample_tree(marked=True),
                                   name_reader=fake_image, execute=calls.append)
        self.assertTrue(managed["changed"])
        self.assertEqual(calls, ["[con_id=88] move scratchpad"])

    def test_sway_command_uses_argv_not_shell_and_validates_ack(self):
        real_subprocess = window.subprocess.run
        def succeed(argv, **kwargs):
            self.assertEqual(argv[:2], ["swaymsg", "-r"])
            self.assertEqual(len(argv), 3)
            self.assertNotIn("shell", kwargs)
            return type("Result", (), {"stdout": '[{"success":true}]'})()
        window.subprocess.run = succeed
        try:
            window.sway_command("[con_id=88] focus")
            def fail(argv, **kwargs):
                return type("Result", (), {"stdout": '[{"success":false}]'})()
            window.subprocess.run = fail
            with self.assertRaises(ValueError):
                window.sway_command("[con_id=88] focus")
        finally:
            window.subprocess.run = real_subprocess

    def test_qml_docking_is_direct_click_and_auto_hide_on_leave(self):
        panel = PANEL.read_text(encoding="utf-8")
        social = SOCIAL.read_text(encoding="utf-8")
        self.assertIn('signal desktopDocked(string serviceId)', panel)
        self.assertIn('function dockWindow()', panel)
        self.assertIn('onClicked: panel.dockWindow()', panel)
        self.assertIn('function probeWindow()', panel)
        self.assertIn('DOCK DESKTOP WINDOW IN SOCIAL', panel)
        self.assertIn('CHECK FOR DESKTOP WINDOW', panel)
        self.assertIn('windowRetryTimer', panel)
        self.assertIn('Quickshell.shellPath("services/messaging/DesktopWindowBridge.py")', panel)
        self.assertIn('function hideProviderDesktop()', social)
        self.assertIn('onDesktopDocked: function(serviceId)', social)
        self.assertIn('hideProviderDesktop();', social)
        self.assertIn('providerDesktopManaged: false', social)
        self.assertIn('!messagingWindow.providerDesktopManaged', social)
        self.assertIn('    providerDesktopService = "";', social)
        self.assertNotIn("password", panel.lower())

    def test_cli_probe_error_never_exposes_provider_window_titles(self):
        result = subprocess.run([sys.executable, str(HELPER), "probe", "signal"],
                                text=True, capture_output=True, timeout=6)
        # No running compositor in CI. If Sway is present, probing is still read-only.
        self.assertIn(result.returncode, (0, 2))
        payload = json.loads(result.stdout)
        self.assertFalse(payload["changed"])
        self.assertNotIn("Private chat", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
