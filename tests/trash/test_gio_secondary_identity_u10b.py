"""U10b supplemental GIO metadata guard tests.

Synthetic source and tempfile fixtures only: no actual GIO, user files or
operator Trash are accessed. Existing U10 reviewed-index authority is retained.
"""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts" / "trash" / "trash_cli.py"
spec = importlib.util.spec_from_file_location("u10b_trash_cli", SOURCE)
trash = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trash)


def result(output="", status=0):
    return SimpleNamespace(stdout=output, stderr="", returncode=status)


def metadata(original, date="2026-11-18T01:05:00Z", fileid="inode-test",
             more=""):
    return ("display name: test.txt\n"
            "attributes:\n"
            "  trash::orig-path: " + str(original) + "\n"
            "  trash::deletion-date: " + date + "\n"
            "  id::file: " + fileid + "\n"
            "  standard::type: 1\n"
            "  standard::size: 57\n" + more)


class GIOSecondaryIdentityU10bTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(prefix="trashpp-u10b-")
        self.addCleanup(t.cleanup)
        self.original = Path(t.name) / "screenshot.txt"
        self.uri = "trash:///screenshot.txt"
        self.rows = trash.parse_listing(self.uri + "\t" + str(self.original) + "\n")
        self.row = self.rows[0]
        self.revision = trash._revision(self.rows)
        self.review_id = self.row["reviewId"]

    def _call_reviewed(self):
        return trash.restore_reviewed(self.uri, str(self.original),
                                      self.revision, self.review_id)

    def test_one_exact_gio_info_query_has_no_write_arguments(self):
        with patch.object(trash, "_run",
                          return_value=result(metadata(self.original))) as proc:
            witness = trash._restore_metadata("/usr/bin/gio", self.row)
        self.assertEqual(witness[0], ("trash::orig-path", str(self.original)))
        self.assertEqual(witness[1], ("trash::deletion-date", "2026-11-18T01:05:00Z"))
        self.assertEqual(proc.call_args.args[0], [
            "/usr/bin/gio", "info",
            "--attributes=" + ",".join(trash.RESTORE_METADATA_ATTRS), self.uri
        ])

    def test_attributes_reordered_are_equivalent(self):
        first = metadata(self.original)
        different = ("attributes:\n"
                     "  standard::size: 57\n"
                     "  id::file: inode-test\n"
                     "  standard::type: 1\n"
                     "  trash::deletion-date: 2026-11-18T01:05:00Z\n"
                     "  trash::orig-path: " + str(self.original) + "\n")
        with patch.object(trash, "_run", side_effect=[result(first), result(different)]):
            a = trash._restore_metadata("gio", self.row)
            b = trash._restore_metadata("gio", self.row)
        self.assertEqual(a, b)

    def test_provider_missing_metadata_does_not_block_existing_u10_route(self):
        for raw in (result("", 1), result("display name: missing\n"),
                    result("attributes:\n")):
            with self.subTest(raw=raw.stdout):
                with patch.object(trash, "_run", return_value=raw):
                    self.assertIsNone(trash._restore_metadata("gio", self.row))

    def test_mismatched_original_is_denied(self):
        with patch.object(trash, "_run",
                          return_value=result(metadata("/other/destination.txt"))):
            with self.assertRaisesRegex(trash.TrashError,
                                        "RESTORE_SOURCE_ORIGINAL_CHANGED"):
                trash._restore_metadata("gio", self.row)

    def test_missing_secondary_is_not_misreported_as_identity_proof(self):
        limited = ("attributes:\n"
                   "  standard::size: 57\n"
                   "  standard::type: 1\n")
        with patch.object(trash, "_run", return_value=result(limited)):
            witness = trash._restore_metadata("gio", self.row)
        self.assertIsNotNone(witness)
        self.assertFalse(any(k in ("trash::deletion-date", "id::file")
                             for k, v in witness))

    def test_malformed_or_oversized_metadata_denied(self):
        cases = [
            metadata(self.original, more="  id::file: collision\n"),
            metadata(self.original, more="attributes:\n"),
            "a" * (trash.RESTORE_METADATA_LIMIT + 1),
            metadata(self.original, more="  trash::orig-path: \n"),
        ]
        for raw in cases:
            with self.subTest(size=len(raw)):
                with patch.object(trash, "_run", return_value=result(raw)):
                    with self.assertRaisesRegex(trash.TrashError, "RESTORE_METADATA_MALFORMED"):
                        trash._restore_metadata("gio", self.row)

    def test_second_metadata_swap_refuses_without_running_restore(self):
        first = (("trash::orig-path", str(self.original)),
                 ("trash::deletion-date", "old"),
                 ("id::file", "x"))
        swapped = (("trash::orig-path", str(self.original)),
                   ("trash::deletion-date", "new"),
                   ("id::file", "x"))
        with patch.object(trash, "inventory",
                          side_effect=[("/usr/bin/gio", self.rows)] * 2), \
             patch.object(trash, "_restore_metadata",
                          side_effect=[first, swapped]) as meta, \
             patch.object(trash, "_run") as run:
            with self.assertRaisesRegex(trash.TrashError,
                                        "RESTORE_SOURCE_METADATA_CHANGED"):
                self._call_reviewed()
        self.assertEqual(meta.call_count, 2)
        run.assert_not_called()

    def test_metadata_becoming_unavailable_mid_review_refuses(self):
        with patch.object(trash, "inventory",
                          side_effect=[("/usr/bin/gio", self.rows)] * 2), \
             patch.object(trash, "_restore_metadata",
                          side_effect=[(("id::file", "known"),), None]), \
             patch.object(trash, "_run") as run:
            with self.assertRaisesRegex(trash.TrashError,
                                        "RESTORE_SOURCE_METADATA_CHANGED"):
                self._call_reviewed()
        run.assert_not_called()

    def test_missing_metadata_keeps_prior_review_and_post_state_verification(self):
        def run(argv, timeout=20):
            self.assertEqual(argv, ["/usr/bin/gio", "trash", "--restore", self.uri])
            self.original.write_bytes(b"fixture")
            return result()
        with patch.object(trash, "inventory",
                          side_effect=[("/usr/bin/gio", self.rows),
                                       ("/usr/bin/gio", self.rows),
                                       ("/usr/bin/gio", [])]) as index, \
             patch.object(trash, "_restore_metadata", return_value=None) as meta, \
             patch.object(trash, "_run", side_effect=run) as gio:
            receipt = self._call_reviewed()
        self.assertEqual(index.call_count, 3)
        self.assertEqual(meta.call_count, 2)
        self.assertEqual(gio.call_count, 1)
        self.assertTrue(receipt["verified"])
        self.assertEqual(receipt["metadataWitness"], "unavailable")
        self.assertFalse(receipt["secondaryIdentityObserved"])

    def test_secondary_identity_receipt_only_when_supported(self):
        def run(argv, timeout=20):
            self.original.write_bytes(b"fixture")
            return result()
        witness = (("trash::orig-path", str(self.original)),
                   ("id::file", "stable-id"))
        with patch.object(trash, "inventory",
                          side_effect=[("/usr/bin/gio", self.rows),
                                       ("/usr/bin/gio", self.rows),
                                       ("/usr/bin/gio", [])]), \
             patch.object(trash, "_restore_metadata", return_value=witness), \
             patch.object(trash, "_run", side_effect=run):
            receipt = self._call_reviewed()
        self.assertEqual(receipt["metadataWitness"], "observed")
        self.assertTrue(receipt["secondaryIdentityObserved"])

    def test_invalid_review_token_denies_before_metadata_or_gio(self):
        with patch.object(trash, "_restore_metadata") as metadata_query, \
             patch.object(trash, "inventory") as index, \
             patch.object(trash, "_run") as gio:
            with self.assertRaisesRegex(trash.TrashError,
                                        "RESTORE_REVIEW_TOKEN_INVALID"):
                trash.restore_reviewed(self.uri, str(self.original),
                                       "bad-token", self.review_id)
        metadata_query.assert_not_called()
        index.assert_not_called()
        gio.assert_not_called()


if __name__ == "__main__":
    unittest.main()
