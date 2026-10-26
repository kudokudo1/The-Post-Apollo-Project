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

    def test_browser_startup_is_not_allowed_to_resize_social(self):
        bridge = geometry.Bridge(0.1)
        bridge.x_selected = True
        bridge.x_ready = True
        bridge.browser_site = "x"
        commands = []
        bridge.queue_sync = commands.append
        snapshot = sample(focus="discord", discord_x=780, discord_y=450)
        snapshot["x"] = snapshot.pop("discord")

        # A focused just-mapped app must not lead before a verified dock.
        self.assertFalse(bridge.x_docked)
        result = bridge.fast_follow(snapshot)
        self.assertIsNone(result["fastLeader"])
        self.assertIsNone(result["shared"])
        self.assertEqual(commands, [])

        # Once docking is confirmed, the *same* user-driven geometry change
        # is adopted in both directions, preserving Mod-move/resize.
        bridge.x_docked = True
        result = bridge.fast_follow(snapshot)
        self.assertEqual(result["fastLeader"], "x")
        self.assertEqual(commands[0]["target"], "social")
        commands.clear()
        snapshot["x"]["rect"] = {"x": 211, "y": 51,
                                 "width": 1098, "height": 698}
        snapshot["social"]["rect"]["x"] = 345
        snapshot["social"]["focused"] = True
        snapshot["x"]["focused"] = False
        result = bridge.fast_follow(snapshot)
        self.assertEqual(result["fastLeader"], "social")
        self.assertEqual(commands[0]["target"], "x")

    def test_browser_docking_mode_requires_selected_ready_and_verified(self):
        bridge = geometry.Bridge(0.1)
        state = {
            "op": "mode", "xSelected": True, "xReady": True,
            "xDocked": False, "browserSite": "x",
        }
        modes = [
            state, {"op": "sample"},
            {**state, "xDocked": True}, {"op": "sample"},
            {**state, "xReady": False, "xDocked": True}, {"op": "sample"},
            {**state, "xSelected": False, "xDocked": True}, {"op": "sample"},
            {"op": "stop"},
        ]
        stream = io.StringIO("\n".join(json.dumps(x) for x in modes) + "\n")
        captured = []
        with patch.object(geometry.sys, "stdin", stream):
            original = bridge.sample_event.set
            def capture():
                captured.append((bridge.x_selected, bridge.x_ready,
                                 bridge.x_docked))
                original()
            bridge.sample_event.set = capture
            bridge.stdin_loop()
        self.assertFalse(bridge.x_docked)
        self.assertEqual(captured, [
            (True, True, False), (True, True, True),
            (True, False, False), (False, True, False),
        ])
        # A stale xDocked=True must be rejected as soon as readiness or
        # selection changes, without touching the live Sway resize path.
        self.assertIn("self.x_docked = (", GEOMETRY.read_text())
        self.assertIn("and self.x_selected and self.x_ready", GEOMETRY.read_text())

    def test_source_requires_confirmed_dock_and_resets_on_every_entry(self):
        text = SOCIAL.read_text(encoding="utf-8")
        self.assertIn("property bool discordDocked: false", text)
        self.assertIn("property bool xDocked: false", text)
        self.assertIn("onXDockedChanged: updateGeometryHelperMode()", text)
        self.assertIn("xDocked: xDocked,", text)
        self.assertIn("if (!xDocked) {", text)
        self.assertIn("if (now < ignoreXGeometryUntil)", text)
        self.assertIn("if (now < ignoreDiscordGeometryUntil)", text)
        self.assertIn("if (initialDiscordDockAligned(xRect))", text)
        self.assertIn("xDocked = true;", text)
        self.assertIn("xDocked = false;", text)
        self.assertIn("onDiscordDockedChanged: {", text)
        self.assertIn("updateGeometryHelperMode();", text)
        self.assertIn("if (discordDocked && menuOpen && discordSelected)", text)
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
        self.assertIn("DiscordBackingW {", text)

    def test_social_focus_retry_uses_real_readiness_and_repeats(self):
        src = SOCIAL.read_text(encoding="utf-8")
        chunk = src.split("id: socialFocusDelay", 1)[1].split(
            "id: discordStartupFallback", 1)[0]
        self.assertIn("repeat: true", chunk)
        self.assertIn("messagingWindow.socialReady || attempts >= 6", chunk)
        self.assertNotIn("socailReady", src)
        self.assertIn("syncSocialGeometry(!messagingWindow.externalSelected)", chunk)
        self.assertIn("if (!messagingWindow.socialReady)", src)

    def test_discord_shells_remain_empty_but_exist_above_backing(self):
        # The Social FloatingWindow still contains the component instances,
        # yet they must paint no translucent surface/border above Vesktop.
        social = SOCIAL.read_text(encoding="utf-8")
        contact = (ROOT / "widgets/messanger/ContactList.qml").read_text()
        feed = (ROOT / "components/ConversationFeed.qml").read_text()
        self.assertIn("fillOpacity: messagingWindow.discordSelected ? 0.0 : 0.20", social)
        self.assertIn("id: contactList", social)
        self.assertIn("id: chatFeed", social)
        self.assertIn("discordVisualBehind: messagingWindow.discordSelected", social)
        self.assertIn("visible: messagingWindow.menuOpen && !providerAccessPanel.visible", social)
        self.assertIn("visible: messagingWindow.menuOpen && !telegramConnectPanel.visible", social)
        self.assertIn("discordMode: messagingWindow.externalSelected", social)
        self.assertIn('color: discordVisualBehind ? "transparent"', contact)
        self.assertIn("border.width: discordVisualBehind ? 0 : 1", contact)
        self.assertIn("opacity: chatFeed.discordVisualBehind ? 0.0 : 0.85", feed)
        self.assertIn("visible: !chatFeed.discordVisualBehind", feed)
        self.assertIn("visible: !contactRoot.discordMode", contact)
        self.assertIn("visible: !chatFeed.discordMode", feed)
        self.assertIn("z: 3", social)

    def test_discord_backing_restored_on_bottom_layer_and_screen(self):
        social = SOCIAL.read_text(encoding="utf-8")
        backing = BACKING.read_text(encoding="utf-8")
        self.assertIn("DiscordBackingW {", social)
        self.assertIn("hostSocial: messagingWindow", social)
        self.assertIn("property var hostSocial: null", backing)
        self.assertIn("WlrLayershell.layer: WlrLayer.Bottom", backing)
        self.assertIn("discordBackingWindow", backing)
        self.assertIn("hostSocial.discordX", backing)
        self.assertIn("hostSocial.discordWidth", backing)
        self.assertIn("hostSocial.menuOpen", backing)
        self.assertIn("hostSocial.discordSelected", backing)
        self.assertIn("width: 0", backing)
        self.assertIn("height: 0", backing)
        self.assertIn("opacity: 0.85", backing)

    def test_discord_sync_reasserts_floating_and_borderless_even_after_setup(self):
        # Screenshot regression: after PR #799 the visible "Vesktop"
        # decoration remains because setup=False may be sent before a
        # successful compositor border update. Every Discord resize/move must
        # still enforce the borderless Sway window.
        for setup in (False, True):
            with self.subTest(setup=setup):
                cmd = geometry.build_sync_command({
                    "target": "discord",
                    "x": 211, "y": 51, "width": 1098, "height": 698,
                    "setup": setup, "focus": False,
                })
                self.assertIn('[app_id="vesktop"] floating enable', cmd)
                self.assertIn('[app_id="vesktop"] border none', cmd)
                self.assertLess(cmd.index("floating enable"), cmd.index("border none"))
                self.assertLess(cmd.index("border none"), cmd.index("resize set"))
                self.assertNotIn(" focus", cmd)

        # This must remain Discord-only: browser and Social commands retain
        # their previous one-time setup behavior and fast-follow performance.
        for target in ("social", "x"):
            cmd = geometry.build_sync_command({
                "target": target, "x": 1, "y": 2,
                "width": 300, "height": 400,
                "setup": False,
            })
            self.assertNotIn("floating enable", cmd)
            self.assertNotIn("border none", cmd)

    def test_discord_launch_requests_real_sway_floating_and_raise(self):
        social = SOCIAL.read_text(encoding="utf-8")
        launch = social.split("    function showDiscord() {", 1)[1].split(
            "    function hideDiscord()", 1)[0]
        float_cmd = 'swaymsg \'[app_id=\\\"vesktop\\\"] floating enable\''
        show_cmd = 'swaymsg \'[app_id=\\\"vesktop\\\"] scratchpad show\''
        focus_cmd = 'swaymsg \'[app_id=\\\"vesktop\\\"] focus\''
        border_cmd = float_cmd.replace("floating enable", "border none")
        self.assertGreaterEqual(launch.count(float_cmd), 2)
        self.assertGreaterEqual(launch.count(border_cmd), 2)
        self.assertLess(launch.index(float_cmd), launch.index(border_cmd))
        self.assertIn(show_cmd, launch)
        self.assertLess(launch.index(show_cmd), launch.rindex(border_cmd))
        self.assertLess(launch.rindex(border_cmd), launch.index(focus_cmd))
        self.assertIn(focus_cmd, launch)
        self.assertLess(launch.index(float_cmd), launch.index(show_cmd))
        self.assertLess(launch.index(show_cmd), launch.index(focus_cmd))
        self.assertIn("if (discordDocked && menuOpen && discordSelected)", social)
        self.assertIn("discordRaiseDelay.restart();", social)

        helper = GEOMETRY.read_text()
        self.assertIn("""'[app_id="vesktop"] floating enable; '""", helper)
        self.assertIn("""'[app_id="vesktop"] focus'""", helper)
        self.assertIn("""'[app_id="vesktop"] move absolute position '""", helper)


if __name__ == "__main__":
    main()
