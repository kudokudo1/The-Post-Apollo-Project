"""Trash++ V2c read-only Archive page contracts, synthetic data only."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/trash/archive_v2_index.py"
SPEC = importlib.util.spec_from_file_location("trash_v2_index", SOURCE)
indexer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(indexer)
from scripts.trash.archive_store_v2 import ArchiveStore


class ArchiveV2IndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def make_archive(self):
        return ArchiveStore(self.root)

    def index(self, cursor=""):
        return indexer.index(str(self.root), cursor)

    def test_missing_store_does_not_create_database(self):
        before = set(self.root.iterdir())
        result = self.index()
        self.assertTrue(result["ok"])
        self.assertEqual(result["state"], "NOT_INSTALLED")
        self.assertEqual(result["items"], [])
        self.assertEqual(result["total"], 0)
        self.assertEqual(set(self.root.iterdir()), before)

    def test_pages_are_bounded_and_metadata_only(self):
        store = self.make_archive()
        for i in range(57):
            store.save("demo-scrape", "page-1", "rev-" + str(i),
                       b"PRIVATE PAYLOAD " + str(i).encode(), "Title " + str(i),
                       captured_ms=1760000000000 + i)
        seen, cursor, page_count = [], "", 0
        before = store.path.read_bytes()
        before_mode = store.path.stat().st_mode
        while True:
            result = self.index(cursor)
            page_count += 1
            self.assertEqual(result["kind"], "archive-v2-index")
            self.assertTrue(result["readOnly"])
            self.assertLessEqual(len(result["items"]), indexer.PAGE_SIZE)
            self.assertEqual(result["total"], 57)
            self.assertNotIn("PRIVATE PAYLOAD", json.dumps(result))
            for item in result["items"]:
                self.assertEqual(item["kind"], "V2 SNAPSHOT")
                self.assertEqual(item["state"], "archived-v2")
                self.assertTrue(item["copyOnly"])
                self.assertFalse(item["verified"])
                self.assertFalse(item["capabilities"]["burn"])
                self.assertFalse(item["capabilities"]["trash"])
                self.assertFalse(item["capabilities"]["restore"])
                self.assertIn("PAYLOAD NOT VERIFIED", item["details"])
                seen.append(item["id"])
            if not result["hasMore"]:
                self.assertIsNone(result["nextCursor"])
                break
            cursor = result["nextCursor"]
        self.assertEqual(page_count, 3)
        self.assertEqual(len(seen), 57)
        self.assertEqual(len(set(seen)), 57)
        self.assertEqual(store.path.read_bytes(), before)
        self.assertEqual(store.path.stat().st_mode, before_mode)

    def test_global_search_across_all_pages_and_owners(self):
        store = self.make_archive()
        for i in range(80):
            label = ("Alpha" if i % 2 == 0 else "Bravo") + f" report {i}"
            owner = "demo-scrape" if i % 4 else "weather-events"
            store.save(owner, "file-" + str(i), "rev" + str(i),
                       b"PRIVATE PAYLOAD", label,
                       captured_ms=1760000000000 + i)
        seen, cursor = [], ""
        while True:
            result = indexer.index(str(self.root), cursor, "ALPHA")
            self.assertEqual(result["total"], 40)
            self.assertEqual(result["query"], "ALPHA")
            self.assertNotIn("PRIVATE PAYLOAD", json.dumps(result))
            self.assertLessEqual(len(result["items"]), indexer.PAGE_SIZE)
            for row in result["items"]:
                self.assertIn("alpha", row["title"].lower())
                seen.append(row["id"])
            if not result["hasMore"]:
                break
            cursor = result["nextCursor"]
        self.assertEqual(len(seen), 40)
        self.assertEqual(len(set(seen)), 40)
        research_only = indexer.index(str(self.root), query="demo-scrape")
        self.assertEqual(research_only["total"], 60)
        self.assertEqual(len(research_only["items"]), 25)
        by_id = indexer.index(str(self.root), query="file-79")
        self.assertEqual(by_id["total"], 1)
        self.assertEqual(by_id["items"][0]["resourceId"], "file-79")

    def test_search_sql_wildcards_and_injection_are_literal(self):
        store = self.make_archive()
        store.save("demo-scrape", "p-a", "r1", b"a", "Budget_100%")
        store.save("demo-scrape", "p-b", "r2", b"b", "Budget XX 100")
        underscore = indexer.index(str(self.root), query="_100%")
        self.assertEqual(underscore["total"], 1)
        self.assertEqual(underscore["items"][0]["title"], "Budget_100%")
        percent = indexer.index(str(self.root), query="%")
        self.assertEqual(percent["total"], 1)
        query = "' OR 1=1 --"
        self.assertEqual(indexer.index(str(self.root), query=query)["total"], 0)
        self.assertEqual(indexer.index(str(self.root), query="nonexistent")["items"], [])
        self.assertEqual(store.verify()["items"], 2)

    def test_invalid_search_query_fails_closed_without_source(self):
        for query in (None, 9, [], "x" * (indexer.MAX_QUERY_LENGTH + 1),
                      "row\\nother".replace("\\n", "\n"), "\x00", "\x1f"):
            with self.assertRaisesRegex(indexer.ReadIndexError,
                                        "INVALID_SEARCH_QUERY"):
                indexer.index(str(self.root), query=query)
        result = indexer.index(str(self.root), query="no matches")
        self.assertEqual(result["state"], "NOT_INSTALLED")
        self.assertEqual(result["query"], "no matches")
        self.assertFalse((self.root / indexer.DB_NAME).exists())

    def test_search_uses_pinned_read_only_database_state(self):
        store = self.make_archive()
        snap = store.save("demo-scrape", "record-1", "rev1", b"DATA", "Search me")
        before = store.path.read_bytes()
        out = io.StringIO()
        with redirect_stdout(out):
            code = indexer.main(["archive_v2_index.py", "index",
                                 str(self.root), "", "search"])
        self.assertEqual(code, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["query"], "search")
        self.assertFalse(result["items"][0]["capabilities"]["burn"])
        self.assertEqual(store.path.read_bytes(), before)
        self.assertEqual(store.read_verified(snap["id"]), b"DATA")

    def test_weather_owner_is_labeled_as_copy(self):
        store = self.make_archive()
        store.save("weather-events", "event-x", "rev-1", b"synthetic", "Test alert")
        result = self.index()
        self.assertEqual(result["items"][0]["source"], "WEATHER // V2 COPY")
        self.assertTrue(result["items"][0]["copyOnly"])
        self.assertEqual(result["items"][0]["title"], "Test alert")

    def test_duplicate_timestamp_page_cursor_is_stable(self):
        store = self.make_archive()
        for i in range(30):
            store.save("demo-scrape", "fixture", "rev" + str(i),
                       b"synthetic", captured_ms=1760000000000)
        p1 = self.index()
        self.assertTrue(p1["hasMore"])
        p2 = self.index(p1["nextCursor"])
        self.assertEqual(len(p1["items"]), 25)
        self.assertEqual(len(p2["items"]), 5)
        self.assertFalse(p2["hasMore"])
        self.assertFalse({x["id"] for x in p1["items"]}
                         & {x["id"] for x in p2["items"]})

    def test_invalid_cursor_fails_without_file_mutation(self):
        store = self.make_archive()
        snap = store.save("demo-scrape", "r", "1", b"synthetic")
        before = store.path.read_bytes()
        for value in ("broken", "1:../evil", "0:" + "a"*32,
                      "99999999999999:"+"a"*32, "123:abc", None, 12):
            with self.assertRaisesRegex(indexer.ReadIndexError,
                                        "INVALID_PAGE_CURSOR"):
                self.index(value)
        self.assertEqual(store.path.read_bytes(), before)
        self.assertEqual(store.read_verified(snap["id"]), b"synthetic")

    def test_invalid_archive_schema_refuses_page(self):
        store = self.make_archive()
        store.save("demo-scrape", "r", "1", b"synthetic")
        with sqlite3.connect(store.path) as db:
            db.execute("UPDATE archive_meta SET schema_id='unexpected'")
        with self.assertRaisesRegex(indexer.ReadIndexError,
                                    "ARCHIVE_SCHEMA_UNSUPPORTED"):
            self.index()

    def test_invalid_row_metadata_refuses_entire_page(self):
        store = self.make_archive()
        snap = store.save("demo-scrape", "r", "1", b"synthetic")
        with sqlite3.connect(store.path) as db:
            db.execute("UPDATE snapshots SET owner_id='hospital' WHERE id=?",
                       (snap["id"],))
        with self.assertRaisesRegex(indexer.ReadIndexError,
                                    "ARCHIVE_OWNER_UNAUTHORIZED"):
            self.index()

    def test_symlinked_database_and_root_refused(self):
        store = self.make_archive()
        store.path.unlink()
        store.path.symlink_to(self.root / "elsewhere")
        with self.assertRaisesRegex(indexer.ReadIndexError, "ARCHIVE_FILE_UNSAFE"):
            self.index()
        store.path.unlink()
        link = self.root / "alias"
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(indexer.ReadIndexError, "ARCHIVE_ROOT_UNSAFE"):
            indexer.index(str(link))

    def test_sidecars_and_unprivate_directory_refused(self):
        store = self.make_archive()
        sidecar = self.root / (indexer.DB_NAME + "-wal")
        sidecar.symlink_to(self.root / "outside")
        with self.assertRaisesRegex(indexer.ReadIndexError,
                                    "ARCHIVE_UNEXPECTED_SIDECAR"):
            self.index()
        sidecar.unlink()
        os.chmod(self.root, 0o755)
        try:
            with self.assertRaisesRegex(indexer.ReadIndexError,
                                        "ARCHIVE_ROOT_UNSAFE"):
                self.index()
        finally:
            os.chmod(self.root, 0o700)

    def test_invalid_sqlite_database_fails_closed(self):
        (self.root / indexer.DB_NAME).write_bytes(b"not SQLite")
        with self.assertRaisesRegex(indexer.ReadIndexError,
                                    "ARCHIVE_FILE_UNSAFE"):
            self.index()
        os.chmod(self.root / indexer.DB_NAME, 0o600)
        with self.assertRaisesRegex(indexer.ReadIndexError,
                                    "ARCHIVE_INDEX_UNAVAILABLE"):
            self.index()

    def test_only_read_only_index_cli_action(self):
        for verb in ("burn", "delete", "migrate", "save", "restore"):
            out = io.StringIO()
            with redirect_stdout(out):
                code = indexer.main(["archive_v2_index.py", verb, str(self.root)])
            self.assertNotEqual(code, 0)
            self.assertEqual(json.loads(out.getvalue())["error"],
                             "READ_ONLY_INDEX_ONLY")
        self.assertFalse((self.root / indexer.DB_NAME).exists())

    def test_index_does_not_create_empty_database_on_read_only_query(self):
        before = set(self.root.iterdir())
        out = io.StringIO()
        with redirect_stdout(out):
            code = indexer.main(["archive_v2_index.py", "index", str(self.root)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue())["state"], "NOT_INSTALLED")
        self.assertEqual(before, set(self.root.iterdir()))


if __name__ == "__main__":
    unittest.main()
