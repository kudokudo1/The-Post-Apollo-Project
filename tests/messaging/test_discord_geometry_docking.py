"""Discord/Social Sway docking regression contracts, without a live compositor.

The initial placement is Social-owned. Vesktop's old scratchpad geometry
must never be adopted until we have observed it in the expected Social slot.
After that, both Mod-move/resize leader directions remain supported.
"""
import importlib.util
import io
import json
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
GEOMETRY = ROOT / "widgets/messanger/DiscordGeometry.py"
SOCIAL = ROOT / "widgets/messanger/MessagingW.qml"
BACKING = ROOT / "widgets/messanger/DiscordBackingW.qml"
spec = importlib.util.spec_from_file_location("discord_docking_regression", GEOMETRY)
geometry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geometry)


def sample(*, focus="discord", discord_x=211, discord_y=51,
           social_x=100, social_y=50):
    return {
        "social": {
            "rect": {"x": social_x, "y": social_y,
                     "width": 1210, "height": 700},
            "focused": focus == "social",
        },
        "discord": {
            "rect": {"x": discord_x, "y": discord_y,
                     "width": 1098, "height": 698},
            "focused": focus == "discord",
        },
    }


class DiscordDockingTests(TestCase):
    def bridge(self, docked=False):
        bridge = geometry.Bridge(0.1)
        bridge.discord_selected = True
        bridge.discord_ready = True
        bridge.discord_docked = docked
        commands = []
        bridge.queue_sync = commands.append
        return bridge, commands

    def test_first_focused_vesktop_sample_cannot_drag_social(self):
        bridge, commands = self.bridge(docked=False)
        snapshot = bridge.fast_follow(sample(discord_x=780, discord_y=450))
        self.assertIsNone(snapshot["fastLeader"])
        self.assertIsNone(snapshot["shared"])
        self.assertEqual(commands, [])

    def test_first_focused_social_sample_is_not_a_premature_fast_follow(self):
        bridge, commands = self.bridge(docked=False)
        snapshot = bridge.fast_follow(sample(focus="social", discord_x=780))
        self.assertIsNone(snapshot["fastLeader"])
        self.assertEqual(commands, [])

    def test_after_dock_discord_may_lead_social_move(self):
        bridge, commands = self.bridge(docked=True)
        result = bridge.fast_follow(sample(discord_x=480, discord_y=180))
        self.assertEqual(result["fastLeader"], "discord")
        self.assertEqual(result["shared"]["x"], 369)  # 480 - 110 - 1
        self.assertEqual(result["shared"]["y"], 179)
        self.assertEqual([cmd["target"] for cmd in commands], ["social"])
        self.assertEqual(commands[0]["x"], 369)

    def test_after_dock_social_may_lead_discord_move(self):
        bridge, commands = self.bridge(docked=True)
        result = bridge.fast_follow(sample(focus="social", social_x=425))
        self.assertEqual(result["fastLeader"], "social")
        self.assertEqual([cmd["target"] for cmd in commands], ["discord"])
        self.assertEqual(commands[0]["x"], 536)  # 425 + 110 + 1
        self.assertEqual(commands[0]["y"], 51)

    def test_aligned_pair_does_not_create_new_sway_moves(self):
        bridge, commands = self.bridge(docked=True)
        out = bridge.fast_follow(sample())
        self.assertEqual(out["fastLeader"], "discord")
        self.assertEqual(commands, [])

    def test_inactive_or_unready_discord_cannot_lead(self):
        for name in ("discord_selected", "discord_ready", "discord_docked"):
            bridge, commands = self.bridge(docked=True)
            setattr(bridge, name, False)
            with self.subTest(turned_off=name):
                result = bridge.fast_follow(sample(discord_x=800))
                self.assertIsNone(result["fastLeader"])
                self.assertEqual(commands, [])

    def test_helper_mode_fails_closed_without_docked_flag(self):
        bridge, commands = self.bridge(docked=False)
        events = [
            {"op": "mode", "discordSelected": True,
             "discordReady": True},  # Older or stale messages cannot arm.
            {"op": "sample"},
            {"op": "mode", "discordSelected": True,
             "discordReady": True, "discordDocked": True},
            {"op": "mode", "discordSelected": False,
             "discordReady": True, "discordDocked": True},
            {"op": "stop"},
        ]
        stream = io.StringIO("\n".join(json.dumps(item) for item in events) + "\n")
        captured = []
        with patch.object(geometry.sys, "stdin", stream):
            # Verify the actual JSON mode parser, capturing state at each mode.
            original_event = bridge.sample_event.set
            def record():
                captured.append(bridge.discord_docked)
                original_event()
            bridge.sample_event.set = record
            bridge.stdin_loop()
        self.assertFalse(bridge.discord_selected)
        self.assertFalse(bridge.discord_docked)
        self.assertEqual(captured, [False])

    def test_x_follow_is_unchanged_by_discord_docking_gate(self):
        bridge = geometry.Bridge(0.1)
        bridge.x_selected = True
        bridge.x_ready = True
        bridge.browser_site = "x"
        bridge.discord_docked = False
        commands = []
        bridge.queue_sync = commands.append
        snapshot = sample(focus="social", social_x=345)
        snapshot["x"] = snapshot.pop("discord")
        result = bridge.fast_follow(snapshot)
        self.assertEqual(result["fastLeader"], "social")
        self.assertEqual(commands[0]["target"], "x")

    def test_source_requires_confirmed_dock_and_resets_on_every_entry(self):
        text = SOCIAL.read_text(encoding="utf-8")
        self.assertIn("property bool discordDocked: false", text)
        self.assertIn("onDiscordDockedChanged: updateGeometryHelperMode()", text)
        self.assertIn("discordDocked: discordDocked,", text)
        self.assertIn("function initialDiscordDockAligned(rect)", text)
        self.assertIn("function initialSocialDockAligned(rect)", text)
        self.assertIn("if (socialRect && initialSocialDockAligned(socialRect))", text)
        activation = text.split("    function activateApp(index, retainSelectorFocus)", 1)[1]
        self.assertLess(activation.index("discordDocked = false;"),
                        activation.index("activeAppIndex = index;"))
        self.assertIn("if (!discordDocked) {", text)
        self.assertIn("if (initialDiscordDockAligned(discordRect)) {", text)
        self.assertIn("discordDocked = true;", text)
        self.assertIn("if (!socialReady || !discordRect)", text)
        show = text.split("    function showDiscord() {", 1)[1].split(
            "    function hideDiscord()", 1)[0]
        hide = text.split("    function hideDiscord() {", 1)[1].split(
            "    // ============================================================", 1)[0]
        for method in (show, hide):
            self.assertIn("discordReady = false;", method)
            self.assertIn("discordDocked = false;", method)
        self.assertIn('Quickshell.shellPath("widgets/messanger/DiscordGeometry.py")', text)
        self.assertNotIn("DiscordBackingW", text)

    def test_social_focus_retry_uses_real_readiness_and_repeats(self):
        src = SOCIAL.read_text(encoding="utf-8")
        chunk = src.split("id: socialFocusDelay", 1)[1].split(
            "id: discordStartupFallback", 1)[0]
        self.assertIn("repeat: true", chunk)
        self.assertIn("messagingWindow.socialReady || attempts >= 6", chunk)
        self.assertNotIn("socailReady", src)
        self.assertIn("syncSocialGeometry(!messagingWindow.externalSelected)", chunk)
        self.assertIn("if (!messagingWindow.socialReady)", src)

    def test_discord_overlay_does_not_paint_above_vesktop(self):
        # The Sway region mask controls clicks, not pixels. A full-window
        # painted frame + hidden-content-only Discord mode tinted the actual
        # Vesktop client in the operator's desktop screenshot.
        src = SOCIAL.read_text(encoding="utf-8")
        frame = src.split("    WindowPanelFrame {", 1)[1].split(
            "        // KEYBOARD CONTROLLER", 1)[0]
        self.assertIn(
            "fillOpacity: messagingWindow.discordSelected ? 0.0 : 0.20", frame
        )
        self.assertIn("borderVisible: false", frame)
        self.assertIn("glowVisible: false", frame)

        contact = src.split("        ContactList {", 1)[1].split(
            "        // IN-MENU TELEGRAM ACCOUNT CONNECTION", 1)[0]
        feed = src.split("        ChatFeed {", 1)[1]
        for name, body in (("contact", contact), ("feed", feed)):
            with self.subTest(name=name):
                self.assertIn("visible: messagingWindow.menuOpen && !messagingWindow.discordSelected", body)
                self.assertIn("discordMode: messagingWindow.externalSelected", body)

        # The narrow selector should still paint above the provider desktop.
        selector = src.split("        AppSelector {", 1)[1].split(
            "        // CONTACT LIST", 1)[0]
        self.assertIn("id: appSelector", selector)
        self.assertIn("z: 3", selector)
        self.assertNotIn("!messagingWindow.discordSelected", selector)
        self.assertIn("width: messagingWindow.menuOpen ? (messagingWindow.externalSelected ? messagingWindow.appSelectorWidth : socialWindow.width) : 0", src)
        self.assertNotIn("DiscordBackingW {", src)

    def test_backing_remains_unused(self):
        self.assertTrue(BACKING.exists())
        source = SOCIAL.read_text()
        self.assertNotIn("DiscordBackingW {", source)


if __name__ == "__main__":
    main()
