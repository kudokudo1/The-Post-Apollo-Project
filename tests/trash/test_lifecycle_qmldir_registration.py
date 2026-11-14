"""Regression: a local qmldir manifest must export the shared Trash++ type.

GitHub-only read-only contract. This catches the actual Quickshell startup
failure "TrashLifecycleActionDeck is not a type", which Python/Node tests
that only examined QML source previously missed.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS = ROOT / "components"
TYPE = "TrashLifecycleActionDeck"
EXPECTED = f"{TYPE} 1.0 {TYPE}.qml"


class TrashLifecycleQmldirTests(unittest.TestCase):
    def test_manifest_exports_exact_shared_component_once(self):
        module = (COMPONENTS / "qmldir").read_text(encoding="utf-8")
        lines = [line.strip() for line in module.splitlines()
                 if line.strip() and not line.lstrip().startswith("#")]
        self.assertEqual(lines[0], "module qs.components")
        self.assertEqual(lines.count(EXPECTED), 1)
        self.assertTrue((COMPONENTS / (TYPE + ".qml")).is_file())
        # No competing export for the name pointing at a different file.
        exports = [line for line in lines if re.match(r"^" + TYPE + r"\s", line)]
        self.assertEqual(exports, [EXPECTED])

    def test_trash_and_component_are_real_local_qml_types(self):
        trash = (ROOT / "modules/Trash.qml").read_text(encoding="utf-8")
        deck = (COMPONENTS / (TYPE + ".qml")).read_text(encoding="utf-8")
        self.assertIn('import "../components"', trash)
        self.assertIn(TYPE + " {", trash)
        self.assertIn("import QtQuick", deck)
        self.assertIn("Row {", deck)
        self.assertIn("signal restoreReviewRequested(", deck)
        self.assertIn("signal trashReviewRequested(", deck)

    def test_manifest_entry_is_not_only_in_comment(self):
        module = (COMPONENTS / "qmldir").read_text(encoding="utf-8")
        self.assertRegex(module, r"(?m)^TrashLifecycleActionDeck 1\.0 TrashLifecycleActionDeck\.qml$")


if __name__ == "__main__":
    unittest.main()
