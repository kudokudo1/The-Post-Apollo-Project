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
from unittest.mock import Mock, patch

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
            "visible": True,
            "conId": 4242,
        },
    }


class DiscordDockingTests(TestCase):
    def test_discord_tray_activation_routes_to_social_not_native_vesktop(self):
        tray = (ROOT / "modules/Tray.qml").read_text(encoding="utf-8")
        social = SOCIAL.read_text(encoding="utf-8")
        bridge = (ROOT / "services/social/SocialTrayBridge.qml").read_text(
            encoding="utf-8"
        )
        qmldir = (ROOT / "services/social/qmldir").read_text(encoding="utf-8")

        # Tray and Social are already in one Quickshell instance. A detached
        # "qs ipc call" may select the wrong instance or fail silently and
        # must not be involved in handling the local icon click.
        self.assertIn("pragma Singleton", bridge)
        self.assertIn("Singleton {", bridge)
        self.assertIn("signal discordActivationRequested()", bridge)
        self.assertIn("function requestDiscordActivation()", bridge)
        self.assertIn("discordActivationRequested();", bridge)
        self.assertIn(
            "singleton SocialTrayBridge 1.0 SocialTrayBridge.qml", qmldir
        )
        self.assertIn("import qs.services.social", tray)
        self.assertIn("import qs.services.social", social)
        self.assertIn("function isDiscordTrayItem(item)", tray)
        self.assertIn('id === "dev.vencord.vesktop"', tray)
        self.assertIn('title === "vesktop"', tray)
        self.assertIn('title === "discord"', tray)
        self.assertIn('tooltip === "vesktop"', tray)
        self.assertIn("SocialTrayBridge.requestDiscordActivation();", tray)
        self.assertNotIn('["qs", "ipc", "call", "messaging"', tray)
        self.assertIn("trayDock.isDiscordTrayItem(trayButton.modelData)", tray)
        self.assertIn("trayDock.openDiscordFromTray();", tray)
        # Unrelated applications keep their own native tray activation.
        self.assertIn("trayButton.modelData.activate();", tray)
        self.assertIn("target: SocialTrayBridge", social)
        self.assertIn("function onDiscordActivationRequested()", social)
        self.assertIn("messagingWindow.openDiscordFromTray();", social)

    def test_tray_open_uses_existing_social_menu_lifecycle(self):
        src = SOCIAL.read_text(encoding="utf-8")
        opening = src.split("    function openDiscordFromTray() {", 1)[1].split(
            "    function showDiscord() {", 1
        )[0]
        # Opening a hidden menu must not invoke a native Vesktop tray action,
        # and a visible menu switches to Discord without closing the widget.
        self.assertIn("if (!menuOpen)", opening)
        self.assertIn("menuOpen = true;", opening)
        self.assertIn("Qt.callLater(function ()", opening)
        self.assertIn("messagingWindow.activateApp(1);", opening)
        self.assertIn("function openDiscordFromTray(): void", src)

    def test_discord_launch_waits_for_verified_social_mapping(self):
        src = SOCIAL.read_text(encoding="utf-8")
        show = src.split("    function showDiscord() {", 1)[1].split(
            "    function hideDiscord()", 1
        )[0]
        self.assertIn("onSocialReadyChanged: {", src)
        self.assertIn(
            "if (socialReady && menuOpen && discordSelected && !discordReady)", src
        )
        self.assertLess(
            show.index("if (!socialReady)"), show.index("discordLaunchProcess.exec(")
        )
        self.assertLess(
            show.index("helperShowDiscord("), show.index("discordLaunchProcess.exec(")
        )

    def test_hiding_discord_disarms_stale_follow_before_scratchpad(self):
        bridge = geometry.Bridge(0.1)
        bridge.discord_ready = True
        bridge.discord_docked = True
        bridge.discord_con_id = 4242
        bridge.discord_visible = True
        bridge.pending_sync = {
            "discord": {"target": "discord", "width": 330},
            "social": {"target": "social", "width": 441},
            "x": {"target": "x", "width": 1000},
        }
        with patch.object(geometry.sys, "stdin", io.StringIO('{"op":"hideDiscord"}\n')):
            with patch.object(bridge, "queue_command") as send:
                bridge.stdin_loop()
                send.assert_called_once_with('[con_id="4242"] move scratchpad')

        self.assertFalse(bridge.discord_show_requested)
        self.assertFalse(bridge.discord_ready)
        self.assertFalse(bridge.discord_docked)
        self.assertEqual(bridge.pending_sync, {"x": {"target": "x", "width": 1000}})

    def test_app_rail_detects_hidden_browser_without_geometry_authority(self):
        # The UI may show a magenta background-open label for an existing
        # managed browser in Sway scratchpad. Geometry must remain hidden from
        # the legacy helper until its active browser handoff.
        tree = {
            "id": 1, "visible": True,
            "rect": {"x": 0, "y": 0, "width": 1920, "height": 1080},
            "nodes": [
                {
                    "id": 4001, "name": "X",
                    "window_properties": {"class": "post-apollo-x"},
                    "visible": False, "focused": False,
                    "rect": {"x": 300, "y": 100, "width": 700, "height": 600},
                    "nodes": [], "floating_nodes": [],
                },
                {
                    "id": 4002, "name": "Reddit",
                    "window_properties": {"class": "post-apollo-reddit"},
                    "visible": True, "focused": False,
                    "rect": {"x": 300, "y": 100, "width": 700, "height": 600},
                    "nodes": [], "floating_nodes": [],
                },
                {
                    "id": 4003, "name": "Unrelated Chrome",
                    "window_properties": {"class": "post-apollo-x-clone"},
                    "visible": True, "focused": False,
                    "rect": {"x": 300, "y": 100, "width": 700, "height": 600},
                    "nodes": [], "floating_nodes": [],
                },
                {
                    "id": 0, "name": "Unmapped",
                    "window_properties": {"class": "post-apollo-instagram"},
                    "visible": True, "focused": False,
                    "rect": {"x": 300, "y": 100, "width": 700, "height": 600},
                    "nodes": [], "floating_nodes": [],
                },
            ],
            "floating_nodes": [],
        }
        snapshot = geometry.snapshot_from_tree(tree)
        self.assertEqual(snapshot["openBrowserSites"], ["reddit", "x"])
        self.assertIsNone(snapshot["x"])  # no hidden legacy geometry authority
        self.assertEqual(snapshot["reddit"]["rect"]["width"], 700)

        # A closed background provider disappears on the next observed Sway
        # snapshot, rather than remaining highlighted from click history.
        tree["nodes"] = tree["nodes"][1:]
        self.assertEqual(
            geometry.snapshot_from_tree(tree)["openBrowserSites"], ["reddit"]
        )

    def test_background_browser_observation_respects_identity_scope(self):
        rect = {"x": 0, "y": 0, "width": 900, "height": 700}
        def scoped_node(cid, cls):
            return {
                "id": cid, "name": cls,
                "window_properties": {"class": cls},
                "visible": False, "focused": False, "rect": rect,
                "nodes": [], "floating_nodes": [],
            }
        tree = {
            "id": 1, "visible": True, "rect": rect,
            "nodes": [
                scoped_node(11, "post-apollo-x-identity-1"),
                scoped_node(12, "post-apollo-reddit-identity-2"),
                scoped_node(13, "post-apollo-instagram"),
                scoped_node(14, "post-apollo-x-identity-invalid"),
            ],
            "floating_nodes": [],
        }
        self.assertEqual(
            geometry.snapshot_from_tree(tree, "identity-1")["openBrowserSites"],
            ["x"],
        )
        self.assertEqual(
            geometry.snapshot_from_tree(tree, "identity-2")["openBrowserSites"],
            ["reddit"],
        )
        self.assertEqual(
            geometry.snapshot_from_tree(tree)["openBrowserSites"], ["instagram"]
        )

    def test_app_rail_active_and_background_color_contract(self):
        selector = (ROOT / "widgets/messanger/AppSelector.qml").read_text(
            encoding="utf-8")
        social = SOCIAL.read_text(encoding="utf-8")
        self.assertIn("property int activeAppIndex: -1", selector)
        self.assertIn("property var backgroundOpenServiceIds: []", selector)
        self.assertIn(
            "appSelector.activeAppIndex === buttonContainer.modelData.serviceIndex",
            selector,
        )
        self.assertIn(
            "appSelector.backgroundOpenServiceIds.indexOf(", selector,
        )
        self.assertIn("readonly property bool isOpenStyled: isActive || isBackgroundOpen", selector)
        self.assertIn("color: appButton.isActive ? Colors.yellow", selector)
        self.assertIn(": appButton.isBackgroundOpen ? Colors.dark", selector)
        self.assertIn("color: appButton.isOpenStyled ? Colors.magenta", selector)
        self.assertIn(
            "layer.enabled: appButton.isOpenStyled", selector,
        )
        self.assertIn(
            "color: appButton.isOpenStyled ? Colors.magenta : Colors.orange",
            selector,
        )
        self.assertIn("opacity: appButton.isActive ? 0.55", selector)
        self.assertIn("opacity: appButton.isActive ? 0.12", selector)
        self.assertEqual(selector.count("appButton.isBackgroundOpen ? 0.0"), 2)
        # Hover and keyboard selection only preview. They cannot paint the
        # yellow active state or falsely claim a different displayed app.
        self.assertIn("appSelector.selectedIndex = buttonContainer.modelData.serviceIndex;", selector)
        self.assertNotIn(
            "appButton.isSelected ? Colors.yellow", selector,
        )
        self.assertIn("activeAppIndex: messagingWindow.activeAppIndex", social)
        self.assertIn(
            "backgroundOpenServiceIds: messagingWindow.openProviderServiceIds",
            social,
        )
        self.assertIn("function updateOpenProviderServiceIds(payload)", social)
        self.assertIn("updateOpenProviderServiceIds(payload);", social)
        self.assertIn("present.every(function(id, i)", social)
        self.assertIn('sites[i] === "whatsappweb" ? "whatsapp"', social)
        self.assertIn('sites[i] === "messengerweb" ? "messenger"', social)
        self.assertIn('sites[i] === "linechrome" ? "line"', social)
        # No new app launching, authentication inference, or geometry side
        # effects are added to presence observation.
        helper = GEOMETRY.read_text(encoding="utf-8")
        self.assertIn('"openBrowserSites": sorted(observed_browser_sites)', helper)
        self.assertIn("expected_browser_classes.get(window_class)", helper)

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
        self.assertIn("property int discordWindowConId: 0", text)
        self.assertIn("discordConId !== discordWindowConId", text)
        self.assertIn("discordWindowConId = discordConId;", text)
        self.assertNotIn("discordStartupFallback", text)
        self.assertIn("if (initialDiscordDockAligned(xRect))", text)
        self.assertIn("xDocked = true;", text)
        self.assertIn("xDocked = false;", text)
        self.assertIn("onDiscordDockedChanged: {", text)
        self.assertIn("updateGeometryHelperMode();", text)
        self.assertIn("if (!discordDocked || !menuOpen || !discordSelected)", text)
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
        self.assertNotIn("DiscordBackingW {", text)
        self.assertIn("helperShowDiscord(", text)
        self.assertIn("helperHideDiscord()", text)
        self.assertNotIn('[app_id=\\\"vesktop\\\"]', text)

    def test_shared_external_geometry_round_trip_is_app_agnostic(self):
        bridge = geometry.Bridge(0.1)
        resized_external = {
            "x": 480,
            "y": 180,
            "width": 1260,
            "height": 820,
        }

        shared = bridge.shared_from_discord(resized_external)
        next_external = bridge.discord_from_shared(shared)

        # Discord and every browser-backed Social app use this same external
        # slot conversion. A resize learned from one app therefore becomes the
        # exact opening geometry of the next selected app.
        self.assertEqual(next_external, resized_external)

    def test_social_reopen_preserves_runtime_shared_geometry(self):
        src = SOCIAL.read_text(encoding="utf-8")
        open_block = src.split("    onMenuOpenChanged: {", 1)[1]

        self.assertIn(
            "sharedPanelX/Y/Width/Height are the canonical Social viewport",
            open_block,
        )
        self.assertNotIn("sharedPanelWidth = defaultPanelWidth;", open_block)
        self.assertNotIn("sharedPanelHeight = defaultPanelHeight;", open_block)
        self.assertNotIn("sharedPanelX = Math.round(defaultPanelX);", open_block)
        self.assertNotIn("sharedPanelY = Math.round(defaultPanelY);", open_block)

        # Defaults still exist for the first runtime initialization only.
        self.assertIn("property int sharedPanelWidth: defaultPanelWidth", src)
        self.assertIn("property int sharedPanelHeight: defaultPanelHeight", src)
        self.assertIn("sharedPanelX = Math.round(defaultPanelX);", src)
        self.assertIn("sharedPanelY = Math.round(defaultPanelY);", src)
        self.assertIn("function initializeSharedPosition()", src)

    def test_social_focus_retry_uses_real_readiness_and_repeats(self):
        src = SOCIAL.read_text(encoding="utf-8")
        chunk = src.split("id: socialFocusDelay", 1)[1].split(
            "id: xRaiseDelay", 1
        )[0]
        self.assertIn("repeat: true", chunk)
        self.assertIn("messagingWindow.socialReady || attempts >= 6", chunk)
        self.assertNotIn("socailReady", src)
        self.assertIn("syncSocialGeometry(!messagingWindow.externalSelected)", chunk)
        # Splash promotion used to supply this extra readiness fallback.
        # It is deliberately gone: only the Social positioning retry remains.
        self.assertNotIn("discordStartupFallback", src)

    def test_discord_uses_normal_empty_panes_without_backing_window(self):
        social = SOCIAL.read_text(encoding="utf-8")
        contact = (ROOT / "widgets/messanger/ContactList.qml").read_text()
        feed = (ROOT / "components/ConversationFeed.qml").read_text()

        # Discord is the same external-window model as X/browser apps: native
        # panes remain as the normal visual surface underneath, while
        # discordMode hides only their contents.
        self.assertIn("fillOpacity: 0.20", social)
        self.assertIn("id: contactList", social)
        self.assertIn("id: chatFeed", social)
        self.assertIn("discordMode: messagingWindow.externalSelected", social)
        self.assertNotIn("discordVisualBehind", social)
        self.assertNotIn("DiscordBackingW {", social)
        self.assertFalse(BACKING.exists())

        self.assertNotIn("discordVisualBehind", contact)
        self.assertIn(
            "color: Qt.rgba(Colors.black.r, Colors.black.g, Colors.black.b, 0.85)",
            contact,
        )
        self.assertIn("border.width: 1", contact)
        self.assertIn("visible: !contactRoot.discordMode", contact)

        self.assertNotIn("discordVisualBehind", feed)
        self.assertIn("opacity: 0.85", feed)
        self.assertIn("visible: true", feed)
        self.assertIn("visible: !chatFeed.discordMode", feed)

    def test_vesktop_discovery_handles_wayland_xwayland_and_scratchpad(self):
        variants = (
            {"id": 101, "app_id": "vesktop", "window_properties": {}},
            {"id": 102, "app_id": "dev.vencord.vesktop", "window_properties": {}},
            {"id": 103, "app_id": "dev.vencord.Vesktop", "window_properties": {}},
            {
                "id": 104,
                "app_id": None,
                "window_properties": {"class": "Vesktop", "instance": "vesktop"},
            },
            {
                "id": 105,
                "app_id": None,
                "sandbox_app_id": "dev.vencord.Vesktop",
                "window_properties": {},
            },
        )
        for node in variants:
            with self.subTest(node=node):
                candidate = {
                    **node,
                    "name": "Vesktop",
                    "visible": False,
                    "focused": False,
                    "rect": {"x": 700, "y": 300, "width": 300, "height": 350},
                    "nodes": [],
                    "floating_nodes": [],
                }
                tree = {
                    "id": 1,
                    "visible": True,
                    "rect": {"x": 0, "y": 0, "width": 1920, "height": 1080},
                    "nodes": [candidate],
                    "floating_nodes": [],
                }
                snapshot = geometry.snapshot_from_tree(tree)
                self.assertEqual(snapshot["discord"]["conId"], node["id"])
                self.assertFalse(snapshot["discord"]["visible"])
                self.assertEqual(snapshot["discord"]["kind"], "splash")

    def test_small_real_discord_window_is_not_misclassified_as_splash(self):
        tree = {
            "id": 1,
            "visible": True,
            "rect": {"x": 0, "y": 0, "width": 1920, "height": 1080},
            "nodes": [{
                "id": 106,
                "name": "Friends",
                "app_id": "dev.vencord.vesktop",
                "visible": True,
                "focused": True,
                "rect": {"x": 700, "y": 300, "width": 360, "height": 350},
                "nodes": [],
                "floating_nodes": [],
            }],
            "floating_nodes": [],
        }
        snapshot = geometry.snapshot_from_tree(tree)
        self.assertEqual(snapshot["discord"]["kind"], "main")
        self.assertEqual(snapshot["discord"]["name"], "Friends")

    def test_discord_criteria_requires_discovered_container_id(self):
        self.assertEqual(
            geometry.sway_criteria("discord", 4242),
            '[con_id="4242"]',
        )
        with self.assertRaises(ValueError):
            geometry.sway_criteria("discord")

    def test_upstream_splash_is_exact_size_and_never_promoted_by_timeout(self):
        social = SOCIAL.read_text(encoding="utf-8")
        helper = GEOMETRY.read_text(encoding="utf-8")
        self.assertIn("property int vesktopSplashWidth: 300", social)
        self.assertIn("property int vesktopSplashHeight: 350", social)
        self.assertIn('String(node.kind || "") === "splash"', social)
        self.assertIn("helperCenterDiscord(x, y, vesktopSplashWidth, vesktopSplashHeight)", social)
        self.assertNotIn("discordStartupFallback", social)
        self.assertIn("VESKTOP_SPLASH_WIDTH = 300", helper)
        self.assertIn("VESKTOP_SPLASH_HEIGHT = 350", helper)
        self.assertIn("VESKTOP_SPLASH_TOLERANCE = 80", helper)
        self.assertIn("splash_sized and splash_named", helper)

        cmd = geometry.build_sync_command({
            "target": "discord", "conId": 55,
            "x": 10, "y": 20, "width": 300, "height": 350,
            "setup": False, "focus": False,
        })
        self.assertIn('[con_id="55"] resize set width 300 px height 350 px', cmd)

    def test_splash_to_main_container_change_disarms_geometry_authority(self):
        bridge, _ = self.bridge(docked=True)
        bridge.discord_con_id = 100
        bridge.discord_ready = True
        bridge.discord_docked = True

        main = {
            "social": sample()["social"],
            "discord": {
                "rect": {"x": 900, "y": 600, "width": 980, "height": 520},
                "focused": True,
                "visible": True,
                "conId": 200,
                "kind": "main",
            },
        }
        bridge.poll_ipc.request = Mock(return_value={
            "id": 1,
            "visible": True,
            "focused": False,
            "rect": {"x": 0, "y": 0, "width": 1920, "height": 1080},
            "nodes": [
                {
                    "id": 99,
                    "name": "QS_SOCIAL_MENU",
                    "visible": True,
                    "focused": False,
                    "rect": main["social"]["rect"],
                    "nodes": [], "floating_nodes": [],
                },
                {
                    "id": 200,
                    "name": "Vesktop",
                    "app_id": "dev.vencord.vesktop",
                    "visible": True,
                    "focused": True,
                    "rect": main["discord"]["rect"],
                    "nodes": [], "floating_nodes": [],
                },
            ],
            "floating_nodes": [],
        })
        bridge.emit_snapshot(force=True)
        self.assertEqual(bridge.discord_con_id, 200)
        self.assertFalse(bridge.discord_ready)
        self.assertFalse(bridge.discord_docked)

    def test_restarted_helper_restores_hidden_sway_scratchpad_main(self):
        # Quickshell restarts, but Vesktop remains hidden in Sway scratchpad.
        # The fresh helper has never seen this main window visible.
        bridge = geometry.Bridge(0.1)
        bridge.discord_show_requested = True
        bridge.discord_show_focus = True
        self.assertEqual(bridge.discord_main_seen_visible, set())
        tree = {
            "id": 1, "visible": True,
            "rect": {"x": 0, "y": 0, "width": 1920, "height": 1080},
            "nodes": [
                {
                    "id": 99, "name": "QS_SOCIAL_MENU", "visible": True,
                    "focused": False,
                    "rect": {"x": 100, "y": 50, "width": 1210, "height": 700},
                    "nodes": [], "floating_nodes": [],
                },
                {
                    "id": 7001, "name": "Friends",
                    "app_id": "dev.vencord.vesktop",
                    "scratchpad_state": "fresh", "visible": False,
                    "focused": False,
                    "rect": {"x": 480, "y": 240, "width": 900, "height": 600},
                    "nodes": [], "floating_nodes": [],
                },
            ],
            "floating_nodes": [],
        }
        snap = geometry.snapshot_from_tree(tree)
        self.assertEqual(snap["discord"]["kind"], "main")
        self.assertEqual(snap["discord"]["scratchpadState"], "fresh")
        bridge.poll_ipc.request = Mock(return_value=tree)
        commands, dock_commands = [], []
        bridge.queue_command = commands.append
        bridge.queue_sync = dock_commands.append
        bridge.emit_snapshot(force=True)
        bridge.emit_snapshot(force=True)
        self.assertEqual(commands, ['[con_id="7001"] scratchpad show'])
        self.assertEqual(dock_commands, [])
        self.assertTrue(bridge.discord_show_requested)
        self.assertNotIn(7001, bridge.discord_main_seen_visible)
        self.assertFalse(bridge.discord_docked)

        # Only once Sway sees that same main as visible may the helper dock
        # into the known Social rectangle and consume the open request.
        tree["nodes"][1]["visible"] = True
        bridge.emit_snapshot(force=True)
        self.assertEqual(dock_commands, [{
            "op": "sync", "target": "discord", "x": 211, "y": 51,
            "width": 1098, "height": 698, "focus": True, "setup": True,
        }])
        self.assertFalse(bridge.discord_show_requested)
        self.assertIn(7001, bridge.discord_main_seen_visible)
        self.assertEqual(commands, ['[con_id="7001"] scratchpad show'])

    def test_restart_never_forces_cold_main_or_splash_visible(self):
        for title, width, height, state in (
            ("Friends", 1280, 720, "none"),
            ("Vesktop", 300, 350, "fresh"),
            ("Friends", 1280, 720, "unknown"),
        ):
            with self.subTest(title=title, state=state):
                bridge = geometry.Bridge(0.1)
                bridge.discord_show_requested = True
                bridge.poll_ipc.request = Mock(return_value={
                    "id": 1, "visible": True,
                    "rect": {"x": 0, "y": 0, "width": 1920, "height": 1080},
                    "nodes": [{
                        "id": 7101, "name": title,
                        "app_id": "dev.vencord.vesktop",
                        "scratchpad_state": state, "visible": False,
                        "focused": False,
                        "rect": {"x": 0, "y": 0, "width": width, "height": height},
                        "nodes": [], "floating_nodes": [],
                    }],
                    "floating_nodes": [],
                })
                bridge.queue_command = Mock()
                bridge.queue_sync = Mock()
                bridge.emit_snapshot(force=True)
                bridge.queue_command.assert_not_called()
                bridge.queue_sync.assert_not_called()
                self.assertTrue(bridge.discord_show_requested)

    def test_previously_visible_hidden_main_reveals_once_and_waits_for_visibility(self):
        bridge = geometry.Bridge(0.1)
        bridge.discord_show_requested = True
        bridge.discord_show_focus = True
        bridge.discord_main_seen_visible.add(4242)
        bridge.poll_ipc.request = Mock(return_value={
            "id": 1,
            "visible": True,
            "focused": False,
            "rect": {"x": 0, "y": 0, "width": 1920, "height": 1080},
            "nodes": [{
                "id": 4242,
                "name": "Vesktop",
                "app_id": "dev.vencord.vesktop",
                "visible": False,
                "focused": False,
                "rect": {"x": 200, "y": 100, "width": 1280, "height": 720},
                "nodes": [], "floating_nodes": [],
            }],
            "floating_nodes": [],
        })
        commands = []
        bridge.queue_command = commands.append
        bridge.emit_snapshot(force=True)
        bridge.emit_snapshot(force=True)
        joined = "\n".join(commands)
        self.assertEqual(joined.count('[con_id="4242"] scratchpad show'), 1)
        self.assertNotIn("move scratchpad", joined)
        self.assertTrue(bridge.discord_show_requested)

    def test_cold_start_hidden_main_is_not_forced_visible_before_app_loaded(self):
        bridge = geometry.Bridge(0.1)
        bridge.discord_show_requested = True
        bridge.poll_ipc.request = Mock(return_value={
            "id": 1,
            "visible": True,
            "focused": False,
            "rect": {"x": 0, "y": 0, "width": 1920, "height": 1080},
            "nodes": [{
                "id": 5000,
                "name": "Vesktop",
                "app_id": "dev.vencord.vesktop",
                "visible": False,
                "focused": False,
                "rect": {"x": 0, "y": 0, "width": 1280, "height": 720},
                "nodes": [], "floating_nodes": [],
            }],
            "floating_nodes": [],
        })
        bridge.queue_command = Mock()
        bridge.emit_snapshot(force=True)
        bridge.queue_command.assert_not_called()
        self.assertTrue(bridge.discord_show_requested)

    def test_preexisting_hidden_main_waits_for_activation_owned_restore(self):
        bridge = geometry.Bridge(0.1)
        bridge.discord_show_requested = True
        bridge.poll_ipc.request = Mock(return_value={
            "id": 1,
            "visible": True,
            "focused": False,
            "rect": {"x": 0, "y": 0, "width": 1920, "height": 1080},
            "nodes": [{
                "id": 6000,
                "name": "Vesktop",
                "app_id": "dev.vencord.vesktop",
                "visible": False,
                "focused": False,
                "rect": {"x": 0, "y": 0, "width": 1280, "height": 720},
                "nodes": [], "floating_nodes": [],
            }],
            "floating_nodes": [],
        })
        bridge.queue_command = Mock()
        bridge.emit_snapshot(force=True)
        bridge.emit_snapshot(force=True)
        bridge.queue_command.assert_not_called()
        self.assertTrue(bridge.discord_show_requested)

    def test_visible_main_snaps_directly_to_live_social_slot(self):
        bridge = geometry.Bridge(0.1)
        bridge.discord_show_requested = True
        bridge.discord_show_focus = True
        bridge.poll_ipc.request = Mock(return_value={
            "id": 1,
            "visible": True,
            "focused": False,
            "rect": {"x": 0, "y": 0, "width": 1920, "height": 1080},
            "nodes": [
                {
                    "id": 99,
                    "name": "QS_SOCIAL_MENU",
                    "visible": True,
                    "focused": False,
                    "rect": {"x": 100, "y": 50, "width": 1210, "height": 700},
                    "nodes": [], "floating_nodes": [],
                },
                {
                    "id": 7000,
                    "name": "Friends",
                    "app_id": "dev.vencord.vesktop",
                    "visible": True,
                    "focused": False,
                    "rect": {"x": 500, "y": 400, "width": 980, "height": 520},
                    "nodes": [], "floating_nodes": [],
                },
            ],
            "floating_nodes": [],
        })
        syncs = []
        bridge.queue_sync = syncs.append
        bridge.emit_snapshot(force=True)

        self.assertIn(7000, bridge.discord_main_seen_visible)
        self.assertFalse(bridge.discord_show_requested)
        self.assertEqual(len(syncs), 1)
        self.assertEqual(syncs[0]["target"], "discord")
        self.assertEqual(syncs[0]["x"], 211)
        self.assertEqual(syncs[0]["y"], 51)
        self.assertEqual(syncs[0]["width"], 1098)
        self.assertEqual(syncs[0]["height"], 698)
        self.assertTrue(syncs[0]["setup"])
        self.assertTrue(syncs[0]["focus"])

    def test_splash_request_stays_armed_for_real_main_window(self):
        bridge = geometry.Bridge(0.1)
        bridge.discord_show_requested = True
        bridge.poll_ipc.request = Mock(return_value={
            "id": 1,
            "visible": True,
            "focused": False,
            "rect": {"x": 0, "y": 0, "width": 1920, "height": 1080},
            "nodes": [{
                "id": 101,
                "name": "Vesktop",
                "app_id": "dev.vencord.vesktop",
                "visible": True,
                "focused": True,
                "rect": {"x": 800, "y": 400, "width": 300, "height": 350},
                "nodes": [], "floating_nodes": [],
            }],
            "floating_nodes": [],
        })
        bridge.queue_command = Mock()
        bridge.emit_snapshot(force=True)
        self.assertEqual(bridge.discord_kind, "splash")
        self.assertTrue(bridge.discord_show_requested)

    def test_discord_sync_reasserts_floating_and_borderless_even_after_setup(self):
        # Screenshot regression: after PR #799 the visible "Vesktop"
        # decoration remains because setup=False may be sent before a
        # successful compositor border update. Every Discord resize/move must
        # still enforce the borderless Sway window.
        for setup in (False, True):
            with self.subTest(setup=setup):
                cmd = geometry.build_sync_command({
                    "target": "discord", "conId": 4242,
                    "x": 211, "y": 51, "width": 1098, "height": 698,
                    "setup": setup, "focus": False,
                })
                self.assertIn('[con_id="4242"] floating enable', cmd)
                self.assertIn('[con_id="4242"] border none', cmd)
                self.assertNotIn('[app_id=', cmd)
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

    def test_discord_activation_owns_launch_and_helper_owns_only_sway_control(self):
        social = SOCIAL.read_text(encoding="utf-8")
        helper = GEOMETRY.read_text(encoding="utf-8")

        launch = social.split("    function showDiscord() {", 1)[1].split(
            "    function hideDiscord()", 1
        )[0]
        self.assertIn("discordLaunchProcess.exec(", launch)
        self.assertIn("setsid -f flatpak run dev.vencord.Vesktop", launch)
        self.assertIn("helperShowDiscord(", launch)
        self.assertNotIn("swaymsg", launch)
        self.assertNotIn('[app_id="vesktop"]', social)

        self.assertIn('VESKTOP_WAYLAND_IDS = {"vesktop", "dev.vencord.vesktop"}', helper)
        self.assertIn('VESKTOP_X11_CLASSES = {"vesktop"}', helper)
        self.assertIn('sandbox_app_id == "dev.vencord.vesktop"', helper)
        self.assertIn("discord_main_seen_visible", helper)
        self.assertIn('return f\'[con_id="{int(con_id)}"]\'', helper)
        self.assertIn('op == "showDiscord"', helper)
        self.assertIn('op == "hideDiscord"', helper)
        self.assertNotIn("subprocess.Popen(", helper)
        self.assertNotIn("node.get(\"app_id\") == \"vesktop\"", helper)

    def test_helper_waits_without_launching_when_no_container_is_discovered(self):
        bridge = geometry.Bridge(0.1)
        bridge.discord_show_requested = True
        tree = {
            "id": 1,
            "visible": True,
            "focused": False,
            "rect": {"x": 0, "y": 0, "width": 1920, "height": 1080},
            "nodes": [],
            "floating_nodes": [],
        }
        bridge.poll_ipc.request = Mock(return_value=tree)
        bridge.emit_snapshot(force=True)
        bridge.emit_snapshot(force=True)
        self.assertTrue(bridge.discord_show_requested)

    def test_fast_follow_ignores_hidden_scratchpad_vesktop(self):
        bridge, commands = self.bridge(docked=True)
        hidden = sample()
        hidden["discord"]["visible"] = False
        result = bridge.fast_follow(hidden)
        self.assertIsNone(result["fastLeader"])
        self.assertEqual(commands, [])



if __name__ == "__main__":
    main()
