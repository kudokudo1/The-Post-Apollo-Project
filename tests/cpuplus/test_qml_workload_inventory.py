import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import cpuplus_qml_workload_inventory as scanner


class InventoryTests(unittest.TestCase):
    def test_markers_and_line_numbers(self):
        source = """Item {
    // Timer {
    /* Process {
       FileView {
    */
    Timer {
        interval: 500
        running: root.menuOpen
        repeat: true
    }
    Io.Process {
        running: false
    }
    Component.onCompleted: refresh()
    property string fake: "Timer {"
    FileView {
        watchChanges: true
    }
}"""
        self.assertEqual(scanner.scan_source(source), [
            {"line": 6, "kind": "Timer"},
            {"line": 7, "kind": "interval.literal", "milliseconds": 500},
            {"line": 8, "kind": "running.expression"},
            {"line": 9, "kind": "repeat.true"},
            {"line": 11, "kind": "Process"},
            {"line": 12, "kind": "running.false"},
            {"line": 14, "kind": "Component.onCompleted"},
            {"line": 16, "kind": "FileView"},
            {"line": 17, "kind": "watchChanges.true"},
        ])

    def test_multiline_strings_masked_and_no_payload(self):
        source = 'property string data: `\nTimer {\nrunning: true\n`\n' + (
            'running: privateValue("secret-token")\ninterval: 15 * 60\n')
        found = scanner.scan_source(source)
        self.assertEqual(found, [{"line": 5, "kind": "running.expression"},
                                 {"line": 6, "kind": "interval.expression"}])
        self.assertNotIn("secret-token", json.dumps(found))

    def test_grouped_inventory_and_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "services" / "weather").mkdir(parents=True)
            (root / "services" / "weather" / "A.qml").write_text("Timer {\n")
            (root / "shell.qml").write_text("Connections {\n")
            paths = ["services/weather/A.qml", "shell.qml", "missing.qml", "../escape.qml"]
            result = scanner.inventory(root, paths)
            self.assertEqual(result["trackedQml"], 4)
            self.assertEqual(result["scannedQml"], 2)
            self.assertEqual(result["totals"], {"Timer": 1, "Connections": 1})
            self.assertEqual(result["groups"]["services/weather"]["files"], 1)
            self.assertEqual(result["skipped"], ["missing.qml", "../escape.qml"])

    def test_symlink_not_scanned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "target.qml").write_text("Process {\n")
            (root / "link.qml").symlink_to(root / "target.qml")
            result = scanner.inventory(root, ["link.qml"])
            self.assertEqual(result["skipped"], ["link.qml"])
            self.assertEqual(result["scannedQml"], 0)


if __name__ == "__main__":
    unittest.main()
