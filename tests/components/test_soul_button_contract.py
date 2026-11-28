import pathlib
import unittest
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[2]

class SoulButtonContract(unittest.TestCase):
    def test_shared_wrappers_and_registration(self):
        self.assertIn("SoulButton 1.0 SoulButton.qml", (ROOT / "components/qmldir").read_text())
        for p in ("components/InformationButton.qml", "widgets/appcontrol/ProcessInformationButton.qml"):
            s = (ROOT / p).read_text()
            self.assertIn("SoulButton {", s)
            self.assertNotIn("MouseArea", s)

    def test_native_input_and_glow(self):
        s = (ROOT / "components/SoulButton.qml").read_text()
        for fragment in ('ActionButton {', 'accentColor: Colors.yellow', 'showLabel: false',
                         'acceptedButtons: Qt.LeftButton', 'keyboardActivationSignal: "leftClicked"',
                         'contentGlowSource: soulArtwork'):
            self.assertIn(fragment, s)
        for plane in ("Content", "Soft"):
            for state in ("idle", "hover", "pressed", "selected", "keyboardSelected"):
                self.assertIn(f"{state}{plane}GlowColor: Colors.magenta", s)
        self.assertNotIn("MouseArea", s)
        self.assertNotIn("Timer {", s)

    def test_vector_artwork(self):
        root = ET.parse(ROOT / "assets/prism/soul-joy.svg").getroot()
        ns = {"s": "http://www.w3.org/2000/svg"}
        self.assertEqual(len(root.findall(".//s:rect", ns)), 10)
        self.assertFalse(root.findall(".//s:filter", ns))
        self.assertFalse(root.findall(".//s:image", ns))

if __name__ == "__main__":
    unittest.main()
