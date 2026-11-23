"""ForestW V0 source-scoped guards. Native Qt/Wayland acceptance is separate."""
from pathlib import Path
import hashlib
import struct
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
        self.assertIn('hoverIconPath: "../assets/forest/maple-hover-orange.svg"', view)
        self.assertIn("source: Qt.resolvedUrl(", view)
        self.assertIn("modelData.hoverIconPath", view)
        self.assertIn("modelData.openIconPath", view)
        self.assertIn("fillMode: Image.PreserveAspectFit", view)
        self.assertIn("width: 26", view)
        self.assertIn("height: 26", view)
        self.assertIn("text: modelData.name", view)
        self.assertIn("onLeftClicked: root.selectedTreeIndex = index", view)
        self.assertIn("open: index === root.selectedTreeIndex", view)
        self.assertIn("readonly property color iconIdentityColor: modelData.identityColor", view)
        self.assertIn("normalForegroundColor: iconIdentityColor", view)
        self.assertIn("readonly property color iconIdleGlowColor: modelData.iconIdleGlowColor", view)
        self.assertIn("readonly property color spiritualIdleGlowColor: modelData.spiritualIdleGlowColor", view)
        self.assertIn("normalDockGlowColor: spiritualIdleGlowColor", view)
        self.assertIn("normalContentGlowColor: spiritualIdleGlowColor", view)
        self.assertIn("preferredGlowColor: treeRow.resolvedIconGlowColor", view)
        self.assertIn("hoverForegroundColor: Colors.orange", view)
        self.assertIn("pressedForegroundColor: Colors.magenta", view)
        self.assertIn("id: treeGradientBorder", view)
        self.assertIn("border.width: 0", view)
        self.assertIn("baseColor: treeRow.foregroundColor", view)
        self.assertIn("accentColor: treeRow.energized", view)
        self.assertIn("accentTopRight: modelData.gradientTopRight", view)
        self.assertIn("baseColor: treeRow.foregroundColor", view)
        self.assertIn("id: treeNameGlow", view)
        self.assertIn("safeSource: treeName", view)
        self.assertIn("contentGlowEnabled: false", view)
        self.assertNotIn("color: index === root.selectedTreeIndex ?", view)
        self.assertNotIn("modelData.mark", view)
        self.assertNotIn('mark: "🍁"', view)
        self.assertNotIn('mark: "✿"', view)

        # Shared DockButton governs idle, hover, pressed and open
        # consistently across the Tree artwork, title, border and glows.
        self.assertIn("TextHashGlow {", view)
        self.assertIn("id: treeGlyphGlow", view)
        self.assertIn("safeSource: treeGlyph", view)
        self.assertIn("requestedVisible: root.menuOpen", view)
        self.assertIn("foregroundColor: treeRow.foregroundColor", view)
        self.assertIn("preferredGlowColor: treeRow.contentGlowColor", view)
        self.assertIn("z: -1", view)
        self.assertNotIn("layer.effect: DropShadow", view)

        palette = (ROOT / "components/Colors.qml").read_text()
        self.assertIn('#C74EC7', palette)
        self.assertIn('#ED981A', palette)
        ns = "{http://www.w3.org/2000/svg}"
        # Only the two idle SVGs have gradients, using the existing palette.
        # No runtime shader, bitmap, mask or unrelated markup is permitted.
        for asset, kind, gradient_id, colors, min_paths in (
            ("cherry-outline.svg", "radialGradient", "cherry-petal-stroke",
             ("#EE76B2", "#F09AC7", "#DCF3FA"), 6),
            ("maple-outline.svg", "linearGradient", "maple-vertical-stroke",
             ("#C7482F", "#D86438", "#E78924", "#ED981A"), 2),
        ):
            with self.subTest(icon=asset):
                svg = ET.parse(ROOT / "assets/forest" / asset).getroot()
                self.assertEqual(svg.tag, ns + "svg")
                self.assertEqual(svg.attrib.get("viewBox"), "0 0 48 48")
                descendants = list(svg.iter())
                self.assertTrue(any(el.attrib.get("fill") == "none"
                                    for el in descendants))
                self.assertGreaterEqual(
                    sum(el.tag == ns + "path" for el in descendants), min_paths)
                forbidden = {"rect", "image", "foreignObject", "mask",
                             "filter", "pattern", "script", "style"}
                for el in descendants:
                    self.assertNotIn(el.tag.removeprefix(ns), forbidden)
                    self.assertEqual(el.attrib.get("fill", "none"), "none")
                gradients = [el for el in descendants
                             if el.tag in (ns + "linearGradient",
                                           ns + "radialGradient")]
                self.assertEqual(len(gradients), 1)
                gradient = gradients[0]
                self.assertEqual(gradient.tag, ns + kind)
                self.assertEqual(gradient.attrib.get("id"), gradient_id)
                self.assertEqual(gradient.attrib.get("gradientUnits"),
                                 "userSpaceOnUse")
                stops = gradient.findall(ns + "stop")
                self.assertEqual(tuple(el.attrib.get("stop-color")
                                       for el in stops), colors)
                self.assertEqual(stops[0].attrib.get("offset"), "0%")
                expected_offsets = ("0%", "52%", "100%") if kind == "radialGradient" \
                    else ("0%", "38%", "74%", "100%")
                self.assertEqual(tuple(stop.attrib.get("offset") for stop in stops),
                                 expected_offsets)
                self.assertEqual(stops[-1].attrib.get("offset"), "100%")
                self.assertIn("url(#" + gradient_id + ")",
                              [el.attrib.get("stroke") for el in descendants])

        # Variant SVGs must keep every original outline path intact while
        # carrying the shared orange hover and magenta open palette.
        for original, variant, ink in (
            ("cherry-outline.svg", "cherry-hover-orange.svg", "#ED981A"),
            ("cherry-outline.svg", "cherry-open-magenta.svg", "#C74EC7"),
            ("maple-outline.svg", "maple-hover-orange.svg", "#ED981A"),
            ("maple-outline.svg", "maple-open-magenta.svg", "#C74EC7"),
        ):
            normal = ET.parse(ROOT / "assets/forest" / original).getroot()
            colored = ET.parse(ROOT / "assets/forest" / variant).getroot()
            paths_a = [p.attrib.get("d") for p in normal.iter()
                       if p.tag == ns + "path"]
            paths_b = [p.attrib.get("d") for p in colored.iter()
                       if p.tag == ns + "path"]
            self.assertEqual(paths_a, paths_b)
            strokes = [n.attrib["stroke"] for n in colored.iter()
                       if "stroke" in n.attrib]
            self.assertTrue(strokes)
            self.assertTrue(all(color == ink for color in strokes))

        cherry = ET.parse(ROOT / "assets/forest/cherry-outline.svg").getroot()
        petals = cherry.find(".//" + ns + "g[@id='sakura-petals']")
        self.assertIsNotNone(petals)
        self.assertEqual(petals.attrib.get("stroke"),
                         "url(#cherry-petal-stroke)")
        self.assertEqual(len(petals.findall(ns + "path")), 5)
        self.assertEqual(
            [petal.attrib.get("transform") for petal in petals.findall(ns + "path")],
            [None] + [f"rotate({i} 24 24)" for i in (72, 144, 216, 288)],
        )
        stamens = cherry.find(".//" + ns + "g[@id='sakura-stamens']")
        self.assertIsNotNone(stamens)
        self.assertEqual(stamens.attrib.get("stroke"), "#EE76B2")
        self.assertGreaterEqual(len(stamens.findall(ns + "circle")), 6)
        maple = ET.parse(ROOT / "assets/forest/maple-outline.svg").getroot()
        contour = maple.find(".//" + ns + "path[@id='maple-contour']")
        veins = maple.find(".//" + ns + "path[@id='maple-veins']")
        self.assertIsNotNone(contour)
        self.assertIsNotNone(veins)
        maple_group = maple.find(".//" + ns + "g")
        self.assertEqual(maple_group.attrib.get("stroke"),
                         "url(#maple-vertical-stroke)")
        self.assertGreaterEqual(contour.attrib["d"].count("C"), 8)

    def test_five_tree_ids_assets_and_unassigned_roles(self):
        view = (ROOT / "widgets/ForestW.qml").read_text()
        self.assertIn('property var selectedTreeModels: ["", "", "", "", ""]', view)
        self.assertIn('text: "TREES // " + String(root.treeSlots.length).padStart(2, "0")', view)
        tree_profiles = (
            ("CHERRY", "cherry-outline.svg", "GENERAL // ASSISTANT",
             "white", "magenta", "magenta", '"#EE76B2"', False),
            ("MAPLE", "maple-outline.svg", "FILES // ORGANIZATION",
             "orange", "red", "red", '"#C7482F"', False),
            ("BRISTLECONE PINE", "bristlecone-pine.png", "TREEWRITE // CODER",
             "white", "orange", "green", "Colors.green", False),
            ("CEDAR", "cedar-outline.svg", "SECURITY // PROTECTION",
             "green", "orange", "orange", "Colors.orange", False),
            ("MACINTOSH", "macintosh-outline.svg", "TECH // SUPPORT",
             "green", "red", "red", "Colors.red", False),
        )
        for name, asset, role, foreground, icon_glow, spiritual_glow, accent, right in tree_profiles:
            with self.subTest(tree=name):
                self.assertEqual(view.count('name: "' + name + '", role:'), 1)
                self.assertIn('iconPath: "../assets/forest/' + asset + '"', view)
                block = view.split('name: "' + name + '", role:', 1)[1].split(
                    '        }', 1)[0]
                self.assertIn('identityColor: Colors.' + foreground, block)
                self.assertIn('iconIdleGlowColor: Colors.' + icon_glow, block)
                self.assertIn('spiritualIdleGlowColor: Colors.' + spiritual_glow, block)
                self.assertIn('gradientAccentColor: ' + accent, block)
                self.assertIn('gradientTopRight: ' +
                              ('true' if right else 'false'), block)
                self.assertIn('"' + role + '"', block)
                self.assertTrue((ROOT / "assets/forest" / asset).is_file())
        self.assertIn("readonly property bool chatHostTrusted: false", view)
        self.assertIn("readonly property var activeChatSessions: []", view)
        self.assertIn("source: Qt.resolvedUrl(root.activeTree.iconPath)", view)

    def test_spiritual_tree_glow_is_independent_of_icon_glow(self):
        view = (ROOT / "widgets/ForestW.qml").read_text()
        tree_block = view.split("id: treeRow", 1)[1].split(
            "onLeftClicked: root.selectedTreeIndex = index", 1)[0]
        glyph_block = view.split("id: treeGlyphGlow", 1)[1].split(
            "id: treeName", 1)[0]
        name_block = view.split("id: treeNameGlow", 1)[1].split(
            "GohuText {", 1)[0]
        self.assertIn("readonly property color resolvedIconGlowColor:", tree_block)
        self.assertIn("treeRow.open || treeRow.pressed || treeRow.hovered", tree_block)
        self.assertIn("? treeRow.contentGlowColor : treeRow.iconIdleGlowColor",
                      tree_block)
        self.assertIn("normalDockGlowColor: spiritualIdleGlowColor", tree_block)
        self.assertIn("normalContentGlowColor: spiritualIdleGlowColor", tree_block)
        self.assertIn("preferredGlowColor: treeRow.resolvedIconGlowColor",
                      glyph_block)
        self.assertIn("preferredGlowColor: treeRow.contentGlowColor", name_block)
        self.assertIn("foregroundColor: treeRow.foregroundColor", name_block)
        self.assertIn("border.width: 0", tree_block)
        self.assertIn("id: treeGradientBorder", tree_block)
        # Chat title keeps its own Tree spiritual channel rather than
        # inheriting the selected button's magenta open state.
        self.assertIn("preferredGlowColor: root.activeTree.spiritualIdleGlowColor", view)
        self.assertIn("preferredGlowColor: root.activeTree.iconIdleGlowColor", view)
        self.assertNotIn("chromeIdleGlowColor", view)
        self.assertNotIn("modelData.idleGlowColor", view)

    def test_bristlecone_approved_pixel_art_and_state_variants(self):
        # Exact user-edited 48px pixel source, including the three tiny
        # foliage/branch gaps. Binary PNG, not replacement traced vectors.
        approved = {
            "bristlecone-pine.png":
                "cb7d9e4868f4b696ae78722209a806d6c0fd9c97ff710c0c409dfaf68c907798",
            "bristlecone-hover-orange.png":
                "d035c7e85115e238608d591d8fb1e27aeae0bc5dddbe51a636f7fde7f2ce2d43",
            "bristlecone-open-magenta.png":
                "50b195800d01966791bb362b2e7d71c37a8b97183dd73f7e12019e4107c12f1b",
        }
        for filename, expected_hash in approved.items():
            with self.subTest(filename=filename):
                data = (ROOT / "assets/forest" / filename).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), expected_hash)
                self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(data[12:16], b"IHDR")
                width, height = struct.unpack(">II", data[16:24])
                self.assertEqual((width, height), (48, 48))
                self.assertEqual(data[25], 6)  # Truecolor + alpha
        view = (ROOT / "widgets/ForestW.qml").read_text()
        self.assertIn('hoverIconPath: "../assets/forest/bristlecone-hover-orange.png"', view)
        self.assertIn('openIconPath: "../assets/forest/bristlecone-open-magenta.png"', view)

    def test_new_line_svg_variants_preserve_geometry_and_palette(self):
        ns = "{http://www.w3.org/2000/svg}"
        for stem, gradient_count, identity_colors in (
            ("cedar", 1, ("#00F782", "#90E84F", "#ED981A")),
            ("macintosh", 2, ("#FF6154", "#EB3346", "#ED981A",
                               "#78CC57", "#00F782", "#9ECE6A")),
        ):
            original = ET.parse(ROOT / "assets/forest" /
                                (stem + "-outline.svg")).getroot()
            self.assertEqual(original.tag, ns + "svg")
            self.assertEqual(original.attrib.get("viewBox"), "0 0 48 48")
            orig_paths = [el.attrib.get("d") for el in original.iter()
                          if el.tag == ns + "path"]
            gradients = [el for el in original.iter()
                         if el.tag in (ns + "linearGradient", ns + "radialGradient")]
            self.assertEqual(len(gradients), gradient_count)
            stops = [el.attrib.get("stop-color") for el in original.iter()
                     if el.tag == ns + "stop"]
            for color in identity_colors:
                self.assertIn(color, stops)
            self.assertGreaterEqual(len(orig_paths), 5)
            for suffix, color in (("hover-orange.svg", "#ED981A"),
                                  ("open-magenta.svg", "#C74EC7")):
                with self.subTest(stem=stem, variant=suffix):
                    svg = ET.parse(ROOT / "assets/forest" /
                                   (stem + "-" + suffix)).getroot()
                    self.assertEqual(svg.attrib.get("viewBox"), "0 0 48 48")
                    self.assertEqual([p.attrib.get("d") for p in svg.iter()
                                      if p.tag == ns + "path"], orig_paths)
                    self.assertFalse(any(el.tag in
                                         (ns + "linearGradient", ns + "radialGradient")
                                         for el in svg.iter()))
                    strokes = [el.attrib["stroke"] for el in svg.iter()
                               if "stroke" in el.attrib]
                    self.assertTrue(strokes)
                    self.assertTrue(all(value == color for value in strokes))
            for el in original.iter():
                self.assertNotIn(el.tag, {ns + "image", ns + "foreignObject",
                                          ns + "script", ns + "filter", ns + "mask"})

    def test_tree_corner_gradients_reuse_identity_and_resolved_state(self):
        view = (ROOT / "widgets/ForestW.qml").read_text()
        ring = (ROOT / "widgets/ForestCornerGradientBorder.qml").read_text()
        name = (ROOT / "widgets/ForestGradientName.qml").read_text()

        self.assertEqual(view.count("ForestCornerGradientBorder {"), 1)
        self.assertEqual(view.count("ForestGradientName {"), 3)
        self.assertIn("baseColor: treeRow.foregroundColor", view)
        self.assertEqual(view.count("accentColor: treeRow.energized"), 3)
        self.assertEqual(view.count("? treeRow.foregroundColor : modelData.gradientAccentColor"), 3)
        self.assertIn("accentTopRight: modelData.gradientTopRight", view)
        self.assertIn('gradientAccentColor: "#C7482F", gradientTopRight: false', view)
        self.assertIn("text: modelData.name", view)
        self.assertIn("id: treeRole", view)
        self.assertIn("text: modelData.role", view)
        self.assertIn("pixelSize: 9", view)
        self.assertIn("bold: false", view)
        self.assertIn("height: 12", view)
        self.assertIn('text: root.activeTree.name + " // CHAT"', view)
        self.assertIn("baseColor: root.activeTree.identityColor", view)
        self.assertIn("accentColor: root.activeTree.gradientAccentColor", view)
        self.assertIn("accentTopRight: root.activeTree.gradientTopRight", view)
        self.assertIn('gradientText: root.activeTree.name + " // CHAT"', view)
        self.assertIn("preferredGlowColor: root.activeTree.spiritualIdleGlowColor", view)
        self.assertIn("safeSource: treeName", view)
        self.assertIn("safeSource: chatHeading", view)
        self.assertIn("foregroundColor: chatHeading.baseColor", view)
        self.assertNotIn("baseColor: root.selectedTreeButton", view)
        self.assertNotIn("accentColor: root.selectedTreeButton.contentGlowColor", view)

        # The corner border is an even-odd 1px ring, not a filled overlay.
        # It retains the existing yellow open fill and shared button input.
        self.assertIn("import QtQuick.Shapes", ring)
        self.assertIn("fillRule: ShapePath.OddEvenFill", ring)
        self.assertIn("PathMove { x: root.lineWidth; y: root.lineWidth }", ring)
        self.assertIn("strokeWidth: -1", ring)
        self.assertIn("fillGradient: RadialGradient {", ring)
        self.assertIn("centerX: root.accentTopRight ? root.width : 0", ring)
        self.assertIn("color: root.accentColor", ring)
        self.assertIn("color: root.baseColor", ring)
        # The previous 0.43-width glow stopped too early on the top edge.
        # Keep an accent spanning roughly four-fifths of the button top.
        self.assertIn("Math.max(56, Math.min(160, width * 0.78))", ring)
        self.assertNotIn("width * 0.43", ring)
        for button_width in (96, 128, 160):
            new_radius = max(56, min(160, button_width * 0.78))
            old_radius = max(42, min(100, button_width * 0.43))
            self.assertGreater(new_radius, old_radius)
        self.assertNotIn("MouseArea {", ring)
        self.assertNotIn("Process {", ring)
        self.assertNotIn("ShaderEffect {", ring)
        self.assertIn("border.width: 0", view)
        self.assertIn("open: index === root.selectedTreeIndex", view)
        # All energized states are solid ink; open has precedence over
        # hover/press and must retain yellow fill, magenta ink and glow.
        dock = (ROOT / "components/DockButton.qml").read_text()
        self.assertIn("property color openFillColor: Colors.yellow", dock)
        self.assertIn("property color openForegroundColor: Colors.magenta", dock)
        self.assertIn("property color openGlowColor: Colors.magenta", dock)
        # Role labels use the identical idle corner accent and resolve to
        # solid foreground ink in hover/open, without changing button fill.
        role_block = view.split("id: treeRole", 1)[1].split(
            "        }", 1)[0]
        self.assertIn("text: modelData.role", role_block)
        self.assertIn("baseColor: treeRow.foregroundColor", role_block)
        self.assertIn("accentColor: treeRow.energized", role_block)
        self.assertIn("? treeRow.foregroundColor : modelData.gradientAccentColor",
                      role_block)
        self.assertIn("accentTopRight: modelData.gradientTopRight", role_block)
        self.assertIn("pixelSize: 9", role_block)
        self.assertIn("bold: false", role_block)
        self.assertIn("height: 12", role_block)

        # Both the button-name and the chat title use the measured GohuFont
        # glyph gradient, while the selected button still uses solid magenta.
        # TextHashGlow still samples each actual rendered label.
        # GraphicalEffects and QtQuick.Shapes both export RadialGradient,
        # but only the Shapes type provides centerX/focalY. An unqualified
        # import silently selects the wrong one and Quickshell refuses to load.
        self.assertIn("import QtQuick.Shapes", name)
        self.assertIn("import Qt5Compat.GraphicalEffects as Effects", name)
        self.assertNotIn("import Qt5Compat.GraphicalEffects" + chr(10), name)
        self.assertIn("Effects.OpacityMask {", name)
        self.assertIn("focalY: centerY", name)
        self.assertIn("import QtQuick.Shapes", ring)
        self.assertNotIn("import Qt5Compat.GraphicalEffects", ring)
        self.assertIn("GohuText {", name)
        self.assertIn("text: root.text", name)
        self.assertIn("textFormat: Text.PlainText", name)
        self.assertIn("elide: Text.ElideRight", name)
        self.assertIn("OpacityMask {", name)
        self.assertIn("source: radialInk", name)
        self.assertIn("maskSource: inkMask", name)
        self.assertIn("fillGradient: RadialGradient {", name)
        self.assertIn("centerX: root.accentTopRight ? root.visibleGlyphWidth : 0", name)
        self.assertIn("GradientStop { position: 0.0; color: root.accentColor }", name)
        self.assertIn("GradientStop { position: 1.0; color: root.baseColor }", name)
        # Maple has red accent anchored to the upper-left and orange
        # base progressing rightward in both the name and button border.
        self.assertIn("GradientStop { position: 0.0; color: root.accentColor }", ring)
        self.assertIn("GradientStop { position: 1.0; color: root.baseColor }", ring)
        self.assertNotIn("id: rightInk", name)
        self.assertNotIn("fillGradient: LinearGradient {", name)
        self.assertIn("Math.min(width, gradientMeasure.implicitWidth)", name)
        self.assertIn("visibleGlyphWidth * 0.58", name)
        self.assertIn("Math.max(19", name)
        self.assertIn("centerY: root.height * 0.36", name)
        self.assertIn("property string gradientText: text", name)
        self.assertIn("text: root.gradientText", name)
        self.assertNotIn("visibleGlyphWidth * 0.42", name)
        self.assertIn("color: root.accentColor", name)
        self.assertIn("color: root.baseColor", name)
        self.assertNotIn("MouseArea {", name)
        self.assertNotIn("Process {", name)

    def test_header_rescan_reuses_reload_without_host_activation(self):
        view = (ROOT / "widgets/ForestW.qml").read_text()
        reload_button = (ROOT / "components/ReloadButton.qml").read_text()
        self.assertIn("ReloadButton {", view)
        self.assertIn("id: headerRescanButton", view)
        self.assertIn("id: headerStatusControls", view)
        self.assertIn("anchors.right: headerStatusControls.left", view)
        self.assertIn("anchors.right: closeButton.left", view)
        self.assertIn("width: headerRescanButton.width + 7 + liveIndicator.width", view)
        self.assertIn("anchors.left: parent.left", view)
        self.assertIn("anchors.left: headerRescanButton.right", view)
        self.assertIn("anchors.leftMargin: 7", view)
        # The two controls occupy a single cluster with explicit left-to-right order.
        cluster = view.split("id: headerStatusControls", 1)[1].split(
            "id: closeButton", 1)[0]
        self.assertLess(cluster.index("id: headerRescanButton"),
                        cluster.index("id: liveIndicator"))
        self.assertIn("interactive: root.menuOpen && !localInventory.scanning", view)
        self.assertIn("onReloadRequested: {", view)
        block = view.split("id: headerRescanButton", 1)[1].split(
            "// LIVE describes only the Quickshell workspace", 1)[0]
        self.assertIn("localInventory.scanModels();", block)
        self.assertIn('root.pendingModelScan = "";', block)
        self.assertNotIn("session", block.lower().replace("model inventory scan in progress", ""))
        self.assertIn('label: "⟳"', reload_button)

    def test_tree_chat_header_shows_active_icon_and_glow(self):
        view = (ROOT / "widgets/ForestW.qml").read_text()
        self.assertIn("id: chatHeadingRow", view)
        self.assertIn("id: activeChatTreeIcon", view)
        self.assertIn("source: Qt.resolvedUrl(root.activeTree.iconPath)", view)
        self.assertIn("safeSource: activeChatTreeIcon", view)
        self.assertIn("foregroundColor: root.activeTree.identityColor", view)
        self.assertIn("preferredGlowColor: root.activeTree.iconIdleGlowColor", view)
        self.assertIn('text: root.activeTree.name + " // CHAT"', view)
        self.assertIn("id: treeSelectorRepeater", view)
        self.assertIn("treeSelectorRepeater.itemAt(selectedTreeIndex)", view)
        self.assertIn("id: chatHeadingGlow", view)
        self.assertIn("safeSource: chatHeading", view)
        self.assertIn("foregroundColor: chatHeading.baseColor", view)
        self.assertIn("baseColor: root.activeTree.identityColor", view)
        self.assertIn('gradientText: root.activeTree.name + " // CHAT"', view)
        self.assertIn("accentColor: root.activeTree.gradientAccentColor", view)
        self.assertIn("preferredGlowColor: root.activeTree.spiritualIdleGlowColor", view)
        self.assertIn('text: root.activeTree.name + " // CHAT"', view)
        self.assertIn('gradientText: root.activeTree.name + " // CHAT"', view)
        self.assertNotIn("gradientText: root.activeTree.name" + chr(10), view)
        self.assertNotIn("root.selectedTreeButton.foregroundColor", view)
        self.assertNotIn("root.selectedTreeButton.contentGlowColor", view)
        self.assertIn("radius: 7", view)
        self.assertIn("samples: 13", view)
        self.assertIn("anchors.top: chatHeadingRow.bottom", view)
        self.assertNotIn("anchors.top: chatHeading.bottom", view)

    def test_forest_chat_list_uses_social_rail_recipe_without_fake_sessions(self):
        view = (ROOT / "widgets/ForestW.qml").read_text()
        rail = (ROOT / "widgets/ForestChatList.qml").read_text()
        social = (ROOT / "widgets/messanger/ContactList.qml").read_text()
        self.assertIn("readonly property var activeChatSessions: []", view)
        self.assertIn("id: activeChatRail", view)
        self.assertIn("hostConnected: root.chatHostTrusted", view)
        self.assertIn("sessions: root.activeChatSessions", view)
        self.assertIn("anchors.left: activeChatRail.right", view)
        self.assertIn("width: root.chatListWidth", view)
        self.assertIn("visible: width > 0", view)
        self.assertIn("frameWidth >= 800 ? 184 : frameWidth >= 680 ? 148 : 0", view)
        for required in ("ListView {", "NeonScrollBar {",
                         'handleStyle: "star"', "accountForContentOrigin: true"):
            self.assertIn(required, social)
            self.assertIn(required, rail)
        self.assertIn("model: chatListRoot.hostConnected ? chatListRoot.sessions : []", rail)
        self.assertIn('"NO ACTIVE CHATS', rail)
        self.assertIn("TRUSTED CHAT HOST NOT CONNECTED", rail)
        self.assertIn("textFormat: Text.PlainText", rail)
        self.assertNotIn("ContactList {", view)
        self.assertNotIn("Process {", rail)
        self.assertNotIn("MouseArea {", rail)
        # With the rail visible, the existing locked composer stays usable.
        for frame_width in (680, 800, 930):
            side = min(204, max(144, round(frame_width * 0.31)))
            rail_width = 184 if frame_width >= 800 else 148
            prompt = frame_width - side - rail_width - 12 - 4 - 46 - 7
            send = max(54, min(86, round(prompt * 0.21)))
            box = prompt - send - 6
            mic = max(28, min(34, round(box * 0.16)))
            # Removing the tiny dial restores prompt width even with the
            # 46px shared SelectorSlider host reserved at the chat right.
            local_draft = box - 11 - 6 - mic - 4 - 39 - 4
            self.assertGreaterEqual(local_draft, 100)

    def test_forest_section_dividers_use_grassy_green(self):
        view = (ROOT / "widgets/ForestW.qml").read_text()
        rail = (ROOT / "widgets/ForestChatList.qml").read_text()
        # Only 1px section dividers change; individual status colors and
        # product-specific button borders retain their established grammar.
        self.assertEqual(view.count("height: 1\n                color: Colors.green"), 3)
        self.assertEqual(view.count("width: 1\n                color: Colors.green"), 1)
        self.assertNotIn("height: 1\n                color: Colors.cyan", view)
        self.assertNotIn("width: 1\n                color: Colors.cyan", view)
        self.assertIn("height: 1\n            color: Colors.green", rail)
        self.assertIn("width: 1\n        color: Colors.green", rail)
        self.assertNotIn("height: 1\n            color: Colors.cyan", rail)
        self.assertNotIn("width: 1\n        color: Colors.cyan", rail)

    def test_reasoning_selector_slider_uses_git_hospital_shared_control(self):
        view = (ROOT / "widgets/ForestW.qml").read_text()
        selector = (ROOT / "components/SelectorSlider.qml").read_text()
        git = (ROOT / "widgets/GitW.qml").read_text()
        hospital = (ROOT / "widgets/HospitalW.qml").read_text()

        # The selector is the same shared hardware used by Git/Hospital.
        # Forest remains the only changed owner; shared source is unchanged.
        self.assertEqual(view.count("SelectorSlider {"), 1)
        self.assertEqual(view.count("IndexRail {"), 0)
        self.assertIn("SelectorSlider {", git)
        self.assertIn("SelectorSlider {", hospital)
        self.assertNotIn("ForestReasoningDial {", view)
        self.assertFalse((ROOT / "widgets/ForestReasoningDial.qml").exists())
        self.assertFalse((ROOT / "widgets/ForestReasoningDialPolicy.js").exists())

        self.assertIn("id: reasoningRailHost", view)
        self.assertIn("id: reasoningSelectorSlider", view)
        self.assertIn("enabled: root.menuOpen", view)
        self.assertIn("anchors.top: chatDivider.bottom", view)
        self.assertIn("anchors.bottom: promptRow.bottom", view)
        self.assertIn("anchors.right: parent.right", view)
        self.assertIn("anchors.right: reasoningRailHost.left", view)
        self.assertIn("anchors.rightMargin: 35", view)  # labels clear chat
        self.assertIn("width: 46", view)                 # composer unchanged
        self.assertIn("width: 40", view)                 # real slider width
        self.assertIn('selectorProfile: "index"', view)
        self.assertIn('indexInteraction: "legacy"', view)
        self.assertIn("count: 4", view)
        self.assertIn("currentIndex: 3 - root.selectedReasoningStep", view)
        self.assertIn("root.chooseTreeReasoningStep(3 - index);", view)
        self.assertIn('optionLabels: ["HIGH", "MED", "LOW", "NONE"]', view)
        self.assertIn('model: ["HIGH", "MED", "LOW", "NONE"]', view)
        self.assertIn("anchors.right: reasoningSelectorSlider.left", view)
        self.assertIn("reasoningRailHost.detentCenterY(index)", view)
        self.assertIn('sideLabel: "THINK"', view)
        self.assertIn("accentColor: Colors.cyan", view)
        self.assertIn("handleGlowColor: Colors.magenta", view)
        self.assertIn("enabledSlider: root.menuOpen", view)
        self.assertIn("selectedTreeReasoningSteps: [0, 0, 0, 0, 0]", view)
        self.assertIn("steps[selectedTreeIndex] = step", view)
        self.assertIn("selectedTreeReasoningSteps = steps", view)
        self.assertIn("readonly property bool chatHostTrusted: false", view)
        self.assertIn("readonly property bool voiceHostTrusted: false", view)
        self.assertNotRegex(view, r"(?m)^\s*onPrimaryRequested\s*:")
        self.assertNotRegex(view, r"(?m)^\s*onToggleRequested\s*:")

        # These markers come from the real SelectorSlider implementation.
        for source in (
            "property int count: 0", "property int currentIndex: -1",
            "signal indexRequested(int index)", "function indexFromHandleY(handleY)",
            "Math.round(fraction * (count - 1))",
            "function handleYForIndex(index)",
            "width: 40", "height: 52", "width: 28",
            "color: dragArea.pressed ? Colors.yellow : Colors.white",
            "slider.handleGlowColor",
            "onWheel: function(wheel)",
        ):
            self.assertIn(source, selector)

        # The top is HIGH; the bottom is NONE, matching both the bound
        # currentIndex and the four fixed Gohu labels.
        levels = ["NONE", "LOW", "MED", "HIGH"]
        labels_top_to_bottom = ["HIGH", "MED", "LOW", "NONE"]
        for rail_index, label in enumerate(labels_top_to_bottom):
            step = 3 - rail_index
            self.assertEqual(levels[step], label)
            self.assertEqual(3 - step, rail_index)
        for height in (190, 245, 310):
            track_height = height - 64  # SelectorSlider top 38 / bottom 26
            handle_height = 52
            travel = max(0, track_height - handle_height)
            self.assertGreater(travel, 0)
            centers = [38 + handle_height / 2 + travel * i / 3
                       for i in range(4)]
            self.assertEqual(centers, sorted(centers))
            self.assertGreaterEqual(centers[0], 38)
            self.assertLessEqual(centers[-1], height - 26)

    def test_forest_prompt_reuses_voice_and_ask_send_without_permissions(self):
        view = (ROOT / "widgets/ForestW.qml").read_text()
        voice = (ROOT / "components/VoiceToTextButton.qml").read_text()
        action = (ROOT / "components/AskSendButton.qml").read_text()
        workflow = (ROOT / ".github/workflows/forestw-v0.yml").read_text()

        self.assertIn('import "../components"', view)
        self.assertIn("readonly property bool voiceHostTrusted: false", view)
        self.assertIn("readonly property bool chatHostTrusted: false", view)
        self.assertEqual(view.count("VoiceToTextButton {"), 1)
        self.assertEqual(view.count("AskSendButton {"), 1)
        self.assertIn("id: voiceToTextButton", view)
        # The original speaking glyph and glyph glow stay enabled. Binding
        # the glow to ActionButton's anchored content layer avoids sampling
        # a centered glyph whose mapped x/y can become stale on resize.
        forest_voice = view.split("VoiceToTextButton {", 1)[1].split("\n                }", 1)[0]
        self.assertIn("glyphGlowEnabled: true", forest_voice)
        self.assertIn("contentGlowSource: contentItem", forest_voice)
        self.assertNotIn("voiceGlyph:", forest_voice)
        self.assertIn('property string voiceGlyph: "🗣︎"', voice)
        button = (ROOT / "components/ActionButton.qml").read_text()
        self.assertIn("default property alias contentData: contentHost.data", button)
        self.assertIn("property alias contentItem: contentHost", button)
        self.assertIn("id: forestAskSendButton", view)
        self.assertIn("id: modelPickerButton", view)
        # Prompt is an idle-cyan / hover-orange / focus-magenta text field;
        # both controls remain nested inside it. SEND is adjacent and gated.
        inside = view.split("id: sendGate", 1)[1].split(
            "id: forestAskSendButton", 1)[0]
        self.assertIn("id: forestPromptInput", inside)
        self.assertIn("VoiceToTextButton {", inside)
        self.assertIn("DockButton {", inside)
        self.assertIn("id: modelPickerButton", inside)
        self.assertIn("anchors.right: modelPickerButton.left", inside)
        self.assertNotIn("ForestReasoningDial {", inside)
        self.assertNotIn("id: reasoningStepDial", inside)
        self.assertIn("anchors.right: modelPickerButton.left", inside)
        self.assertIn("id: reasoningSelectorSlider", view)
        self.assertIn("anchors.right: reasoningRailHost.left", view)
        self.assertIn("readonly property color promptBorderColor:", inside)
        self.assertIn("forestPromptInput.activeFocus ? Colors.magenta", inside)
        self.assertIn(": promptHover.hovered ? Colors.orange : Colors.cyan", inside)
        self.assertIn("border.width: forestPromptInput.activeFocus ? 2 : 1", inside)
        self.assertIn("border.color: promptBorderColor", inside)
        self.assertIn("HoverHandler {", inside)
        self.assertIn("id: promptHover", inside)
        self.assertIn("enabled: root.menuOpen", inside)
        field = inside.split("TextInput {", 1)[1].split("GohuText {", 1)[0]
        self.assertIn('font.family: "GohuFont 11 Nerd Font Mono"', field)
        self.assertIn("font.pixelSize: 16", field)
        self.assertIn("height: parent.height - 8", field)
        self.assertIn("anchors.verticalCenter: parent.verticalCenter", field)
        self.assertIn("verticalAlignment: TextInput.AlignVCenter", field)
        self.assertIn("color: Colors.magenta", field)
        self.assertIn("selectionColor: Colors.magenta", field)
        self.assertIn("selectedTextColor: Colors.black", field)
        self.assertIn("cursorDelegate: Rectangle {", field)
        self.assertIn("width: 3", field)
        self.assertIn("color: Colors.orange", field)
        # A custom Qt TextInput cursorDelegate tracks cursorRectangle
        # position/height. Do not pin its y to a fixed pixel offset.
        self.assertNotIn("cursorDelegate: Rectangle {\n                            y:", field)
        self.assertIn("height: forestPromptInput.height", inside)
        self.assertIn("verticalAlignment: Text.AlignVCenter", inside)
        self.assertIn("font.pixelSize: 11", inside)
        self.assertIn("enabled: root.menuOpen", inside)
        self.assertIn("In-memory draft only.", inside)
        self.assertIn("anchors.left: forestPromptInput.left", inside)
        self.assertIn("forestPromptInput.text.length === 0", inside)
        self.assertIn("if (forestPromptInput)", view)
        self.assertIn("forestPromptInput.clear();", view)
        self.assertNotRegex(view, r"(?m)^\s*onAccepted\s*:")
        self.assertIn("anchors.right: voiceToTextButton.left", view)
        self.assertIn("anchors.right: forestAskSendButton.left", view)
        self.assertIn("anchors.right: modelPickerButton.left", view)
        self.assertIn("anchors.right: parent.right", view)
        self.assertIn("available: root.voiceHostTrusted && !processing", view)
        self.assertIn("enabledAction: root.chatHostTrusted", view)
        self.assertIn("backendReady: root.voiceHostTrusted", view)
        self.assertIn("busy: false", view)
        self.assertIn("recording: false", view)
        self.assertIn("allowSecondaryAction: false", view)
        self.assertIn('askLabel: "SEND"', view)
        self.assertIn('sendLabel: "SEND"', view)
        self.assertIn("VOICE LOCKED // TRUSTED FOREST AUDIO HOST NOT CONNECTED", view)
        self.assertIn("SEND LOCKED // TRUSTED FOREST CHAT HOST NOT CONNECTED", view)
        self.assertIn("SEND LOCKED // HOST NOT CONNECTED", view)
        self.assertIn("SEND LOCKED // B4 TRUSTED HOST NOT CONNECTED", view)
        self.assertNotRegex(view, r"(?m)^\s*onToggleRequested\s*:")
        self.assertNotRegex(view, r"(?m)^\s*onPrimaryRequested\s*:")
        self.assertNotRegex(view, r"(?m)^\s*onSecondaryRequested\s*:")
        self.assertNotIn("HospitalSpeechInputService {", view)
        self.assertNotIn("HospitalLiveDictationService {", view)
        self.assertNotIn("onClicked: root.submit", view)
        self.assertIn("signal toggleRequested()", voice)
        self.assertIn("available: !processing", voice)
        self.assertIn("signal primaryRequested()", action)
        self.assertIn("signal secondaryRequested()", action)
        self.assertIn("available: enabledAction", action)
        for path in ("components/VoiceToTextButton.qml",
                     "components/AskSendButton.qml"):
            self.assertEqual(workflow.count(path), 2)

        # First three stages retain 930px width; only the fourth expands.
        for frame_width in (930, 930, 930, 1884):
            side = min(204, max(144, round(frame_width * 0.31)))
            rail_width = 184 if frame_width >= 800 else 148
            row = frame_width - side - rail_width - 12 - 4 - 46 - 7
            send = max(54, min(86, round(row * 0.21)))
            box = row - send - 6
            mic = max(28, min(34, round(box * 0.16)))
            # Removing the tiny dial restores prompt width even with the
            # 46px shared SelectorSlider host reserved at the chat right.
            local_draft = box - 11 - 6 - mic - 4 - 39 - 4
            self.assertGreaterEqual(local_draft, 100)

    def test_b0_inventory_ui_is_explicit_and_fail_closed(self):
        view = (ROOT / "widgets/ForestW.qml").read_text()
        adapter = (ROOT / "services/forest/ForestInventoryAdapter.qml").read_text()
        policy = (ROOT / "services/forest/ForestInventoryPolicy.js").read_text()
        self.assertIn("ForestInventoryAdapter {", view)
        self.assertIn("localInventory.scanModels();", view)
        self.assertIn("id: scanAllButton", view)
        self.assertIn("SEND LOCKED // B4 TRUSTED HOST NOT CONNECTED", view)
        self.assertIn("B1 / B2 / B3 READY AS CONTRACTS", view)
        self.assertIn("running: false", adapter)
        self.assertIn('Quickshell.shellPath("scripts/forest/ollama_inventory.py")', adapter)
        self.assertIn('"list-models"', adapter)
        self.assertNotIn("ollama_chat_transport", adapter)
        self.assertNotIn("session_journal_v0", adapter)
        self.assertNotIn("Quickshell.execDetached", adapter)
        self.assertIn("generation_enabled !== false", policy)
        self.assertIn("model_count !== value.models.length", policy)
        self.assertIn("id: sessionPreview", view)
        self.assertIn("anchors.top: chatDivider.bottom", view)
        self.assertIn("anchors.bottom: promptRow.top", view)
        self.assertIn("clip: true", view)
        self.assertIn("id: sendGate", view)
        self.assertIn("id: promptRow", view)
        self.assertIn('visible: root.frameHeight >= 540', view)
        self.assertIn('MODEL LIST READY // CHAT HOST NOT CONNECTED', view)
        self.assertIn('SEND LOCKED // HOST NOT CONNECTED', view)
        self.assertIn('Accessible.name: "Scan local Ollama models, read-only"', view)
        self.assertIn('Accessible.name: "Open Forest model selector"', view)
        self.assertNotIn("id: modelStrip", view)
        self.assertNotIn("id: nextModelButton", view)
        # Popups are bounded to the local chat panel even at the 340px stage.
        for height in (610, 790, 790, 1051):
            chat_height = height - 56 - 30
            prompt_top = chat_height - 13 - 40
            popup_height = max(120, min(360, prompt_top - 42))
            popup_top = prompt_top - 6 - popup_height
            self.assertGreaterEqual(popup_top, 35)
            self.assertGreaterEqual(popup_height, 120)

        self.assertIn("InventoryPolicy.beginScan()", adapter)
        self.assertIn("InventoryPolicy.captureStdoutScan(", adapter)
        self.assertIn("InventoryPolicy.captureStderrScan(", adapter)
        self.assertIn("InventoryPolicy.captureExitScan(", adapter)
        self.assertIn("models = scanState.accepted ? scanState.models : []", adapter)
        self.assertIn("if (!s.stdoutSeen || !s.stderrSeen || !s.exitSeen)", policy)
        self.assertIn("s.exitStatus !== 0", policy)
        self.assertNotIn("Qt.callLater(function() { inventory.complete(); })", adapter)
        self.assertTrue((ROOT / "scripts/forest/ollama_inventory.py").is_file())
        self.assertNotIn("Component.onCompleted", adapter)
        self.assertNotIn("running: true", adapter)

        node = r'''
const fs=require("fs"), vm=require("vm");
const ctx={}; vm.runInNewContext(fs.readFileSync(process.argv[1], "utf8"),ctx);
const base={schema_version:1,provider:"ollama",status:"REACHABLE",
 models:[{name:"qwen3:1.7b",size_bytes:1024}],model_count:1,
 capabilities:["list_models"],generation_enabled:false,tools_enabled:false,sessions_enabled:false};
const parse=o=>ctx.parseInventory(JSON.stringify(o));
if (!parse(base).valid || parse(base).models[0].name!=="qwen3:1.7b")process.exit(1);
for(const x of [
 {...base,generation_enabled:true},{...base,sessions_enabled:true},
 {...base,tools_enabled:true},{...base,model_count:2},
 {...base,capabilities:["list_models","generate"]},
 {...base,models:[{name:"bad name",size_bytes:1}]},
 {...base,provider:"cloud"},
 {...base,models:[{name:"a",size_bytes:1},{name:"a",size_bytes:2}],model_count:2}
])if(parse(x).valid)process.exit(2);
const unavailable={...base,status:"UNAVAILABLE",models:[],model_count:0,capabilities:[],reason:"OLLAMA_UNAVAILABLE"};
if(!parse(unavailable).valid || parse(unavailable).status!=="UNAVAILABLE")process.exit(3);
if(ctx.parseInventory("not-json").valid)process.exit(4);
'''
        result = subprocess.run(
            ["node", "-e", node, str(ROOT / "services/forest/ForestInventoryPolicy.js")],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        # All 6 event orders must defer publication until the final event.
        event_orders = r"""
const fs = require("fs"), vm = require("vm");
const ctx = {}; vm.runInNewContext(fs.readFileSync(process.argv[1], "utf8"),ctx);
const output = JSON.stringify({
  schema_version: 1, provider: "ollama", status: "REACHABLE",
  models: [{name:"qwen3:1.7b",size_bytes:100}], model_count:1,
  capabilities:["list_models"], generation_enabled:false,
  tools_enabled:false, sessions_enabled:false
});
const unavailable = JSON.stringify({
  schema_version:1, provider:"ollama", status:"UNAVAILABLE",
  models:[],model_count:0,capabilities:[],generation_enabled:false,
  tools_enabled:false,sessions_enabled:false,reason:"OLLAMA_UNAVAILABLE"
});
const events = {
  o:s=>ctx.captureStdoutScan(s,output),
  e:s=>ctx.captureStderrScan(s,""),
  x:s=>ctx.captureExitScan(s,0,0)
};
const permutations = [
  "oex","oxe","eox","exo","xoe","xeo"
];
for(const order of permutations) {
  let s = ctx.beginScan();
  for(let i=0;i<3;i++) {
    s=events[order[i]](s);
    if(i<2 && (s.complete || s.accepted || s.models.length))process.exit(10);
  }
  if(!s.complete||!s.accepted||s.status!=="REACHABLE"||s.models.length!==1)
    process.exit(11);
  if(ctx.captureStdoutScan(s,output).models.length!==1)process.exit(12);
}
const failures=[
  ["stderr",["o","e","x"],(s,k)=> k==="e" ? ctx.captureStderrScan(s,"unexpected") : events[k](s)],
  ["nonzero",["o","e","x"],(s,k)=> k==="x" ? ctx.captureExitScan(s,2,0) : events[k](s)],
  ["crash",["o","e","x"],(s,k)=> k==="x" ? ctx.captureExitScan(s,0,1) : events[k](s)],
  ["badjson",["x","o","e"],(s,k)=> k==="o" ? ctx.captureStdoutScan(s,"not-json") : events[k](s)],
  ["dup",["o","o","e","x"],(s,k)=> events[k](s)]
];
for(const [label,seq,fn] of failures) {
  let s=ctx.beginScan();
  for(const k of seq) s=fn(s,k);
  if(!s.complete||s.accepted||s.models.length||s.status!=="UNAVAILABLE")
    process.exit(20);
}
let s=ctx.beginScan();
s=ctx.captureExitScan(s,2,0);
s=ctx.captureStderrScan(s,"");
s=ctx.captureStdoutScan(s,unavailable);
if(!s.complete||!s.accepted||s.status!=="UNAVAILABLE"
   ||s.reason!=="OLLAMA_UNAVAILABLE"||s.models.length)process.exit(30);
"""
        result = subprocess.run(
            ["node", "-e", event_orders,
             str(ROOT / "services/forest/ForestInventoryPolicy.js")],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_prompt_anchored_model_popup_and_truthful_statuses(self):
        view = (ROOT / "widgets/ForestW.qml").read_text()
        self.assertIn('text: "❦︎๋࣭"', view)
        self.assertIn('text: "⊹"', view)
        self.assertIn('text: "⭑"', view)
        self.assertNotIn('text: "๋࣭⭑"', view)
        self.assertIn("clip: false", view)
        self.assertIn("boundsBehavior: Flickable.StopAtBounds", view)
        self.assertIn("id: modelPickerArt", view)
        self.assertIn("id: pickerFlower", view)
        self.assertIn("id: pickerLeftStar", view)
        self.assertIn("id: pickerRightStars", view)
        self.assertIn("id: modelPickerButton", view)
        self.assertIn("open: root.modelPopupOpen", view)
        self.assertIn("acceptedButtons: Qt.LeftButton", view)
        self.assertIn("normalForegroundColor: Colors.green", view)
        self.assertIn("hoverForegroundColor: Colors.green", view)
        self.assertIn("pressedForegroundColor: Colors.green", view)
        self.assertIn("openForegroundColor: Colors.magenta", view)
        self.assertIn("normalDockGlowColor: Colors.green", view)
        self.assertIn("hoverDockGlowColor: Colors.green", view)
        self.assertIn("pressedDockGlowColor: Colors.green", view)
        self.assertIn("openGlowColor: Colors.magenta", view)
        self.assertIn("normalContentGlowColor: Colors.green", view)
        self.assertIn("hoverContentGlowColor: Colors.green", view)
        self.assertIn("pressedContentGlowColor: Colors.green", view)
        self.assertIn("contentGlowSource: pickerFlower", view)
        self.assertIn("trackArtworkGlowLocally: true", view)
        self.assertIn("border.color: dockGlowColor", view)
        self.assertIn("modelPickerButton.open ? Colors.magenta : Colors.white", view)
        self.assertEqual(view.count("color: modelPickerButton.pickerStarColor"), 2)
        self.assertIn("color: modelPickerButton.foregroundColor", view)
        self.assertNotIn("safeSource: pickerFlower", view)
        dock = (ROOT / "components/DockButton.qml").read_text()
        self.assertIn("readonly property bool hovered:", dock)
        self.assertIn("readonly property color dockGlowColor: open", dock)
        self.assertIn("readonly property color foregroundColor: open", dock)
        self.assertIn("readonly property real contentGlowOpacity: open", dock)
        self.assertIn("color: open ? openFillColor : closedFillColor", dock)
        self.assertIn("textFormat: Text.PlainText", view)
        self.assertIn("id: modelPickerButton", view)
        self.assertIn("anchors.right: modelPickerButton.left", view)
        self.assertIn("onLeftClicked: root.modelPopupOpen = !root.modelPopupOpen", view)
        self.assertIn("onModelPopupOpenChanged:", view)
        self.assertIn("if (modelPopupOpen)", view)
        self.assertIn("if (!localInventory.scanning)", view)
        self.assertIn("localInventory.scanModels();", view)
        self.assertNotIn("onMenuOpenChanged: localInventory.scanModels()", view)
        self.assertIn("id: closeModelPopupButton", view)
        self.assertIn("CloseButton {\n                        id: closeModelPopupButton", view)
        self.assertIn("width: 24", view)
        self.assertIn("onCloseRequested: root.modelPopupOpen = false", view)
        # The popup uses the same ordinary red close control as other
        # Post-Apollo menus, at a reduced size.
        close = (ROOT / "components/CloseButton.qml").read_text()
        self.assertIn('label: "×"', close)
        self.assertIn("accentColor: Colors.red", close)
        self.assertIn("hoverFillColor: Colors.yellow", close)
        self.assertIn("idleContentGlowColor: Colors.red", close)
        self.assertIn("height: width * 16 / 17", close)
        self.assertIn("anchors.bottom: promptRow.top", view)
        self.assertIn("anchors.right: promptRow.right", view)
        self.assertIn("width: Math.min(390, chatPane.width - 24)", view)
        self.assertIn("id: dismissModelPopup", view)
        self.assertIn("id: modelPopup", view)
        self.assertIn("id: modelList", view)
        self.assertIn("clip: true", view)
        self.assertIn("boundsBehavior: Flickable.StopAtBounds", view)
        self.assertIn('text: "FOREST // MODELS"', view)
        self.assertIn('text: "FOUND"', view)
        self.assertIn('text: "LIVE ?"', view)
        self.assertIn('text: "ACCESS ?"', view)
        self.assertIn("SCAN = INVENTORY ONLY // LIVE & ACCESS UNVERIFIED", view)
        self.assertIn("onClicked: root.scanModel(modelEntry.modelName)", view)
        self.assertIn("onClicked: root.chooseLocalModel(modelEntry.modelName)", view)
        self.assertIn("property var selectedTreeModels:", view)
        self.assertIn("choices[selectedTreeIndex] = name", view)
        self.assertIn("onSelectedTreeIndexChanged: modelPopupOpen = false", view)
        self.assertIn("if (root.modelPopupOpen)", view)
        self.assertIn("root.lastModelScanResult", view)
        # No live/readiness/permission claims are set from B0 model names.
        self.assertNotIn('text: "ACCEPTED"', view)
        self.assertNotIn('text: "LIVE"', view[view.index("id: modelPopup"):])
        self.assertNotIn("modelPickerButton: true", view)
        self.assertNotIn("ollama_chat_transport", view)
        self.assertNotIn("host_admission_b4a", view)

    def test_live_status_is_between_resize_and_close(self):
        text = (ROOT / "widgets/ForestW.qml").read_text()
        first = text.index("id: expandButton")
        middle = text.index("id: liveIndicator")
        last = text.index("id: closeButton")
        self.assertLess(first, middle)
        self.assertLess(middle, last)
        self.assertIn("anchors.right: headerStatusControls.left", text)
        self.assertIn("anchors.left: headerRescanButton.right", text)
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

    def test_green_outer_frame_and_git_fullscreen_cap(self):
        view = (ROOT / "widgets/ForestW.qml").read_text()
        shell = (ROOT / "shell.qml").read_text()
        policy = (ROOT / "widgets/ForestChassisPolicy.js").read_text()
        self.assertIn("borderColor: Colors.green", view)
        self.assertIn("glowColor: Colors.green", view)
        self.assertIn("gitFullscreenReference: gitWindow", shell)
        self.assertIn("gitFullscreenReference.visualBottomY", view)
        self.assertIn("gitFullscreenReference.glowGutter", view)
        self.assertIn("gitFullscreenWidthCap, gitFullscreenHeightCap", view)
        self.assertIn("{ width: 930, height: 610 }", policy)
        self.assertIn("{ width: 930, height: 790 }", policy)
        self.assertIn("{ width: 930, height: 99999 }", policy)
        self.assertIn("{ width: 99999, height: 99999 }", policy)
        self.assertIn("visible: root.frameHeight >= 540", view)
        self.assertIn("text: root.frameHeight < 540", view)
        self.assertIn("gitWidth", policy)
        self.assertIn("gitHeight", policy)

    def test_geometry_script(self):
        script = ROOT / "tests/forest/forest_geometry_test.cjs"
        result = subprocess.run(["node", str(script)], text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=10, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
