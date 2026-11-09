"""Synthetic Trash++ research-copy lifecycle. No actual account or desktop data."""
import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/trash/research_records.py"
spec = importlib.util.spec_from_file_location("postapollo_research_records", SOURCE)
records = importlib.util.module_from_spec(spec)
spec.loader.exec_module(records)


def page():
    return {
        "schemaVersion": 1,
        "source": "finance-demo-scrapy",
        "readOnly": True,
        "url": "https://quotes.toscrape.com/page/1/",
        "title": "Demo quote crawl",
        "observedAt": "2026-10-12T10:30:00Z",
        "links": ["https://quotes.toscrape.com/author/Someone"],
        "snippets": ["One sample quote"],
    }


class ManagedResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.data = self.root / "quickshell"
        self.data.mkdir()
        self.source = self.home / records.CRAWL_PATH
        self.source.parent.mkdir(parents=True)
        self.source.write_text(json.dumps([page()]), encoding="utf-8")

    def run_action(self, name, ident="", rev=0, confirmation="", when=""):
        return records.operate(name, str(self.data), ident, rev, confirmation, when,
                               home_dir=self.home)

    def save_store(self, text):
        (self.data / records.STORE_NAME).write_text(text, encoding="utf-8")

    def test_archive_trash_restore_then_burn_only_copy(self):
        original = self.source.read_bytes()
        blank = self.run_action("list")
        self.assertEqual(blank["revision"], 0)
        self.assertEqual(blank["total"], 0)
        self.assertFalse((self.data / records.STORE_NAME).exists())
        copy = self.run_action("archive", page()["url"], 0,
                               when=page()["observedAt"])
        self.assertEqual(copy["result"], "ARCHIVE")
        self.assertEqual(copy["revision"], 1)
        self.assertEqual(copy["total"], 1)
        record = copy["items"][0]
        rid = record["id"]
        self.assertEqual(len(rid), 32)
        self.assertEqual(record["state"], "archived")
        self.assertTrue(record["capabilities"]["trash"])
        self.assertFalse(record["capabilities"]["burn"])
        self.assertEqual(self.source.read_bytes(), original)

        trashed = self.run_action("trash", rid, 1)
        self.assertEqual(trashed["revision"], 2)
        self.assertEqual(trashed["items"][0]["state"], "trashed")
        self.assertTrue(trashed["items"][0]["capabilities"]["restore"])
        self.assertTrue(trashed["items"][0]["capabilities"]["burn"])
        self.assertEqual(self.source.read_bytes(), original)

        restored = self.run_action("restore", rid, 2)
        self.assertEqual(restored["revision"], 3)
        self.assertEqual(restored["items"][0]["state"], "archived")
        second = self.run_action("trash", rid, 3)
        self.assertEqual(second["revision"], 4)
        burnt = self.run_action("burn", rid, 4, "BURN_SAVED_COPY_CONFIRMED")
        self.assertEqual(burnt["total"], 0)
        self.assertEqual(burnt["revision"], 5)
        self.assertEqual(self.run_action("list")["total"], 0)
        self.assertEqual(self.source.read_bytes(), original)

    def test_refuse_direct_burn_without_trash_and_explicit_token(self):
        first = self.run_action("archive", page()["url"], 0,
                                when=page()["observedAt"])
        rid = first["items"][0]["id"]
        with self.assertRaisesRegex(records.LifecycleError,
                                    "BURN_CONFIRMATION_REQUIRED"):
            self.run_action("burn", rid, 1)
        with self.assertRaisesRegex(records.LifecycleError,
                                    "BURN_REQUIRES_TRASH_FIRST"):
            self.run_action("burn", rid, 1, "BURN_SAVED_COPY_CONFIRMED")
        self.assertEqual(self.run_action("list")["revision"], 1)

    def test_stale_revision_unknown_id_and_duplicate_copy_fail_closed(self):
        first = self.run_action("archive", page()["url"], 0,
                                when=page()["observedAt"])
        rid = first["items"][0]["id"]
        with self.assertRaisesRegex(records.LifecycleError,
                                    "COPY_ALREADY_EXISTS"):
            self.run_action("archive", page()["url"], 1,
                            when=page()["observedAt"])
        with self.assertRaisesRegex(records.LifecycleError,
                                    "STALE_MANAGED_REVISION"):
            self.run_action("trash", rid, 0)
        with self.assertRaisesRegex(records.LifecycleError,
                                    "UNKNOWN_MANAGED_RECORD"):
            self.run_action("trash", "f" * 32, 1)
        self.assertEqual(self.run_action("list")["revision"], 1)

    def test_validate_source_before_snapshot_and_reject_other_domains(self):
        for field, val in (
            ("source", "finance-actuals"),
            ("readOnly", False),
            ("url", "https://bank.example/secret"),
            ("observedAt", "not-a-time"),
        ):
            with self.subTest(field=field):
                a = page()
                a[field] = val
                self.source.write_text(json.dumps([a]), encoding="utf-8")
                with self.assertRaises(records.LifecycleError):
                    self.run_action("archive", a["url"], 0, when=a["observedAt"])
                self.assertFalse((self.data / records.STORE_NAME).exists())

    def test_source_symlink_and_missing_file_refuse(self):
        hidden = self.root / "original.json"
        hidden.write_text(json.dumps([page()]))
        self.source.unlink()
        self.source.symlink_to(hidden)
        with self.assertRaisesRegex(records.LifecycleError, "SOURCE_UNREADABLE"):
            self.run_action("archive", page()["url"], 0,
                            when=page()["observedAt"])
        self.source.unlink()
        with self.assertRaisesRegex(records.LifecycleError, "DEMO_SOURCE_MISSING"):
            self.run_action("archive", page()["url"], 0,
                            when=page()["observedAt"])

    def test_corrupt_store_is_not_overwritten_and_symlink_not_followed(self):
        bad = b'{"schema":"broken","records":[]}'
        self.save_store(bad.decode())
        with self.assertRaisesRegex(records.LifecycleError,
                                    "MANAGED_STORE_INVALID"):
            self.run_action("archive", page()["url"], 0,
                            when=page()["observedAt"])
        self.assertEqual((self.data / records.STORE_NAME).read_bytes(), bad)
        (self.data / records.STORE_NAME).unlink()
        hidden = self.root / "keep.json"
        hidden.write_bytes(bad)
        (self.data / records.STORE_NAME).symlink_to(hidden)
        with self.assertRaisesRegex(records.LifecycleError,
                                    "MANAGED_STORE_UNSAFE"):
            self.run_action("list")
        self.assertEqual(hidden.read_bytes(), bad)

    def test_saved_copy_data_is_bounded_and_mode_private(self):
        first = self.run_action("archive", page()["url"], 0,
                                when=page()["observedAt"])
        saved = (self.data / records.STORE_NAME)
        self.assertTrue(saved.is_file())
        self.assertLess(saved.stat().st_size, records.MAX_STORE_BYTES)
        self.assertEqual(saved.stat().st_mode & 0o777, 0o600)
        self.assertEqual(first["items"][0]["kind"], "SAVED RESEARCH")
        self.assertEqual(first["items"][0]["source"], "RESEARCH // DEMO COPY")
        self.assertFalse(any(key in first["items"][0] for key in
                             ("snippets", "links", "payload", "transport")))
        self.assertNotIn("hospital", saved.read_text().lower())
        with self.assertRaisesRegex(records.LifecycleError, "ACTION_NOT_PERMITTED"):
            self.run_action("hospital-delete")

    def test_cli_exposes_explicit_allowlist_and_json_error(self):
        args = [
            ["research_records.py", "burn-all", str(self.data)],
            ["research_records.py", "burn", str(self.data), "a"*32, "0"],
            ["research_records.py", "trash", str(self.data), "a"*32, "zero"],
        ]
        for argv in args:
            with self.subTest(argv=argv):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = records.main(argv)
                self.assertEqual(code, 1)
                self.assertFalse(json.loads(output.getvalue())["ok"])
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(records.main(["research_records.py", "list",
                                           str(self.data)]), 0)
        self.assertTrue(json.loads(output.getvalue())["ok"])


if __name__ == "__main__":
    unittest.main()
