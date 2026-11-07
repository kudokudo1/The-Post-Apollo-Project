"""Offline contracts for Vesktop focus entering Social from outside its dock.

Only an exact, live, uniquely focused main window may request controller
activation. No compositor command, provider login, or local app is used.
"""
import importlib.util
from pathlib import Path
from unittest import TestCase, main

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "widgets/messanger/DiscordGeometry.py"
SOCIAL = ROOT / "widgets/messanger/MessagingW.qml"
spec = importlib.util.spec_from_file_location("social_external_focus", HELPER)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


def window(cid=42, *, title="Friends", visible=True, focused=True,
           app_id="dev.vencord.vesktop", width=1098, height=698):
    return {
        "id": cid, "app_id": app_id, "name": title,
        "visible": visible, "focused": focused,
        "rect": {"x": 100, "y": 50, "width": width, "height": height},
        "nodes": [], "floating_nodes": [],
    }


def tree(*views):
    return {"id": 1, "nodes": list(views), "floating_nodes": []}


def event(cid=42, change="focus"):
    return {"change": change, "container": {"id": cid}}


class ExternalVesktopFocusContracts(TestCase):
    def test_only_unique_visible_focused_vesktop_main_is_accepted(self):
        self.assertEqual(
            bridge.verified_external_vesktop_focus(event(), tree(window())),
            {"event": "externalDiscordFocus", "conId": 42},
        )

    def test_splash_and_hidden_scratchpad_do_not_open_social(self):
        for candidate in (
            window(title="Vesktop", width=300, height=350),
            window(visible=False),
            window(focused=False),
        ):
            with self.subTest(candidate=candidate):
                self.assertIsNone(
                    bridge.verified_external_vesktop_focus(
                        event(), tree(candidate)
                    )
                )

    def test_no_spoofed_or_stale_event_can_activate(self):
        valid = tree(window())
        for candidate in (
            event(43), event(42, "move"), event(42, "new"),
            {"change": "focus", "container": {"id": True}},
            {"change": "focus", "container": {}},
            {},
        ):
            with self.subTest(candidate=candidate):
                self.assertIsNone(
                    bridge.verified_external_vesktop_focus(candidate, valid)
                )
        self.assertIsNone(bridge.verified_external_vesktop_focus(
            event(), tree(window(app_id="org.example.Unrelated"))
        ))

    def test_duplicate_main_views_fail_closed(self):
        self.assertIsNone(bridge.verified_external_vesktop_focus(
            event(), tree(window(), window(43))
        ))

    def test_recheck_live_tree_not_untrusted_event_properties(self):
        # Event data has an arbitrary title/class. Only the re-read tree
        # provides current identity and geometry; event ID alone is a hint.
        spoof = {"change": "focus", "container": {
            "id": 42, "app_id": "org.example.Unrelated", "name": "untrusted"
        }}
        self.assertEqual(bridge.verified_external_vesktop_focus(
            spoof, tree(window())
        )["conId"], 42)
        self.assertIsNone(bridge.verified_external_vesktop_focus(
            event(), tree(window(focused=False))
        ))

    def test_sway_event_subscription_and_closed_menu_route(self):
        helper = HELPER.read_text(encoding="utf-8")
        qml = SOCIAL.read_text(encoding="utf-8")
        self.assertIn("IPC_SUBSCRIBE = 2", helper)
        self.assertIn("IPC_EVENT_WINDOW = 0x80000003", helper)
        self.assertIn("self.event_ipc.request(IPC_SUBSCRIBE, '[\"window\"]')", helper)
        self.assertIn("target=self.external_activation_loop", helper)
        self.assertIn('packet.event === "externalDiscordFocus"', qml)
        self.assertIn("messagingWindow.openDiscordFromExternal(Number(packet.conId))", qml)
        self.assertIn("function openDiscordFromExternal(conId)", qml)
        self.assertIn("messagingWindow.activateApp(1);", qml)
        self.assertIn("if (!discordExternalActivationPending)", qml)
        self.assertIn("var externallyActivated = discordExternalActivationPending;", qml)
        self.assertIn("if (!externallyActivated)", qml)

    def test_no_external_launch_or_geometry_authority_from_event_alone(self):
        qml = SOCIAL.read_text(encoding="utf-8")
        opening = qml.split("function openDiscordFromExternal(conId)", 1)[1].split(
            "function showDiscord()", 1
        )[0]
        self.assertNotIn("discordLaunchProcess.exec", opening)
        self.assertNotIn("sharedPanelWidth =", opening)
        self.assertNotIn("sharedPanelHeight =", opening)
        helper = HELPER.read_text(encoding="utf-8")
        observer = helper.split("def external_activation_loop(", 1)[1].split(
            "def poll_loop(", 1
        )[0]
        self.assertNotIn("queue_sync(", observer)
        self.assertNotIn("queue_command(", observer)


if __name__ == "__main__":
    main()
