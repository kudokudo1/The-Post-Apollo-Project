"""Guard the shared QML registry used by FinanceW's content keyboard navigation."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "components" / "qmldir"
COMPONENT = ROOT / "components" / "WidgetContentKeyboardNavigator.qml"
FINANCE = ROOT / "widgets" / "FinanceW.qml"
REGISTRATION = (
    "WidgetContentKeyboardNavigator 1.0 WidgetContentKeyboardNavigator.qml"
)


class WidgetContentNavigatorRegistrationTests(unittest.TestCase):
    def test_navigator_registered_once_and_file_exists(self):
        lines = [
            line.strip() for line in MANIFEST.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertEqual(lines.count(REGISTRATION), 1)
        self.assertTrue(COMPONENT.is_file())

    def test_finance_imports_registered_component_directory(self):
        finance = FINANCE.read_text(encoding="utf-8")
        self.assertIn('import "../components"', finance)
        self.assertIn("WidgetContentKeyboardNavigator {", finance)


if __name__ == "__main__":
    unittest.main()
