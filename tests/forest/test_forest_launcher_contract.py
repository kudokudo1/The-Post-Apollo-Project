"""ForestW V0 source-scoped guards. Native Qt/Wayland acceptance is separate."""
from pathlib import Path
import subprocess
import unittest
import xml.etree.ElementTree as ET

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
        # One Forest host inside the standard 8px left Row after To-do.
        left = text.split("// ===== LEFT MODULES", 1)[1].split(
            "// ===== CENTER MODULE", 1)[0]
        self.assertIn("spacing: 8", left)
        self.assertIn("id: forestHost", left)
        self.assertLess(left.index("id: tasksHost"), left.index("id: forestHost"))
        self.assertIn("dockCenterX: shellRoot.margins.left + leftModules.x", left)
        self.assertIn("+ forestHost.x + forestButton.width / 2", left)
        self.assertNotIn("anchors.right: apolloHubHost.left", text)
        self.assertNotIn("anchors.left: apolloHubHost.right", text)
        self.assertEqual(text.count("id: forestHost"), 1)

    def test_ai_palette_and_compact_decorated_icon(self):
        text = (ROOT / "modules/Forest.qml").read_text()
        for required in ('text: "🏕"', 'text: "࣪݁✧"', 'text: "๋⭑"',
                         "GohuText {", "textFormat: Text.PlainText",
                         "readonly property int iconPadding: 10",
                         "readonly property color starColor: dock.open ? Colors.magenta : Colors.white",
                         "implicitWidth: 50", "implicitHeight: 50",
                         "width: dock.width - 2 * dock.iconPadding",
                         "height: dock.height - 2 * dock.iconPadding",
                         "anchors.centerIn: parent",
                         "contentGlowSource: tentFace",
                         "normalForegroundColor: Colors.green",
                         "normalDockGlowColor: Colors.green",
                         "normalContentGlowColor: Colors.green",
                         "openForegroundColor: Colors.magenta",
                         "openGlowColor: Colors.magenta"):
            with self.subTest(required=required):
                self.assertIn(required, text)
        self.assertNotIn("NotoText {", text)
        self.assertEqual(text.count("GohuText {"), 3)
        self.assertEqual(text.count("color: dock.starColor"), 2)
        self.assertEqual(text.count("id: tentFace"), 1)
        self.assertEqual(text.count("color: dock.foregroundColor"), 1)
        self.assertNotIn("anchors.verticalCenterOffset", text)
        # Geometry constraint: a 50px square with 10px insets yields
        # a centered 30px square on both axes. Text ink needs live review.
        dock = 50
        pad = 10
        artwork = dock - 2 * pad
        self.assertEqual((dock - artwork) / 2, pad)
        self.assertEqual(artwork, 30)

    def test_tree_selector_uses_local_outline_svg_assets(self):
        view = (ROOT / "widgets/ForestW.qml").read_text()
        self.assertIn('iconPath: "../assets/forest/cherry-outline.svg"', view)
        self.assertIn('iconPath: "../assets/forest/maple-outline.svg"', view)
        self.assertIn("source: Qt.resolvedUrl(modelData.iconPath)", view)
        self.assertIn("fillMode: Image.PreserveAspectFit", view)
        self.assertIn("width: 26", view)
        self.assertIn("height: 26", view)
        self.assertIn("text: modelData.name", view)
        self.assertIn("onClicked: root.selectedTreeIndex = index", view)
        self.assertIn("index === root.selectedTreeIndex ? Colors.magenta : Colors.white", view)
        self.assertNotIn("modelData.mark", view)
        self.assertNotIn('mark: "🍁"', view)
        self.assertNotIn('mark: "✿"', view)

        # Forest-specific icon identity: foreground and halo are different
        # color axes, with the effect sampling its sibling Image.
        self.assertIn("TextHashGlow {", view)
        self.assertIn("id: treeGlyphGlow", view)
        self.assertIn("safeSource: treeGlyph", view)
        self.assertIn("requestedVisible: root.menuOpen", view)
        self.assertIn('foregroundColor: modelData.name === "CHERRY" ? Colors.white : Colors.orange', view)
        self.assertIn('preferredGlowColor: modelData.name === "CHERRY" ? Colors.magenta : Colors.red', view)
        self.assertIn("z: -1", view)
        self.assertNotIn("layer.effect: DropShadow", view)

        palette = (ROOT / "components/Colors.qml").read_text()
        self.assertIn('#C74EC7', palette)
        self.assertIn('#ED981A', palette)
        for asset, color, min_paths in (
            ("cherry-outline.svg", "#DCF3FA", 6),
            ("maple-outline.svg", "#ED981A", 2),
        ):
            with self.subTest(icon=asset):
                filename = ROOT / "assets/forest" / asset
                svg = ET.parse(filename).getroot()
                ns = "{http://www.w3.org/2000/svg}"
                self.assertEqual(svg.tag, ns + "svg")
                self.assertEqual(svg.attrib.get("viewBox"), "0 0 48 48")
                descendants = list(svg.iter())
                self.assertTrue(any(el.attrib.get("stroke") == color for el in descendants))
                self.assertTrue(any(el.attrib.get("fill") == "none" for el in descendants))
                self.assertGreaterEqual(
                    sum(el.tag == ns + "path" for el in descendants), min_paths)
                # No gradients, masks, bitmap/foreign embeds or filled petals.
                forbidden = {"rect", "image", "foreignObject", "linearGradient",
                             "radialGradient", "filter", "pattern"}
                for el in descendants:
                    self.assertNotIn(el.tag.removeprefix(ns), forbidden)
                    self.assertIn(el.attrib.get("fill", "none"), ("none",))
                    if "stroke" in el.attrib:
                        self.assertEqual(el.attrib["stroke"], color)

        cherry = ET.parse(ROOT / "assets/forest/cherry-outline.svg").getroot()
        petals = cherry.find(".//" + ns + "g[@id='sakura-petals']")
        self.assertIsNotNone(petals)
        self.assertEqual(len(petals.findall(ns + "path")), 5)
        self.assertEqual(
            [petal.attrib.get("transform") for petal in petals.findall(ns + "path")],
            [None] + [f"rotate({i} 24 24)" for i in (72, 144, 216, 288)],
        )
        stamens = cherry.find(".//" + ns + "g[@id='sakura-stamens']")
        self.assertIsNotNone(stamens)
        self.assertGreaterEqual(len(stamens.findall(ns + "circle")), 6)
        maple = ET.parse(ROOT / "assets/forest/maple-outline.svg").getroot()
        contour = maple.find(".//" + ns + "path[@id='maple-contour']")
        veins = maple.find(".//" + ns + "path[@id='maple-veins']")
        self.assertIsNotNone(contour)
        self.assertIsNotNone(veins)
        self.assertGreaterEqual(contour.attrib["d"].count("C"), 8)

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
