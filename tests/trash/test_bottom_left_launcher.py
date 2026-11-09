"""Read-only source contracts for the first bottom-left Trash launcher.

These tests never invoke Quickshell, GIO or filesystem deletion. Real visual
geometry, glyph rendering, focus and compositor behavior require operator review.
"""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
POWER = (ROOT / "modules" / "Power.qml").read_text(encoding="utf-8")
TRASH = (ROOT / "modules" / "Trash.qml").read_text(encoding="utf-8")
SHELL = (ROOT / "shell.qml").read_text(encoding="utf-8")
DOCK = (ROOT / "components" / "DockButton.qml").read_text(encoding="utf-8")


def number(source, name):
    match = re.search(r"\b" + re.escape(name) + r"\s*:\s*(\d+)", source)
    if match is None:
        raise AssertionError(f"Missing numeric QML property {name}")
    return int(match.group(1))


def section(source, before, after):
    return source.split(before, 1)[1].split(after, 1)[0]


class TrashBottomLeftLauncherTests(unittest.TestCase):
    def test_shell_mounts_one_bottom_left_trash_and_preserves_power(self):
        self.assertEqual(SHELL.count("    Trash {}"), 1)
        self.assertEqual(SHELL.count("    Power {}"), 1)
        self.assertLess(SHELL.index("    Trash {}"), SHELL.index("    Power {}"))
        self.assertIn("Tray {}", SHELL)
        self.assertIn("id: leftModules", SHELL)

    def test_mirror_power_real_geometry_not_window_size_guess(self):
        trash_anchor = section(TRASH, "    anchors {", "    margins {")
        power_anchor = section(POWER, "    anchors {", "    margins {")
        self.assertIn("bottom: true", trash_anchor)
        self.assertIn("left: true", trash_anchor)
        self.assertIn("right: false", trash_anchor)
        self.assertIn("bottom: true", power_anchor)
        self.assertIn("right: true", power_anchor)

        trash_margins = section(TRASH, "    margins {", "    implicitWidth:")
        power_margins = section(POWER, "    margins {", "    implicitWidth:")
        trash_button = section(TRASH, "        DockButton {", "            onLeftClicked:")
        power_button = section(POWER, "        DockButton {", "            onHoverEntered:")
        for key in ("implicitWidth", "implicitHeight"):
            self.assertEqual(number(TRASH, key), number(POWER, key))
        for key in ("width", "height", "y"):
            self.assertEqual(number(trash_button, key), number(power_button, key))
        self.assertEqual(number(trash_button, "width"), 50)
        self.assertEqual(number(trash_button, "height"), 50)

        left_gap = number(trash_margins, "left") + number(trash_button, "x")
        right_gap = (number(power_margins, "right")
                     + number(POWER, "implicitWidth")
                     - number(power_button, "x")
                     - number(power_button, "width"))
        self.assertEqual(left_gap, right_gap)
        self.assertEqual(left_gap, 25)

        trash_bottom = (number(trash_margins, "bottom")
                        + number(TRASH, "implicitHeight")
                        - number(trash_button, "y")
                        - number(trash_button, "height"))
        power_bottom = (number(power_margins, "bottom")
                        + number(POWER, "implicitHeight")
                        - number(power_button, "y")
                        - number(power_button, "height"))
        self.assertEqual(trash_bottom, power_bottom)
        self.assertEqual(trash_bottom, 20)

    def test_top_row_glow_strengths_and_independent_color_planes(self):
        self.assertIn("DockButton {", TRASH)
        self.assertIn("readonly property bool hovered:", DOCK)
        self.assertIn("readonly property bool pressed:", DOCK)
        self.assertIn("readonly property bool energized:", DOCK)
        self.assertIn("open: trashLauncher.menuOpen", TRASH)

        # The white glyph stays white while closed/hovered/pressed, then
        # follows the canonical yellow/magenta selected state.
        for field in (
            "normalForegroundColor", "hoverForegroundColor",
            "pressedForegroundColor"
        ):
            self.assertIn(field + ": Colors.white", TRASH)
        self.assertIn("openForegroundColor: Colors.magenta", TRASH)
        self.assertIn("openFillColor: Colors.yellow", TRASH)

        # The sampled glyph glow is a distinct Omnitrix-green layer.
        # The chassis is ordinary green; open overrides both to magenta.
        for field in (
            "normalContentGlowColor", "hoverContentGlowColor",
            "pressedContentGlowColor"
        ):
            self.assertIn(field + ": Colors.omnitrix", TRASH)
        for field in (
            "normalDockGlowColor", "hoverDockGlowColor",
            "pressedDockGlowColor"
        ):
            self.assertIn(field + ": Colors.green", TRASH)
        self.assertIn("openGlowColor: Colors.magenta", TRASH)
        self.assertIn('text: "♻︎"', TRASH)
        self.assertIn("contentGlowSource: trashGlyph", TRASH)
        self.assertIn("color: trashButton.foregroundColor", TRASH)

        # Inherit every numerical glow setting from the same DockButton
        # component used by the top-row AppLauncher/Camera modules.
        trash_button = section(TRASH, "        DockButton {", "            onLeftClicked:")
        for field in (
            "contentGlowIdleOpacity", "contentGlowHoverOpacity",
            "contentGlowPressedOpacity", "contentGlowOpenOpacity",
            "contentGlowIdleRadius", "contentGlowActiveRadius",
            "contentGlowHoverRadius", "contentGlowPressedRadius",
            "contentGlowOpenRadius", "contentGlowIdleSamples",
            "contentGlowActiveSamples", "contentGlowHoverSamples",
            "contentGlowPressedSamples", "contentGlowOpenSamples",
            "softGlowSpread", "softGlowIdleOpacity",
            "softGlowHoverOpacity", "softGlowPressedOpacity",
            "softGlowOpenOpacity", "wideGlowSpread",
            "wideGlowIdleOpacity", "wideGlowHoverOpacity",
            "wideGlowPressedOpacity", "wideGlowOpenOpacity"
        ):
            self.assertRegex(DOCK, r"\\b" + field + r"\\s*:")
            self.assertNotRegex(trash_button, r"\\b" + field + r"\\s*:")

    def test_ipc_handler_type_is_imported_before_use(self):
        # IpcHandler is exported by Quickshell.Io, not base Quickshell.
        # Missing this import prevents the entire shell from starting.
        self.assertIn("import Quickshell.Io", TRASH.split("PanelWindow {", 1)[0])
        self.assertIn("IpcHandler {", TRASH)
        self.assertIn("import Quickshell.Io", POWER.split("PanelWindow {", 1)[0])

    def test_open_close_mask_keyboard_and_placeholder_are_safe(self):
        self.assertIn("function toggle()", TRASH)
        self.assertIn("onLeftClicked: trashLauncher.toggle()", TRASH)
        self.assertIn('target: "trash"', TRASH)
        self.assertIn("WlrKeyboardFocus.Exclusive", TRASH)
        self.assertIn("WlrKeyboardFocus.None", TRASH)
        self.assertIn("mask: Region {", TRASH)
        self.assertIn("item: trashButton", TRASH)
        self.assertIn("width: trashMenu.visible ? trashMenu.width : 0", TRASH)
        self.assertIn("height: trashMenu.visible ? trashMenu.height : 0", TRASH)
        self.assertIn("event.key === Qt.Key_Escape", TRASH)
        self.assertIn("trashLauncher.menuOpen = false", TRASH)
        self.assertIn('label: "X"', TRASH)
        self.assertIn('text: "TRASH // INDEX"', TRASH)
        self.assertIn("NO FILE ACTIONS IN THIS PREVIEW.", TRASH)
        self.assertNotRegex(
            TRASH, r"(?i)\bprocess\s*\{|\bgio\b|unlink\s*\("
            r"|\brm\s+-|\bsystemctl\b|\bshutil\b"
        )


if __name__ == "__main__":
    unittest.main()
