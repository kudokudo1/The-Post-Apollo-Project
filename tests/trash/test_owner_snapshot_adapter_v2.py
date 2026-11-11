"""Synthetic Trash++ V2b owner-source witnesses: no user/host data."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "owner_snapshot_adapter_v2", ROOT / "scripts/trash/owner_snapshot_adapter_v2.py")
adapters = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapters)
from scripts.trash.archive_store_v2 import ArchiveError, ArchiveStore
from scripts.trash import research_records as source


def demo_page():
    return {
        "schemaVersion": 1, "source": "finance-demo-scrapy", "readOnly": True,
        "url": "https://quotes.toscrape.com/page/1/",
        "title": "Synthetic demo page",
        "observedAt": "2026-10-12T10:30:00Z",
        "links": ["https://quotes.toscrape.com/author/Example"],
        "snippets": ["Just a synthetic example"]
    }


def event_record():
    event_key = "usgs|quake-17"
    stamp = 1760001000000
    return {
        "sourceId": "usgs", "eventId": "quake-17", "eventKey": event_key,
        "title": "Test earthquake", "typeLabel": "EARTHQUAKE",
        "firstCapturedAtMs": stamp, "lastCapturedAtMs": stamp,
        "snapshots": [{
            "sourceId": "usgs", "eventId": "quake-17",
            "eventKey": event_key, "capturedAtMs": stamp,
            "payload": {"magnitude": 4.2, "place": "Test Valley"}
        }]
    }


class PilotOwnerAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.home.mkdir(mode=0o700)
        self.data = self.root / "data"
        self.data.mkdir(mode=0o700)
        self.archive_root = self.root / "archive"
        self.archive_root.mkdir(mode=0o700)
        self.archive = ArchiveStore(self.archive_root)
        self.pilot = adapters.PilotSnapshotAdapter(
            self.archive, data_dir=self.data, home_dir=self.home)
        self.crawl = self.home / source.CRAWL_PATH
        self.crawl.parent.mkdir(parents=True)
        self.crawl.write_text(json.dumps([demo_page()]), encoding="utf-8")
        self.weather = self.data / source.WEATHER_EVENT_NAME
        self.save_weather()

    def save_weather(self, event=None, extra=None):
        value = event or event_record()
        doc = {"schema": source.WEATHER_EVENT_SCHEMA, "version": 1,
               "revision": 3, "events": {"usgs|quake-17": value}}
        if extra is not None:
            doc["unrelated"] = extra
        self.weather.write_text(json.dumps(doc), encoding="utf-8")

    def test_demo_preview_capture_roundtrip_does_not_change_owner(self):
        url, when = demo_page()["url"], demo_page()["observedAt"]
        before = self.crawl.read_bytes()
        preview = self.pilot.preview_demo(url, when)
        self.assertEqual(preview["ownerId"], "demo-scrape")
        self.assertNotIn("payload", str(preview))
        self.assertNotIn("snippets", str(preview))
        self.assertEqual(len(preview["sourceRevision"]), 64)
        receipt = self.pilot.capture_demo(
            url, when, expected_revision=preview["sourceRevision"])
        self.assertEqual(receipt["sourceRevision"], preview["sourceRevision"])
        self.assertEqual(self.archive.status()["total"], 1)
        saved = json.loads(self.archive.read_verified(receipt["id"]))
        self.assertEqual(saved["title"], demo_page()["title"])
        self.assertEqual(saved["links"], demo_page()["links"])
        self.assertNotIn("schemaVersion", saved)  # owner-normalized copy
        self.assertEqual(self.crawl.read_bytes(), before)
        self.assertEqual(self.archive.verify()["items"], 1)

    def test_weather_preview_capture_roundtrip_does_not_change_owner(self):
        before = self.weather.read_bytes()
        preview = self.pilot.preview_weather("usgs|quake-17", "1760001000000")
        self.assertEqual(preview["ownerId"], "weather-events")
        self.assertEqual(preview["capturedAtMs"], 1760001000000)
        self.assertNotIn("snapshots", preview)
        receipt = self.pilot.capture_weather(
            "usgs|quake-17", "1760001000000",
            expected_revision=preview["sourceRevision"])
        self.assertEqual(json.loads(self.archive.read_verified(receipt["id"])),
                         event_record())
        self.assertEqual(self.weather.read_bytes(), before)

    def test_stale_demo_same_url_and_timestamp_rewrite_rejected(self):
        page = demo_page()
        preview = self.pilot.preview_demo(page["url"], page["observedAt"])
        changed = copy.deepcopy(page)
        changed["snippets"][0] = "changed same timestamp"
        self.crawl.write_text(json.dumps([changed]), encoding="utf-8")
        with self.assertRaisesRegex(adapters.AdapterError,
                                    "STALE_SOURCE_REFRESH_REQUIRED"):
            self.pilot.capture_demo(
                page["url"], page["observedAt"],
                expected_revision=preview["sourceRevision"])
        self.assertEqual(self.archive.status()["total"], 0)

    def test_stale_weather_same_snapshot_time_rewrite_rejected(self):
        preview = self.pilot.preview_weather("usgs|quake-17", "1760001000000")
        modified = event_record()
        modified["snapshots"][0]["payload"]["magnitude"] = 9.2
        self.save_weather(modified)
        with self.assertRaisesRegex(adapters.AdapterError,
                                    "STALE_SOURCE_REFRESH_REQUIRED"):
            self.pilot.capture_weather(
                "usgs|quake-17", "1760001000000",
                expected_revision=preview["sourceRevision"])
        self.assertEqual(self.archive.status()["total"], 0)

    def test_unrelated_json_change_does_not_invalidate_exact_item_witness(self):
        preview = self.pilot.preview_weather("usgs|quake-17", "1760001000000")
        self.save_weather(extra={"unrelatedFileRevision": 22})
        receipt = self.pilot.capture_weather(
            "usgs|quake-17", "1760001000000",
            expected_revision=preview["sourceRevision"])
        self.assertEqual(receipt["sourceRevision"], preview["sourceRevision"])

    def test_duplicate_exact_source_copy_fails_closed(self):
        page = demo_page()
        witness = self.pilot.preview_demo(page["url"], page["observedAt"])
        self.pilot.capture_demo(
            page["url"], page["observedAt"],
            expected_revision=witness["sourceRevision"])
        with self.assertRaisesRegex(ArchiveError, "SNAPSHOT_ALREADY_EXISTS"):
            self.pilot.capture_demo(
                page["url"], page["observedAt"],
                expected_revision=witness["sourceRevision"])
        self.assertEqual(self.archive.status()["total"], 1)

    def test_unknown_or_malformed_owner_source_is_rejected(self):
        with self.assertRaises(adapters.AdapterError):
            self.pilot.preview_demo("https://example.com/evil", "2026-10-12T10:30:00Z")
        with self.assertRaises(adapters.AdapterError):
            self.pilot.preview_weather("hospital|report-1", "1760001000000")
        self.assertEqual(self.archive.status()["total"], 0)

    def test_missing_or_symlink_source_refused(self):
        page = demo_page()
        preview = self.pilot.preview_demo(page["url"], page["observedAt"])
        self.crawl.unlink()
        with self.assertRaises(adapters.AdapterError):
            self.pilot.capture_demo(
                page["url"], page["observedAt"],
                expected_revision=preview["sourceRevision"])
        self.crawl.symlink_to(self.root / "unrelated.json")
        with self.assertRaises(adapters.AdapterError):
            self.pilot.preview_demo(page["url"], page["observedAt"])
        self.assertEqual(self.archive.status()["total"], 0)

    def test_bad_witness_and_different_source_revision_rejected(self):
        page = demo_page()
        for bad in ("abc", "a"*64, "../", "", None, 1):
            with self.assertRaises(adapters.AdapterError):
                self.pilot.capture_demo(
                    page["url"], page["observedAt"], expected_revision=bad)
        self.assertEqual(self.archive.status()["total"], 0)

    def test_source_timestamp_rewrite_is_refused(self):
        preview = self.pilot.preview_weather("usgs|quake-17", "1760001000000")
        later = event_record()
        later["snapshots"][0]["capturedAtMs"] += 1
        later["lastCapturedAtMs"] += 1
        later["firstCapturedAtMs"] += 1
        self.save_weather(later)
        with self.assertRaises(adapters.AdapterError):
            self.pilot.capture_weather(
                "usgs|quake-17", "1760001000000",
                expected_revision=preview["sourceRevision"])
        self.assertEqual(self.archive.status()["total"], 0)

    def test_invalid_roots_and_archive_type_refused(self):
        for data, home in [("relative", self.home),
                           (self.data, "../parent"),
                           (self.data / "..", self.home)]:
            with self.assertRaisesRegex(adapters.AdapterError,
                                        "INVALID_OWNER_ROOT"):
                adapters.PilotSnapshotAdapter(self.archive, data_dir=data, home_dir=home)
        with self.assertRaisesRegex(adapters.AdapterError, "INVALID_ARCHIVE_STORE"):
            adapters.PilotSnapshotAdapter(object(), data_dir=self.data,
                                          home_dir=self.home)

    def test_valid_long_weather_title_copies_without_metadata_overflow(self):
        full = event_record()
        full["title"] = ("W" * 145) + "\n" + ("A" * 30)
        self.save_weather(full)
        preview = self.pilot.preview_weather("usgs|quake-17", 1760001000000)
        self.assertEqual(len(preview["displayLabel"]), 120)
        self.assertEqual(preview["displayLabel"], "W" * 120)
        row = self.pilot.capture_weather(
            "usgs|quake-17", 1760001000000,
            expected_revision=preview["sourceRevision"])
        self.assertEqual(json.loads(self.archive.read_verified(row["id"]))["title"],
                         full["title"])
        self.assertEqual(self.archive.status()["total"], 1)

    def test_invalid_weather_timestamp_types_fail_before_owner_read(self):
        for value in (True, 0, -4, 99999999999999, "nan", "١٧٦٠٠٠١٠٠٠٠٠٠",
                      "1760001000000.0", [], None):
            with self.assertRaisesRegex(adapters.AdapterError,
                                        "INVALID_EVENT_TIMESTAMP"):
                self.pilot.preview_weather("usgs|quake-17", value)

    def test_no_delete_restore_burn_or_cli(self):
        for verb in ("trash", "restore", "burn", "burn_all", "delete", "migrate"):
            self.assertFalse(hasattr(self.pilot, verb))
        self.assertFalse(hasattr(adapters, "main"))
        self.assertFalse((self.data / source.STORE_NAME).exists())


if __name__ == "__main__":
    unittest.main()
