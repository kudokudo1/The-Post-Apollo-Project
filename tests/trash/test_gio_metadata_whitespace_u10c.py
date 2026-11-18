"""U10c // preserve legitimate original-path whitespace in GIO info.

Synthetic only; never runs gio, changes live Trash, or touches operator data.
"""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts" / "trash" / "trash_cli.py"
spec = importlib.util.spec_from_file_location("u10c_trash", SOURCE)
trash = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trash)


def info(original, date="2026-11-18T10:00:00"):
    return SimpleNamespace(
        stdout=("display name: GIO whitespace fixture\n"
                "attributes:\n"
                "  trash::orig-path: " + original + "\n"
                "  trash::deletion-date: " + date + "\n"
                "  standard::type: 1\n"),
        stderr="", returncode=0
    )


class MetadataWhitespaceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="trashpp-u10c-")
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name)

    def test_trailing_whitespace_preserved_in_metadata_path(self):
        for suffix in (" ", "  ", "\t", " \t"):
            with self.subTest(suffix=repr(suffix)):
                original = str(self.path / "capture") + suffix
                uri = "trash:///capture"
                row = trash.parse_listing(uri + "\t" + original + "\n")[0]
                with patch.object(trash, "_run", return_value=info(original)):
                    witness = trash._restore_identity("/usr/bin/gio", row)
                self.assertEqual(witness[0], original)
                self.assertEqual(witness[1], "2026-11-18T10:00:00")

    def test_filename_with_leading_space_after_directory_is_preserved(self):
        original = str(self.path / " screenshot.png")
        row = trash.parse_listing("trash:///screenshot.png\t" + original + "\n")[0]
        with patch.object(trash, "_run", return_value=info(original)):
            witness = trash._restore_identity("/usr/bin/gio", row)
        self.assertEqual(witness[0], original)

    def test_original_mismatch_remains_a_hard_refusal(self):
        original = str(self.path / "camera.png")
        row = trash.parse_listing("trash:///camera.png\t" + original + "\n")[0]
        with patch.object(trash, "_run", return_value=info(original + " ")):
            with self.assertRaisesRegex(trash.TrashError,
                                        "RESTORE_SOURCE_ORIGINAL_CHANGED"):
                trash._restore_identity("/usr/bin/gio", row)

    def test_duplicate_attributes_still_refused(self):
        original = str(self.path / "camera.png ")
        row = trash.parse_listing("trash:///camera.png\t" + original + "\n")[0]
        payload = info(original)
        payload.stdout += "  trash::orig-path: " + original + "\n"
        with patch.object(trash, "_run", return_value=payload):
            with self.assertRaisesRegex(trash.TrashError,
                                        "RESTORE_SOURCE_INFO_INVALID"):
                trash._restore_identity("/usr/bin/gio", row)


if __name__ == "__main__":
    unittest.main()
