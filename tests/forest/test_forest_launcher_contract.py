"""ForestW V0 source-scoped guards. Native Qt/Wayland acceptance is separate."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ForestLauncherContract(unittest.TestCase):
    def test_dock_uses_shared_component_and_click_toggle(self):
        text = (ROOT / "modules/Forest.qml").read_text()
        self.assertIn("DockButton {", text)
        self.assertIn("onLeftClicked: toggleRequested()", text)
        self.assertIn("open: menuOpen", text)

    def test_standalone_mapped_window_and_closed_mask(self):
        text = (ROOT / "widgets/ForestW.qml").read_text()
        for phrase in ("PanelWindow {", "WindowPanelFrame {", "visible: true",
                       "root.menuOpen ? root.frameWidth : 0",
                       "root.menuOpen ? root.frameHeight : 0",
                       "WlrKeyboardFocus.OnDemand",
                       "onCloseRequested: root.menuOpen = false"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertNotIn("WlrKeyboardFocus.Exclusive", text)

    def test_no_active_ai_or_host_mutation_in_scaffold(self):
        text = (ROOT / "widgets/ForestW.qml").read_text()
        for prohibited in ("Process {", "HttpRequest", "agent turn",
                           "agent session-create", "OllamaChat",
                           "onCompleted: run", "Quickshell.exec"):
            with self.subTest(prohibited=prohibited):
                self.assertNotIn(prohibited, text)
        self.assertIn("ADAPTER NOT CONNECTED", text)

    def test_dock_is_wired_in_shell_only_once(self):
        text = (ROOT / "shell.qml").read_text()
        self.assertEqual(text.count("id: forestHost"), 1)
        self.assertEqual(text.count("id: forestButton"), 1)
        self.assertEqual(text.count("id: forestWindow"), 1)
        self.assertIn("onToggleRequested: forestWindow.toggle()", text)
        # Center dock owns ApolloHub. Forest uses its free LEFT side, not
        # the Network dock to the right. One anchor, one launcher instance.
        self.assertIn("anchors.right: apolloHubHost.left", text)
        self.assertIn("anchors.rightMargin: 8", text)
        self.assertNotIn("anchors.left: apolloHubHost.right", text)
        self.assertIn("anchors.top: apolloHubHost.top", text)
        self.assertIn("dockCenterX: shellRoot.margins.left + forestHost.x", text)
        left_modules = text.split("id: leftModules", 1)[1].split(
            "id: apolloHubHost", 1)[0]
        self.assertNotIn("id: forestHost", left_modules)

    def test_ai_palette_and_compact_decorated_icon(self):
        text = (ROOT / "modules/Forest.qml").read_text()
        for required in ('text: "࣪݁🏕๋⭑"',
                         "GohuText {",
                         "textFormat: Text.PlainText",
                         "font.letterSpacing: -1",
                         "contentGlowSource: forestMark",
                         "normalForegroundColor: Colors.green",
                         "normalDockGlowColor: Colors.green",
                         "normalContentGlowColor: Colors.green",
                         "openForegroundColor: Colors.magenta",
                         "openGlowColor: Colors.magenta"):
            with self.subTest(required=required):
                self.assertIn(required, text)
        self.assertNotIn('text: "🌲"', text)
        self.assertNotIn("NotoText {", text)
        self.assertEqual(text.count("GohuText {"), 1)
        self.assertEqual(text.count('text: "࣪݁🏕๋⭑"'), 1)
        self.assertEqual(text.count("id: forestMark"), 1)


    def test_live_status_is_between_resize_and_close(self):
        text = (ROOT / "widgets/ForestW.qml").read_text()
        first = text.index("id: expandButton")
        middle = text.index("id: liveIndicator")
        last = text.index("id: closeButton")
        self.assertLess(first, middle)
        self.assertLess(middle, last)
        self.assertIn("anchors.right: liveIndicator.left", text)
        self.assertIn("anchors.right: closeButton.left", text)
        self.assertIn('text: "LIVE"', text)
        self.assertIn("border.color: Colors.green", text)
        # LIVE reflects an open QML workspace, not an inference backend.
        self.assertIn("AI engine not connected", text)
        self.assertIn("ADAPTER NOT CONNECTED", text)

    def test_chassis_has_common_top_edge(self):
        text = (ROOT / "widgets/ForestChassisPolicy.js").read_text()
        view = (ROOT / "widgets/ForestW.qml").read_text()
        self.assertIn("function topMargin(", text)
        self.assertIn("    return 0;", text)
        self.assertNotIn("topAllowance = height >= 300 ? 80", text)
        self.assertIn("readonly property int frameTopInset: 9", view)
        self.assertIn("anchors.topMargin: root.frameTopInset", view)

    def test_geometry_script(self):
        script = ROOT / "tests/forest/forest_geometry_test.cjs"
        result = subprocess.run(["node", str(script)], text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=10, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
