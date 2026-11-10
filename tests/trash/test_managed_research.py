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


def weather_event():
    snap = {
        "sourceId": "usgs", "sourceLabel": "USGS",
        "eventId": "quake-17", "eventKey": "usgs|quake-17",
        "capturedAtMs": 1760001000000, "sourceTimeMs": 1760000000000,
        "title": "Earthquake test marker", "typeLabel": "EARTHQUAKE",
        "latitude": 34.0, "longitude": -117.0,
        "payload": {
            "magnitude": 4.2, "place": "Test Valley",
            "time": 1760000000000, "updated": 1760001000000,
            "depthKm": 13
        }
    }
    return {
        "sourceId": "usgs", "sourceLabel": "USGS", "eventId": "quake-17",
        "eventKey": "usgs|quake-17", "title": "Earthquake test marker",
        "typeLabel": "EARTHQUAKE",
        "firstCapturedAtMs": 1760001000000,
        "lastCapturedAtMs": 1760001000000,
        "snapshots": [snap]
    }


def weather_document():
    return {
        "schema": records.WEATHER_EVENT_SCHEMA, "version": 1,
        "revision": 3, "events": {"usgs|quake-17": weather_event()}
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

    def test_event_archive_copies_full_snapshot_and_never_mutates_weather(self):
        path = self.data / records.WEATHER_EVENT_NAME
        path.write_text(json.dumps(weather_document()), encoding="utf-8")
        before = path.read_bytes()
        saved = self.run_action("archive-event", "usgs|quake-17", 0,
                                when="1760001000000")
        self.assertEqual(saved["total"], 1)
        self.assertEqual(saved["items"][0]["kind"], "SAVED EVENT")
        self.assertEqual(saved["items"][0]["source"], "WEATHER // EVENT COPY")
        self.assertIn("1 SNAPSHOTS", saved["items"][0]["details"])
        rid = saved["items"][0]["id"]
        self.assertEqual(len(rid), 32)
        store = json.loads((self.data / records.STORE_NAME).read_text())
        self.assertEqual(store["records"][0]["event"], weather_event())
        self.assertEqual(path.read_bytes(), before)
        trashed = self.run_action("trash", rid, 1)
        self.assertEqual(trashed["items"][0]["state"], "trashed")
        restored = self.run_action("restore", rid, 2)
        self.assertEqual(restored["items"][0]["state"], "archived")
        self.run_action("trash", rid, 3)
        self.run_action("burn", rid, 4, "BURN_SAVED_COPY_CONFIRMED")
        self.assertEqual(self.run_action("list")["total"], 0)
        self.assertEqual(path.read_bytes(), before)

    def test_trashing_old_copy_does_not_block_new_demo_or_event_copy(self):
        path = self.data / records.WEATHER_EVENT_NAME
        path.write_text(json.dumps(weather_document()), encoding="utf-8")
        original = path.read_bytes()
        first = self.run_action("archive", page()["url"], 0,
                                when=page()["observedAt"])
        old_demo = first["items"][0]["id"]
        self.run_action("trash", old_demo, 1)
        # Previous v1 content-derived IDs collided even though old item was
        # only in Trash. The fresh copy now has its own unique identity.
        second = self.run_action("archive", page()["url"], 2,
                                 when=page()["observedAt"])
        new_demo = next(x["id"] for x in second["items"]
                        if x["state"] == "archived")
        self.assertNotEqual(old_demo, new_demo)
        self.assertEqual(len(second["items"]), 2)
        event_saved = self.run_action("archive-event", "usgs|quake-17", 3,
                                      when="1760001000000")
        old_event = next(x["id"] for x in event_saved["items"]
                         if x["kind"] == "SAVED EVENT")
        self.run_action("trash", old_event, 4)
        new_event_set = self.run_action("archive-event", "usgs|quake-17", 5,
                                        when="1760001000000")
        new_event = next(x["id"] for x in new_event_set["items"]
                         if x["kind"] == "SAVED EVENT" and x["state"] == "archived")
        self.assertNotEqual(old_event, new_event)
        self.assertEqual(new_event_set["total"], 4)
        # Restoring the old one is still possible; independent saved copies
        # may intentionally coexist.
        both = self.run_action("restore", old_event, 6)
        self.assertEqual(sum(x["kind"] == "SAVED EVENT"
                             and x["state"] == "archived"
                             for x in both["items"]), 2)
        self.assertEqual(path.read_bytes(), original)

    def test_legacy_hashed_demo_record_migrates_without_renaming(self):
        source = records._page(page())
        legacy_id = records._identity(source)
        legacy = {
            "schema": records.STORE_SCHEMA, "version": 1, "revision": 1,
            "records": [{
                "id": legacy_id, "state": "trashed",
                "archivedAtMs": 1760001000000, "page": source
            }]
        }
        self.save_store(json.dumps(legacy))
        new = self.run_action("archive", page()["url"], 1,
                              when=page()["observedAt"])
        self.assertEqual(new["total"], 2)
        self.assertNotEqual(legacy_id, next(x["id"] for x in new["items"]
                                            if x["state"] == "archived"))
        # Legacy item is still individually restorable and burnable.
        self.run_action("restore", legacy_id, 2)
        self.run_action("trash", legacy_id, 3)
        self.run_action("burn", legacy_id, 4, "BURN_SAVED_COPY_CONFIRMED")
        self.assertEqual(self.run_action("list")["total"], 1)

    def test_event_copy_requires_exact_source_identity_and_current_timestamp(self):
        path = self.data / records.WEATHER_EVENT_NAME
        path.write_text(json.dumps(weather_document()))
        for key, stamp in (
            ("usgs|quake-17", "1760000999999"),
            ("finance|quake-17", "1760001000000"),
            ("usgs|not-found", "1760001000000"),
            ("usgs|quake-17", "not-a-timestamp"),
        ):
            with self.subTest(key=key, stamp=stamp):
                with self.assertRaises(records.LifecycleError):
                    self.run_action("archive-event", key, 0, when=stamp)
                self.assertFalse((self.data / records.STORE_NAME).exists())
        source_bytes = path.read_bytes()
        path.unlink()
        hidden = self.root / "weather-protected.json"
        hidden.write_bytes(source_bytes)
        path.symlink_to(hidden)
        with self.assertRaisesRegex(records.LifecycleError, "SOURCE_UNREADABLE"):
            self.run_action("archive-event", "usgs|quake-17", 0,
                            when="1760001000000")
        self.assertEqual(hidden.read_bytes(), source_bytes)

    def test_event_copy_rejects_inconsistent_snapshots_and_oversize(self):
        path = self.data / records.WEATHER_EVENT_NAME
        document = weather_document()
        document["events"]["usgs|quake-17"]["snapshots"][0]["sourceId"] = "other"
        path.write_text(json.dumps(document))
        with self.assertRaisesRegex(records.LifecycleError,
                                    "INVALID_WEATHER_EVENT"):
            self.run_action("archive-event", "usgs|quake-17", 0,
                            when="1760001000000")
        document = weather_document()
        document["events"]["usgs|quake-17"]["snapshots"][0]["payload"]["large"] = "x" * 70000
        path.write_text(json.dumps(document))
        with self.assertRaisesRegex(records.LifecycleError, "EVENT_COPY_TOO_LARGE"):
            self.run_action("archive-event", "usgs|quake-17", 0,
                            when="1760001000000")
        self.assertFalse((self.data / records.STORE_NAME).exists())

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
