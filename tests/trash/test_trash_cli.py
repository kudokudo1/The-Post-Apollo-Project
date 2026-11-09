"""Synthetic GIO Trash adapter tests. No actual user files are touched."""
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "trash" / "trash_cli.py"
spec = importlib.util.spec_from_file_location("postapollo_trash_cli", SCRIPT)
trash = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trash)


def result(output="", status=0, error=""):
    return SimpleNamespace(stdout=output, stderr=error, returncode=status)


class TrashBackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.first = self.root / "Screenshots" / "Camera 1.png"
        self.second = self.root / "Downloads" / "Other item.txt"
        self.rows = (
            f"trash:///Camera%201.png\t{self.first}\n"
            f"trash:///Other%20item.txt\t{self.second}\n"
        )
        self.gio = patch.object(trash.shutil, "which", return_value="/usr/bin/gio")
        self.gio.start()
        self.addCleanup(self.gio.stop)

    def test_paged_index_exposes_real_names_original_paths_and_full_revision(self):
        with patch.object(trash, "_run", return_value=result(self.rows)) as run:
            data = trash.index()
        self.assertTrue(data["ok"])
        self.assertEqual(data["total"], 2)
        self.assertTrue(data["complete"])
        by_uri = {item["uri"]: item for item in data["items"]}
        self.assertEqual(by_uri["trash:///Camera%201.png"]["name"], "Camera 1.png")
        self.assertEqual(by_uri["trash:///Camera%201.png"]["original"],
                         str(self.first))
        self.assertEqual(len(by_uri), 2)
        self.assertEqual(len(data["revision"]), 64)
        self.assertEqual(run.call_args.args[0], ["/usr/bin/gio", "trash", "--list"])
        with patch.object(trash, "_run", return_value=result(self.rows)):
            self.assertEqual(trash.index(1)["items"], [])

    def test_empty_and_malformed_indices_fail_safe(self):
        self.assertEqual(trash.parse_listing(""), [])
        for invalid in (
            "trash:///file.png /home/user/file.png\n",
            "file:///tmp/wrong\t/tmp/wrong\n",
            "trash:///A\t/a\ntrash:///A\t/b\n",
            "trash:///bad\t../relative\n",
            "trash:///bad\t/a\r/b\n",
            "trash:///a\t/a\nnot-a-trash-item\n",
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(trash.TrashError):
                    trash.parse_listing(invalid)
        with self.assertRaises(trash.TrashError):
            trash.parse_listing("trash:///huge\t/a\n" * (trash.MAX_ITEMS + 1))
        with self.assertRaises(trash.TrashError):
            trash.index(-1)

    def test_restore_only_listed_uri_and_never_overwrites_existing_target(self):
        with patch.object(trash, "_run", side_effect=[
                result(self.rows), result("")]) as run:
            data = trash.item_action("restore", "trash:///Camera%201.png",
                                     str(self.first))
        self.assertEqual(data["message"], "RESTORED")
        self.assertEqual(run.call_args_list[-1].args[0],
                         ["/usr/bin/gio", "trash", "--restore",
                          "trash:///Camera%201.png"])

        self.first.parent.mkdir(parents=True)
        self.first.write_text("KEEP")
        with patch.object(trash, "_run", return_value=result(self.rows)) as run:
            with self.assertRaisesRegex(trash.TrashError, "RESTORE_TARGET_EXISTS"):
                trash.item_action("restore", "trash:///Camera%201.png",
                                  str(self.first))
        self.assertEqual(run.call_count, 1)
        self.assertEqual(self.first.read_text(), "KEEP")

    def test_single_burn_requires_confirmed_current_inventory_item(self):
        with patch.object(trash, "_run", return_value=result(self.rows)) as run:
            with self.assertRaisesRegex(trash.TrashError, "BURN_CONFIRMATION_REQUIRED"):
                trash.item_action("burn", "trash:///Camera%201.png", str(self.first))
            self.assertEqual(run.call_count, 0)
            with self.assertRaisesRegex(trash.TrashError, "STALE_OR_UNKNOWN"):
                trash.item_action("burn", "trash:///Camera%201.png",
                                  "/home/someone/other.png", "BURN_CONFIRMED")
            self.assertEqual(run.call_count, 1)

        with patch.object(trash, "_run", side_effect=[
                result(self.rows), result("")]) as run:
            data = trash.item_action("burn", "trash:///Camera%201.png",
                                     str(self.first), "BURN_CONFIRMED")
        self.assertEqual(data["message"], "BURNED")
        self.assertEqual(run.call_args_list[-1].args[0],
                         ["/usr/bin/gio", "remove", "trash:///Camera%201.png"])

    def test_no_permanent_delete_if_index_failed_or_item_missing(self):
        with patch.object(trash, "_run",
                          return_value=result("", 1, "service unavailable")) as run:
            with self.assertRaisesRegex(trash.TrashError, "GIO_LIST_FAILED"):
                trash.item_action("burn", "trash:///a", "/a", "BURN_CONFIRMED")
        self.assertEqual(run.call_count, 1)
        with patch.object(trash, "_run",
                          return_value=result("trash:///a\t/a\n")) as run:
            with self.assertRaisesRegex(trash.TrashError, "STALE_OR_UNKNOWN"):
                trash.item_action("restore", "trash:///other", "/other")
        self.assertEqual(run.call_count, 1)

    def test_burn_all_explicit_confirmation_exact_count_and_revision(self):
        rows = trash.parse_listing(self.rows)
        stamp = trash._revision(rows)
        with patch.object(trash, "_run", return_value=result(self.rows)) as run:
            for value in ("", "CANCEL", "BURN_CONFIRMED"):
                with self.assertRaisesRegex(trash.TrashError, "CONFIRMATION_REQUIRED"):
                    trash.burn_all(stamp, "2", value)
            self.assertEqual(run.call_count, 0)
            for bad_stamp, bad_count in ((stamp, "1"), ("0" * 64, "2")):
                with self.assertRaisesRegex(trash.TrashError, "TRASH_CHANGED"):
                    trash.burn_all(bad_stamp, bad_count, "BURN_ALL_CONFIRMED")
            self.assertEqual(run.call_count, 2)

        with patch.object(trash, "_run", side_effect=[
                result(self.rows), result("")]) as run:
            data = trash.burn_all(stamp, "2", "BURN_ALL_CONFIRMED")
        self.assertEqual(data["count"], 2)
        self.assertEqual(run.call_args_list[-1].args[0],
                         ["/usr/bin/gio", "trash", "--empty"])

    def test_burn_all_refuses_empty_trash_or_invalid_index(self):
        with patch.object(trash, "_run", return_value=result("")) as run:
            with self.assertRaisesRegex(trash.TrashError, "TRASH_CHANGED"):
                trash.burn_all(trash._revision([]), "0", "BURN_ALL_CONFIRMED")
        self.assertEqual(run.call_count, 1)
        with patch.object(trash, "_run", return_value=result("INVALID")) as run:
            with self.assertRaisesRegex(trash.TrashError, "FORMAT_UNSUPPORTED"):
                trash.burn_all("0" * 64, "1", "BURN_ALL_CONFIRMED")
        self.assertEqual(run.call_count, 1)

    def test_gio_failures_are_reported_without_success_claims(self):
        with patch.object(trash, "_run", side_effect=[
                result(self.rows), result("", 1, "cannot restore")]):
            with self.assertRaisesRegex(trash.TrashError, "GIO_RESTORE_FAILED"):
                trash.item_action("restore", "trash:///Camera%201.png",
                                  str(self.first))
        with patch.object(trash, "_run", side_effect=[
                result(self.rows), result("", 1, "cannot burn")]):
            with self.assertRaisesRegex(trash.TrashError, "GIO_BURN_FAILED"):
                trash.item_action("burn", "trash:///Camera%201.png",
                                  str(self.first), "BURN_CONFIRMED")
        with patch.object(trash, "_run", side_effect=[
                result(self.rows), result("", 1, "cannot empty")]):
            with self.assertRaisesRegex(trash.TrashError, "GIO_EMPTY_FAILED"):
                trash.burn_all(trash._revision(trash.parse_listing(self.rows)),
                               "2", "BURN_ALL_CONFIRMED")

    def test_cli_serializes_only_json_and_rejects_unrequested_actions(self):
        from io import StringIO
        from contextlib import redirect_stdout
        stream = StringIO()
        with redirect_stdout(stream):
            code = trash.main(["trash_cli.py", "burn", "trash:///foo", "/foo"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(stream.getvalue())["error"], "INVALID_ACTION")


if __name__ == "__main__":
    unittest.main()
