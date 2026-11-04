"""Camera line-icon contract. No image generation, raster assets or screenshot IO.

Source checks guard a true QtQuick.Shapes glyph with hollow/transparent
negative space, original orbit/star/compass details, and unchanged dock click.
Native QML rendering must still be verified on the user's Quickshell version.
"""
import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
ICON_PATH = ROOT / "components" / "CameraGlyph.qml"
DOCK_PATH = ROOT / "modules" / "Screenshot.qml"
PANEL_PATH = ROOT / "widgets" / "CameraW.qml"
SHELL_PATH = ROOT / "shell.qml"
COMPONENTS_QMLDIR_PATH = ROOT / "components" / "qmldir"


class CameraLineGlyphContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.icon = ICON_PATH.read_text(encoding="utf-8")
        cls.dock = DOCK_PATH.read_text(encoding="utf-8")
        cls.panel = PANEL_PATH.read_text(encoding="utf-8")
        cls.shell = SHELL_PATH.read_text(encoding="utf-8")
        cls.qmldir = COMPONENTS_QMLDIR_PATH.read_text(encoding="utf-8")

    def test_camera_glyph_is_exported_from_directory_import(self):
        # Screenshot.qml imports ../components as a directory, and the
        # directory owns a qmldir manifest. An unlisted QML file is not
        # a usable type, causing the entire shell.qml load to fail.
        self.assertIn('import "../components"', self.dock)
        declarations = [line.strip() for line in self.qmldir.splitlines()
                        if line.strip() and not line.lstrip().startswith("#")]
        self.assertEqual(declarations.count("CameraGlyph 1.0 CameraGlyph.qml"), 1)
        self.assertTrue(ICON_PATH.is_file())
        self.assertIn("CameraGlyph {", self.dock)

    def test_actual_reusable_qt_shape_without_raster_or_filled_camera(self):
        code = self.icon
        self.assertIn("import QtQuick.Shapes", code)
        self.assertIn("Shape {", code)
        self.assertIn("transform: Scale {", code)
        self.assertIn("xScale: glyph.width / 128", code)
        self.assertIn("yScale: glyph.height / 96", code)
        self.assertIn("ShapePath {", code)
        self.assertIn("PathSvg {", code)
        self.assertNotIn("Canvas {", code)
        self.assertNotIn("Image {", code)
        self.assertNotIn("source: ", code)
        self.assertNotIn("Rectangle {", code)
        self.assertNotIn("onPaint:", code)
        self.assertNotIn("fillGradient:", code)
        self.assertNotIn("fillItem:", code)
        self.assertNotIn("fillColor: Colors.black", code)
        self.assertNotIn("fillColor: Colors.white", code)
        self.assertNotIn('fillColor: "#', code)
        num_paths = code.count("ShapePath {")
        self.assertGreaterEqual(num_paths, 7)
        self.assertEqual(num_paths, code.count('fillColor: "transparent"'))
        self.assertEqual(num_paths, code.count("PathSvg {"))
        self.assertEqual(num_paths, code.count("strokeWidth:"))
        self.assertEqual(num_paths, code.count("strokeColor:"))

    def test_hollow_lens_compass_orbit_and_stars_retain_linework(self):
        code = self.icon
        # Three separate circle outlines with nonfilled centers.
        self.assertIn("A 26 26", code)
        self.assertIn("A 19 19", code)
        self.assertIn("A 13 13", code)
        # Compass reticle keeps four cardinal directions.
        self.assertIn("M 64 24 L 64 36", code)
        self.assertIn("M 64 70 L 64 82", code)
        self.assertIn("M 35 53 L 46 53", code)
        self.assertIn("M 82 53 L 93 53", code)
        # Orbit sweeps and four outlined sparkle paths, no filled flashes.
        self.assertIn("M 14 72 C 7 83", code)
        self.assertIn("M 14 72 C 7 67", code)
        self.assertIn("M 101 4 Q", code)
        self.assertIn("M 28 46 Q", code)
        self.assertIn("M 40 77 Q", code)
        self.assertIn("M 102 63 Q", code)
        self.assertIn("M 42 6 L", code)
        self.assertIn("M 119 81 L", code)

    def test_native_icon_in_existing_camera_module_not_an_emoji(self):
        self.assertIn("DockButton {", self.dock)
        self.assertIn('import "../components"', self.dock)
        self.assertIn("CameraGlyph {", self.dock)
        self.assertIn("id: cameraMark", self.dock)
        self.assertIn("contentGlowSource: cameraMark", self.dock)
        self.assertIn("bodyColor: cameraDock.foregroundColor", self.dock)
        self.assertIn("lensColor: cameraDock.menuOpen", self.dock)
        self.assertIn("ornamentColor: cameraDock.menuOpen", self.dock)
        self.assertIn('text: "CAM"', self.dock)
        self.assertIn("onLeftClicked: toggleRequested()", self.dock)
        self.assertNotIn('text: "📷︎"', self.dock)
        self.assertNotIn("NotoText {", self.dock)
        self.assertNotIn("Image {", self.dock)

    def test_keeps_camera_and_social_independently_mounted(self):
        self.assertIn("Screenshot {", self.shell)
        self.assertIn("CameraW {", self.shell)
        self.assertIn("onToggleRequested: cameraWindow.toggle()", self.shell)
        self.assertIn("id: messagingWindow", self.shell)
        self.assertIn("function prepareCapture(mode)", self.panel)
        self.assertIn("function previewCleanup()", self.panel)
        self.assertIn("function confirmCleanup()", self.panel)


if __name__ == "__main__":
    unittest.main()
