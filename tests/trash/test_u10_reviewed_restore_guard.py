"""U10 // synthetic reviewed GIO Restore revalidation and race regressions.

No actual GIO command or personal file is modified. Test-created collision
sentinels live only under tempfile. This does not prove atomic no-overwrite.
"""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/trash/trash_cli.py"
spec = importlib.util.spec_from_file_location("u10_trash_cli", SCRIPT)
trash = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trash)


def result(output="", code=0, error=""):
    return SimpleNamespace(stdout=output, stderr=error, returncode=code)


class ReviewedRestoreTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="trashpp-u10-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.target = self.root / "photos" / "test.png"
        self.target.parent.mkdir()
        self.uri = "trash:///test.png"
        self.rows = f"{self.uri}\t{self.target}\n"
        self.other = f"trash:///unrelated\t{self.root / 'other.png'}\n"
        self.revision = trash._revision(trash.parse_listing(self.rows))
        self.token = trash._review_id(self.uri, str(self.target))
        self.gio = patch.object(trash, "_gio", return_value="/usr/bin/gio")
        self.gio.start()
        self.addCleanup(self.gio.stop)

    def run_guard(self, **kwargs):
        return trash.restore_reviewed(
            kwargs.get("uri", self.uri),
            kwargs.get("original", str(self.target)),
            kwargs.get("revision", self.revision),
            kwargs.get("token", self.token),
        )

    def test_valid_double_index_then_gio_and_postcheck_receipt(self):
        def fake_run(argv, timeout=20):
            if argv[1:3] == ["trash", "--list"]:
                fake_run.scans += 1
                return result(self.rows if fake_run.scans <= 2 else "")
            self.assertEqual(argv, ["/usr/bin/gio", "trash", "--restore", self.uri])
            self.target.write_bytes(b"fixture-restored")
            return result()
        fake_run.scans = 0
        with patch.object(trash, "_run", side_effect=fake_run) as run:
            receipt = self.run_guard()
        self.assertEqual(fake_run.scans, 3)
        self.assertEqual(run.call_count, 4)
        self.assertEqual(receipt["message"], "RESTORED")
        self.assertTrue(receipt["verified"])
        self.assertEqual(self.target.read_bytes(), b"fixture-restored")

    def test_invalid_token_and_revision_denied_without_gio(self):
        with patch.object(trash, "_run") as run:
            for revision, token in (
                ("wrong", self.token), (self.revision, "wrong"),
                (self.revision.upper(), self.token),
                (self.revision, self.token.upper()),
            ):
                with self.subTest(revision=revision, token=token):
                    with self.assertRaisesRegex(
                            trash.TrashError, "RESTORE_REVIEW_TOKEN_INVALID"):
                        self.run_guard(revision=revision, token=token)
        run.assert_not_called()

    def test_changed_revision_and_row_refused_without_restore(self):
        with patch.object(trash, "_run", return_value=result(self.rows)) as run:
            with self.assertRaisesRegex(
                    trash.TrashError, "TRASH_CHANGED_REFRESH_REQUIRED"):
                self.run_guard(revision="a" * 64)
            with self.assertRaisesRegex(
                    trash.TrashError, "TRASH_CHANGED_REFRESH_REQUIRED"):
                self.run_guard(token="b" * 64)
        self.assertEqual(run.call_count, 2)

    def test_stale_or_missing_first_index_fails_closed(self):
        with patch.object(trash, "_run", return_value=result("")) as run:
            with self.assertRaisesRegex(
                    trash.TrashError, "STALE_OR_UNKNOWN_TRASH_ITEM"):
                self.run_guard()
        self.assertEqual(run.call_count, 1)

    def test_initial_destination_collision_refuses_before_second_scan(self):
        self.target.write_bytes(b"do not overwrite")
        with patch.object(trash, "_run", return_value=result(self.rows)) as run:
            with self.assertRaisesRegex(
                    trash.TrashError, "RESTORE_TARGET_EXISTS"):
                self.run_guard()
        self.assertEqual(run.call_count, 1)
        self.assertEqual(self.target.read_bytes(), b"do not overwrite")

    def test_index_changes_between_first_and_second_snapshot(self):
        with patch.object(trash, "_run", side_effect=[
                result(self.rows), result(self.rows + self.other)]) as run:
            with self.assertRaisesRegex(
                    trash.TrashError, "TRASH_CHANGED_REFRESH_REQUIRED"):
                self.run_guard()
        self.assertEqual(run.call_count, 2)

    def test_selected_item_disappears_before_second_scan(self):
        with patch.object(trash, "_run", side_effect=[
                result(self.rows), result(self.other)]) as run:
            with self.assertRaisesRegex(
                    trash.TrashError, "STALE_OR_UNKNOWN_TRASH_ITEM"):
                self.run_guard()
        self.assertEqual(run.call_count, 2)

    def test_destination_created_during_second_scan_cannot_be_overwritten(self):
        def fake_run(argv, timeout=20):
            fake_run.scans += 1
            if fake_run.scans == 2:
                self.target.write_bytes(b"another-writer")
            self.assertEqual(argv[1:3], ["trash", "--list"])
            return result(self.rows)
        fake_run.scans = 0
        with patch.object(trash, "_run", side_effect=fake_run) as run:
            with self.assertRaisesRegex(
                    trash.TrashError, "RESTORE_TARGET_EXISTS"):
                self.run_guard()
        self.assertEqual(run.call_count, 2)
        self.assertEqual(self.target.read_bytes(), b"another-writer")

    def test_gio_failure_does_not_claim_restore(self):
        with patch.object(trash, "_run", side_effect=[
                result(self.rows), result(self.rows),
                result("", 1, "gio failed")]) as run:
            with self.assertRaisesRegex(trash.TrashError, "GIO_RESTORE_FAILED"):
                self.run_guard()
        self.assertEqual(run.call_count, 3)

    def test_completed_gio_with_missing_destination_is_uncertain(self):
        with patch.object(trash, "_run", side_effect=[
                result(self.rows), result(self.rows), result(""), result("")]):
            with self.assertRaisesRegex(
                    trash.TrashError, "RESTORE_RESULT_UNVERIFIED"):
                self.run_guard()

    def test_successful_gio_with_unavailable_postindex_is_uncertain(self):
        self.target.write_bytes(b"restored-from-other-worker")
        def fake_run(argv, timeout=20):
            if fake_run.calls == 0:
                self.target.unlink()
            fake_run.calls += 1
            return [result(self.rows), result(self.rows), result(""),
                    result("", 1, "gvfs unavailable")][fake_run.calls - 1]
        fake_run.calls = 0
        with patch.object(trash, "_run", side_effect=fake_run):
            with self.assertRaisesRegex(
                    trash.TrashError, "RESTORE_RESULT_UNVERIFIED"):
                self.run_guard()

    def test_successful_gio_with_still_listed_item_is_uncertain(self):
        def fake_run(argv, timeout=20):
            fake_run.calls += 1
            if fake_run.calls == 3:
                self.target.write_bytes(b"unverified")
            return result(self.rows)
        fake_run.calls = 0
        with patch.object(trash, "_run", side_effect=fake_run):
            with self.assertRaisesRegex(
                    trash.TrashError, "RESTORE_RESULT_UNVERIFIED"):
                self.run_guard()

    def test_legacy_burn_and_restore_command_shapes_unchanged(self):
        # New UI path is opt-in. Existing CI and external direct CLI can still
        # call legacy restore; that path does NOT get the reviewed guarantees.
        from io import StringIO
        from contextlib import redirect_stdout
        with patch.object(trash, "restore_reviewed", return_value={
                "ok": True, "kind": "restore", "message": "RESTORED"}):
            stream = StringIO()
            with redirect_stdout(stream):
                code = trash.main(["trash_cli.py", "restore-reviewed",
                                   self.uri, str(self.target),
                                   self.revision, self.token])
        self.assertEqual(code, 0)
        self.assertIn('"ok":true', stream.getvalue())
        with patch.object(trash, "_run") as run:
            code = trash.main(["trash_cli.py", "burn", self.uri, str(self.target)])
        self.assertEqual(code, 1)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
