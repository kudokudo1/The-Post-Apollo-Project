"""Trash++ U1 contract: source-only deletion inventory and review-only deck."""
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT = Path(__file__).resolve().parents[2]
SCANNER = ROOT / "scripts/trash/universal_delete_inventory_u1.py"
DECK = ROOT / "components/TrashLifecycleActionDeck.qml"
spec = importlib.util.spec_from_file_location("trash_u1_inventory", SCANNER)
inventory_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory_module)


class UniversalLifecycleInventoryU1Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in inventory_module.SCAN_DIRS:
            (self.root / name).mkdir()

    def test_findings_are_review_only_and_no_payload_is_emitted(self):
        marker = "PRIVATE_ACCOUNT_PAYLOAD_DO_NOT_LEAK"
        (self.root / "modules/Example.qml").write_text(
            'ActionButton { label: "DELETE" }\n'
            'function removeRecord() { /* review-only */ }\n'
            'property string payload: "' + marker + '"\n',
            encoding="utf-8")
        result = inventory_module.inventory(self.root)
        self.assertEqual(result["schema"], inventory_module.SCHEMA)
        self.assertEqual(result["state"], "OWNER_REVIEW_REQUIRED")
        self.assertEqual(result["totals"]["candidateLocations"], 2)
        self.assertEqual(result["totals"]["byFamily"]["modules"], 2)
        self.assertTrue(result["readOnly"])
        self.assertFalse(result["actionAuthority"])
        self.assertFalse(result["sourceOwnerApproval"])
        self.assertTrue(all(not x["trashAllowed"] and not x["burnAllowed"]
                            and x["state"] == "OWNER_REVIEW_REQUIRED"
                            for x in result["candidates"]))
        self.assertNotIn(marker, str(result))
        self.assertEqual((self.root / "modules/Example.qml").read_text(),
                         'ActionButton { label: "DELETE" }\n'
                         'function removeRecord() { /* review-only */ }\n'
                         'property string payload: "' + marker + '"\n')

    def test_unsafe_files_and_symlinked_directories_are_not_read(self):
        secret = self.root / "secret.qml"
        secret.write_text('label: "BURN"\n', encoding="utf-8")
        (self.root / "widgets/pointer.qml").symlink_to(secret)
        (self.root / "components/dangling").symlink_to(self.root / "widgets",
                                                        target_is_directory=True)
        (self.root / "services/oversized.qml").write_bytes(
            b'x' * (inventory_module.MAX_SOURCE_BYTES + 1))
        result = inventory_module.inventory(self.root)
        self.assertEqual(result["totals"]["candidateLocations"], 0)
        self.assertIn("widgets/pointer.qml", result["incompletePaths"])
        self.assertIn("services/oversized.qml", result["incompletePaths"])
        self.assertEqual(result["state"], "INCOMPLETE_REVIEW_REQUIRED")

    def test_missing_source_family_is_never_reported_complete(self):
        (self.root / "services").rmdir()
        result = inventory_module.inventory(self.root)
        self.assertIn("services/", result["incompletePaths"])
        self.assertEqual(result["state"], "INCOMPLETE_REVIEW_REQUIRED")

    def test_cli_rejects_user_selected_paths(self):
        with redirect_stdout(io.StringIO()) as stream:
            self.assertEqual(inventory_module.main(["scanner", "/tmp"]), 2)
        self.assertIn("NO_ARGUMENTS_ALLOWED", stream.getvalue())

    def test_action_deck_is_not_a_destructive_backend(self):
        source = DECK.read_text(encoding="utf-8")
        for prop in ("showTrash", "showRestore", "showBurn",
                     "trashCapable", "restoreCapable", "burnCapable",
                     "ownerApproved", "policyReviewed"):
            self.assertIn("property bool " + prop + ": false", source)
        self.assertIn("property bool protectedResource: true", source)
        self.assertIn("property bool retentionHold: true", source)
        self.assertIn("readonly property bool canReviewTrash:", source)
        self.assertIn("readonly property bool canReviewRestore:", source)
        self.assertIn("readonly property bool canReviewBurn:", source)
        self.assertIn("resourceRevision", source)
        self.assertIn("label: \"TRASH\"", source)
        self.assertIn("label: \"BURN\"", source)
        self.assertIn("label: \"RESTORE\"", source)
        self.assertEqual(source.count("onLeftClicked:"), 3)
        for name in ("trashReviewRequested", "restoreReviewRequested",
                     "burnReviewRequested"):
            self.assertIn("signal " + name, source)
        for forbidden in ("Process {", "Quickshell.Io", "subprocess",
                          "os.unlink", "os.remove", "gio trash",
                          "removeFile(", "burnAll(", "capture("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
