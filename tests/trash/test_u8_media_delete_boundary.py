"""Trash++ U8 source-only tests: MPD queue entries are NOT GIO media files.

Only repository source is read; manipulated fixtures live in isolated CI temp
directories. This test never imports Media owners, executes MPD or moves files.
"""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/trash/media_delete_inventory_u8.py"
spec = importlib.util.spec_from_file_location("trash_media_inventory_u8", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MediaQueueBoundaryTests(unittest.TestCase):
    def test_repository_has_read_only_owner_review_contract(self):
        report = module.inventory(ROOT)
        self.assertEqual(report["schema"], "post-apollo.trash-media-boundary.u8")
        self.assertEqual(report["state"], "INVENTORIED_READ_ONLY", report["problems"])
        self.assertEqual(report["problems"], [])
        self.assertEqual(len(report["scannedFiles"]), len(module.PATHS))
        self.assertFalse(report["actionAuthority"])
        self.assertFalse(report["sourceOwnerApproval"])
        self.assertFalse(report["mediaFileDeleteSupported"])
        self.assertFalse(report["genericTrashEligible"])
        self.assertTrue(report["readOnly"])
        self.assertEqual(len(report["boundaries"]), 4)
        self.assertTrue(all(not row["filesystemTrash"] and not row["genericBurn"]
                            and row["sourceOwnerReview"] for row in report["boundaries"]))

    def _fixture(self, root):
        for name in module.PATHS:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / name).read_bytes())

    def test_fake_media_file_deletion_is_not_silently_classified_as_queue_remove(self):
        with tempfile.TemporaryDirectory(prefix="trashpp-u8-") as temp:
            root = Path(temp)
            self._fixture(root)
            path = root / "scripts/media/headless_mpd.py"
            source = path.read_text()
            self.assertIn('self.command("deleteid", song_id)', source)
            path.write_text(source.replace('self.command("deleteid", song_id)',
                                           'self.command("delete", song_id)', 1))
            result = module.inventory(root)
            self.assertEqual(result["state"], "DRIFT_OWNER_REVIEW_REQUIRED")
            self.assertFalse(result["genericTrashEligible"])
            self.assertTrue(result["problems"])

    def test_active_queue_guard_drift_is_detected(self):
        with tempfile.TemporaryDirectory(prefix="trashpp-u8-") as temp:
            root = Path(temp)
            self._fixture(root)
            path = root / "scripts/media/media_controller.py"
            source = path.read_text()
            self.assertIn('"ACTIVE_TRACK"', source)
            path.write_text(source.replace('"ACTIVE_TRACK"', '"OTHER_ERROR"', 1))
            result = module.inventory(root)
            self.assertEqual(result["state"], "DRIFT_OWNER_REVIEW_REQUIRED")
            self.assertFalse(result["actionAuthority"])
            self.assertTrue(any("queue_remove" in problem for problem in result["problems"]))

    def test_unapproved_ui_action_requires_owner_review(self):
        with tempfile.TemporaryDirectory(prefix="trashpp-u8-") as temp:
            root = Path(temp)
            self._fixture(root)
            path = root / "widgets/MediaDeckW.qml"
            path.write_text(path.read_text() + "\nTrashLifecycleActionDeck {}\n")
            result = module.inventory(root)
            self.assertEqual(result["state"], "DRIFT_OWNER_REVIEW_REQUIRED")
            self.assertTrue(any("Media UI" in problem for problem in result["problems"]))
            self.assertFalse(result["sourceOwnerApproval"])

    def test_missing_media_source_fails_closed(self):
        with tempfile.TemporaryDirectory(prefix="trashpp-u8-") as temp:
            root = Path(temp)
            self._fixture(root)
            (root / "scripts/media/media_controller_server.py").unlink()
            result = module.inventory(root)
            self.assertEqual(result["state"], "DRIFT_OWNER_REVIEW_REQUIRED")
            self.assertNotEqual(result["problems"], [])
            self.assertFalse(result["mediaFileDeleteSupported"])


if __name__ == "__main__":
    unittest.main()
