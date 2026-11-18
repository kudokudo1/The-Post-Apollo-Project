"""Trash++ U10b // bounded GIO metadata witness, strictly reviewed Restore only.

Pure synthetic tests. No actual gio invocation or operator file access.
The real late destination race is tested in U9's private GitHub CI sandbox.
"""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "trash" / "trash_cli.py"
spec = importlib.util.spec_from_file_location("u10b_trash", SCRIPT)
trash = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trash)


def result(stdout="", code=0):
    return SimpleNamespace(stdout=stdout, stderr="", returncode=code)


def info(original, *, deletion="2026-11-18T04:15:00", file_id="file-1",
         size="42", typ="1"):
    return (
        "display name: u10b-test.png\n"
        "type: regular\n"
        "attributes:\n"
        "  standard::type: " + typ + "\n"
        "  standard::size: " + size + "\n"
        "  trash::orig-path: " + str(original) + "\n"
        + ("  trash::deletion-date: " + deletion + "\n" if deletion else "")
        + ("  id::file: " + file_id + "\n" if file_id else "")
    )


class U10bMetadataTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="trashpp-u10b-test-")
        self.addCleanup(tmp.cleanup)
        self.original = str(Path(tmp.name) / "u10b-test.png")
        self.uri = "trash:///u10b-test.png"
        self.rows = trash.parse_listing(
            self.uri + "\t" + self.original + "\n")
        self.row = self.rows[0]
        self.revision = trash._revision(self.rows)

    def reviewed(self):
        return trash.restore_reviewed(
            self.uri, self.original, self.revision, self.row["reviewId"])

    def test_queries_selected_gio_uri_only_with_read_only_info(self):
        with patch.object(trash, "_run",
                          return_value=result(info(self.original))) as run:
            stamp = trash._restore_identity("/usr/bin/gio", self.row)
        self.assertEqual(stamp[0], self.original)
        self.assertEqual(stamp[1], "2026-11-18T04:15:00")
        self.assertEqual(stamp[2], "file-1")
        run.assert_called_once_with([
            "/usr/bin/gio", "info",
            "--attributes=" + ",".join(trash.RESTORE_ATTRIBUTES),
            self.uri
        ])

    def test_original_path_mismatch_refuses_even_if_listed_row_unchanged(self):
        with patch.object(trash, "_run",
                          return_value=result(info("/elsewhere/changed"))):
            with self.assertRaisesRegex(
                    trash.TrashError, "RESTORE_SOURCE_ORIGINAL_CHANGED"):
                trash._restore_identity("/usr/bin/gio", self.row)

    def test_secondary_witness_mandatory_but_either_type_works(self):
        with patch.object(trash, "_run",
                          return_value=result(info(
                              self.original, deletion="", file_id=""))):
            with self.assertRaisesRegex(
                    trash.TrashError, "RESTORE_SOURCE_IDENTITY_UNAVAILABLE"):
                trash._restore_identity("/usr/bin/gio", self.row)
        for deletion, file_id in (
            ("2026-11-18T04:15:00", ""),
            ("", "file-1"),
        ):
            with self.subTest(deletion=deletion, file_id=file_id):
                with patch.object(trash, "_run", return_value=result(
                        info(self.original, deletion=deletion, file_id=file_id))):
                    witness = trash._restore_identity("/usr/bin/gio", self.row)
                self.assertEqual(witness[0], self.original)

    def test_duplicate_oversized_invalid_and_failed_info_refuse(self):
        variants = (
            (result("", 1), "RESTORE_SOURCE_INFO_UNAVAILABLE"),
            (result("display name: no attributes\n"), "RESTORE_SOURCE_ORIGINAL_CHANGED"),
            (result(info(self.original) +
                    "  trash::deletion-date: conflicting\n"),
             "RESTORE_SOURCE_INFO_INVALID"),
            (result(info(self.original) + "attributes:\n"),
             "RESTORE_SOURCE_INFO_INVALID"),
            (result("X" * (trash.RESTORE_INFO_LIMIT + 1)),
             "RESTORE_SOURCE_INFO_INVALID"),
            (result("attributes:\n  trash::orig-path: " + self.original
                    + "\n  id::file: broken\x00id\n"),
             "RESTORE_SOURCE_INFO_INVALID"),
        )
        for response, reason in variants:
            with self.subTest(reason=reason, size=len(response.stdout)):
                with patch.object(trash, "_run", return_value=response):
                    with self.assertRaisesRegex(trash.TrashError, reason):
                        trash._restore_identity("/usr/bin/gio", self.row)

    def test_same_uri_and_revision_but_changed_metadata_deny_before_move(self):
        with patch.object(trash, "_gio", return_value="/usr/bin/gio"), \
             patch.object(trash, "_run", return_value=result(
                 self.uri + "\t" + self.original + "\n")) as run, \
             patch.object(trash, "_restore_identity", side_effect=[
                 (self.original, "old", "f1", "1", "42"),
                 (self.original, "new", "f1", "1", "42")
             ]) as identity:
            with self.assertRaisesRegex(
                    trash.TrashError, "RESTORE_SOURCE_IDENTITY_CHANGED"):
                self.reviewed()
        self.assertEqual(identity.call_count, 2)
        self.assertEqual(run.call_count, 2)  # listings, never restore
        self.assertFalse(any("restore" in arg
                             for call in run.call_args_list
                             for arg in call.args[0]))

    def test_changed_type_or_size_is_an_identity_mismatch(self):
        for second in (
            (self.original, "date", "file-1", "2", "42"),
            (self.original, "date", "file-1", "1", "43"),
        ):
            with self.subTest(second=second):
                with patch.object(trash, "_gio", return_value="/usr/bin/gio"), \
                     patch.object(trash, "_run", return_value=result(
                         self.uri + "\t" + self.original + "\n")) as run, \
                     patch.object(trash, "_restore_identity", side_effect=[
                         (self.original, "date", "file-1", "1", "42"),
                         second
                     ]):
                    with self.assertRaisesRegex(
                            trash.TrashError, "RESTORE_SOURCE_IDENTITY_CHANGED"):
                        self.reviewed()
                self.assertEqual(run.call_count, 2)

    def test_missing_metadata_refuses_before_restore_in_reviewed_path(self):
        with patch.object(trash, "_gio", return_value="/usr/bin/gio"), \
             patch.object(trash, "_run", return_value=result(
                 self.uri + "\t" + self.original + "\n")) as run, \
             patch.object(trash, "_restore_identity",
                          side_effect=trash.TrashError(
                              "RESTORE_SOURCE_INFO_UNAVAILABLE")):
            with self.assertRaisesRegex(
                    trash.TrashError, "RESTORE_SOURCE_INFO_UNAVAILABLE"):
                self.reviewed()
        self.assertEqual(run.call_count, 1)

    def test_legacy_restore_and_burn_not_extended_by_metadata(self):
        # Source inspection protects against accidentally changing the less
        # constrained legacy interface or adding destructive command verbs.
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('result = item_action("restore", argv[2], argv[3])', source)
        self.assertIn('result = item_action("burn", argv[2], argv[3], argv[4])',
                      source)
        body = source.split("def item_action(", 1)[1].split(
            "def burn_all(", 1)[0]
        self.assertNotIn("_restore_identity(", body)
        self.assertIn('[gio, "trash", "--restore", current["uri"]]', source)
        self.assertNotIn('--force', body)
        self.assertNotIn('gio remove', source.split("def restore_reviewed(", 1)[1]
                         .split("def item_action(", 1)[0])


if __name__ == "__main__":
    unittest.main()
