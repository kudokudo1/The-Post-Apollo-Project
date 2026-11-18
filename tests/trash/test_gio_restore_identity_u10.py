"""U10: refuse changed GIO metadata and last-moment occupied Restore targets.

Pure synthetic tests: never call GIO, trash an actual file, or touch user data.
"""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts" / "trash" / "trash_cli.py"
spec = importlib.util.spec_from_file_location("postapollo_trash_u10", SOURCE)
trash = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trash)


def response(stdout="", returncode=0):
    return SimpleNamespace(stdout=stdout, stderr="", returncode=returncode)


def metadata(original, deletion="2026-11-17T19:01:02", file_id="f-abc"):
    return (
        "display name: U10-disposable.txt\n"
        "type: regular\n"
        "attributes:\n"
        "  standard::type: 1\n"
        "  standard::size: 48\n"
        "  trash::orig-path: " + str(original) + "\n"
        "  trash::deletion-date: " + deletion + "\n"
        "  id::file: " + file_id + "\n"
    )


class RestoreIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="trashpp-u10-")
        self.addCleanup(self.temp.cleanup)
        self.original = str(Path(self.temp.name) / "U10-disposable.txt")
        self.uri = "trash:///U10-disposable.txt"
        self.row = {"uri": self.uri, "original": self.original,
                    "name": "U10-disposable.txt", "reviewId": "a" * 64}

    def test_metadata_reads_one_exact_gio_uri_with_no_write_verb(self):
        with patch.object(trash, "_run", return_value=response(metadata(self.original))) as proc:
            found = trash._restore_identity("/usr/bin/gio", self.row)
        self.assertEqual(found[0], self.original)
        self.assertEqual(found[1], "2026-11-17T19:01:02")
        self.assertEqual(found[2], "f-abc")
        self.assertEqual(proc.call_args.args[0], [
            "/usr/bin/gio", "info",
            "--attributes=" + ",".join(trash.RESTORE_ATTRIBUTES), self.uri,
        ])

    def test_metadata_path_swap_is_denied_even_when_listing_tuple_is_unchanged(self):
        with patch.object(trash, "_run",
                          return_value=response(metadata("/elsewhere/new-origin"))):
            with self.assertRaisesRegex(trash.TrashError, "RESTORE_SOURCE_ORIGINAL_CHANGED"):
                trash._restore_identity("/usr/bin/gio", self.row)

    def test_unavailable_incomplete_duplicate_and_oversized_metadata_refused(self):
        scenarios = [
            (response("", 1), "RESTORE_SOURCE_INFO_UNAVAILABLE"),
            (response("display name: blah\n"), "RESTORE_SOURCE_ORIGINAL_CHANGED"),
            (response("attributes:\n  trash::orig-path: " + self.original + "\n"),
             "RESTORE_SOURCE_IDENTITY_UNAVAILABLE"),
            (response(metadata(self.original) + "  trash::deletion-date: REPLACED\n"),
             "RESTORE_SOURCE_INFO_INVALID"),
            (response("a" * (trash.RESTORE_INFO_LIMIT + 1)),
             "RESTORE_SOURCE_INFO_INVALID"),
            (response("attributes:\n  trash::orig-path: " + self.original
                      + "\n  trash::deletion-date: 2026-11-17T19:00:00\n"
                      + "attributes:\n"), "RESTORE_SOURCE_INFO_INVALID"),
        ]
        for result, reason in scenarios:
            with self.subTest(reason=reason):
                with patch.object(trash, "_run", return_value=result):
                    with self.assertRaisesRegex(trash.TrashError, reason):
                        trash._restore_identity("/usr/bin/gio", self.row)

    def test_metadata_change_between_preflights_denies_restore(self):
        current = trash.parse_listing(self.uri + "\t" + self.original + "\n")
        with patch.object(trash, "inventory", return_value=("/usr/bin/gio", current)), \
             patch.object(trash, "_restore_identity",
                          side_effect=[("same", "first"), ("same", "changed")]) as ident:
            with self.assertRaisesRegex(trash.TrashError, "RESTORE_SOURCE_IDENTITY_CHANGED"):
                trash._restore_preflight("/usr/bin/gio", self.row)
        self.assertEqual(ident.call_count, 2)

    def test_missing_entry_at_second_inventory_denies_restore(self):
        with patch.object(trash, "inventory", return_value=("/usr/bin/gio", [])), \
             patch.object(trash, "_restore_identity",
                          return_value=("stable",)) as ident:
            with self.assertRaisesRegex(trash.TrashError, "STALE_OR_UNKNOWN_TRASH_ITEM"):
                trash._restore_preflight("/usr/bin/gio", self.row)
        self.assertEqual(ident.call_count, 1)

    def test_destination_appearing_after_identity_check_denies_restore(self):
        # Another actor creates the destination after the first lexists test.
        current = trash.parse_listing(self.uri + "\t" + self.original + "\n")
        def witness(_gio, _row):
            if not Path(self.original).exists():
                Path(self.original).write_bytes(b"OPERATOR_FILE_MUST_REMAIN")
            return ("stable",)
        with patch.object(trash, "inventory", return_value=("/usr/bin/gio", current)), \
             patch.object(trash, "_restore_identity", side_effect=witness):
            with self.assertRaisesRegex(trash.TrashError, "RESTORE_TARGET_EXISTS"):
                trash._restore_preflight("/usr/bin/gio", self.row)
        self.assertEqual(Path(self.original).read_bytes(), b"OPERATOR_FILE_MUST_REMAIN")

    def test_restore_does_not_add_force_or_permanent_delete_even_with_preflight(self):
        seen = []
        listing = self.uri + "\t" + self.original + "\n"
        def fake_run(argv, timeout=20):
            seen.append(list(argv))
            if argv[-2:] == ["trash", "--list"]:
                return response(listing)
            if argv[1:3] == ["trash", "--restore"]:
                return response()
            raise AssertionError("Unexpected GIO operation")
        with patch.object(trash, "_gio", return_value="/usr/bin/gio"), \
             patch.object(trash, "_run", side_effect=fake_run), \
             patch.object(trash, "_restore_identity", return_value=("stable",)):
            result = trash.item_action("restore", self.uri, self.original)
        self.assertEqual(result["message"], "RESTORED")
        self.assertEqual(seen[-1], ["/usr/bin/gio", "trash", "--restore", self.uri])
        self.assertFalse(any("--force" in row or "remove" in row or "--empty" in row
                             for row in seen))


if __name__ == "__main__":
    unittest.main()
