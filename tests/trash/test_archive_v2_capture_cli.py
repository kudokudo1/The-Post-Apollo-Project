"""Trash++ V2f explicit pilot CLI: synthetic, isolated sources only."""
from contextlib import redirect_stdout
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/trash/archive_v2_capture_cli.py"
SPEC = importlib.util.spec_from_file_location("v2_capture_cli", SCRIPT)
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)
from scripts.trash.archive_store_v2 import ArchiveStore, ArchiveError, DB_NAME
from scripts.trash.archive_v2_location import archive_directory, PRIVATE_SUBDIR
from scripts.trash.archive_v2_index import index as read_index
from scripts.trash import research_records as source


def page():
    return {"schemaVersion": 1, "source": "finance-demo-scrapy",
            "readOnly": True, "url": "https://quotes.toscrape.com/page/1/",
            "title": "Disposable demo", "observedAt": "2026-10-12T10:30:00Z",
            "links": ["https://quotes.toscrape.com/author/Test"],
            "snippets": ["No live user data"]}


def event():
    ts = 1760001000000
    return {"sourceId": "usgs", "eventId": "test-1",
            "eventKey": "usgs|test-1", "title": "Synthetic quake",
            "typeLabel": "EARTHQUAKE",
            "firstCapturedAtMs": ts, "lastCapturedAtMs": ts,
            "snapshots": [{"sourceId": "usgs", "eventId": "test-1",
                           "eventKey": "usgs|test-1", "capturedAtMs": ts,
                           "payload": {"magnitude": 3.1}}]}


class CaptureCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = self.root / "data"
        self.data.mkdir(mode=0o700)
        self.home = self.root / "home"
        self.home.mkdir(mode=0o700)
        self.crawl = self.home / source.CRAWL_PATH
        self.crawl.parent.mkdir(parents=True)
        self.crawl.write_text(json.dumps([page()]), encoding="utf-8")
        self.weather = self.data / source.WEATHER_EVENT_NAME
        self.weather.write_text(json.dumps({
            "schema": source.WEATHER_EVENT_SCHEMA, "version": 1, "revision": 1,
            "events": {"usgs|test-1": event()}}, separators=(",", ":")),
            encoding="utf-8")

    def request(self, action, kind, identity, stamp, witness=None):
        return cli.execute(action, str(self.data), kind, identity, stamp,
                           witness, home_dir=self.home)

    def test_preview_does_not_create_archive_and_exposes_no_payload(self):
        d = page()
        before = self.crawl.read_bytes()
        result = self.request("preview", "demo", d["url"], d["observedAt"])
        self.assertTrue(result["ok"])
        self.assertTrue(result["readOnly"])
        self.assertEqual(result["preview"]["ownerId"], "demo-scrape")
        self.assertEqual(len(result["preview"]["sourceRevision"]), 64)
        self.assertNotIn("snippets", json.dumps(result))
        self.assertNotIn("links", json.dumps(result))
        self.assertEqual(before, self.crawl.read_bytes())
        self.assertFalse((self.data / DB_NAME).exists())
        self.assertEqual(set(self.data.iterdir()), {self.weather})

    def test_confirm_demo_creates_only_independent_snapshot(self):
        d = page()
        source_bytes = self.crawl.read_bytes()
        witness = self.request("preview", "demo", d["url"], d["observedAt"])
        receipt = self.request("capture", "demo", d["url"], d["observedAt"],
                               witness["preview"]["sourceRevision"])
        self.assertEqual(receipt["kind"], "snapshot-captured-v2")
        self.assertTrue(receipt["copyOnly"])
        self.assertEqual(receipt["receipt"]["ownerId"], "demo-scrape")
        store = ArchiveStore(archive_directory(self.data))
        self.assertEqual(store.status()["total"], 1)
        self.assertEqual(json.loads(store.read_verified(receipt["receipt"]["id"]))["title"],
                         d["title"])
        self.assertEqual(self.crawl.read_bytes(), source_bytes)
        self.assertEqual(store.verify()["items"], 1)

    def test_shared_quickshell_parent_keeps_mode_and_private_snapshot(self):
        # Actual failure: an owned, non-writable 0755 Quickshell.dataDir
        # is not an appropriate SQLite root but can host a 0700 child.
        os.chmod(self.data, 0o755)
        d = page()
        before = self.crawl.read_bytes()
        before_weather = self.weather.read_bytes()
        initial = set(self.data.iterdir())
        self.assertEqual(read_index(str(self.data))["state"], "NOT_INSTALLED")
        self.assertEqual(set(self.data.iterdir()), initial)
        preview = self.request("preview", "demo", d["url"], d["observedAt"])
        self.assertEqual(set(self.data.iterdir()), initial)
        receipt = self.request("capture", "demo", d["url"], d["observedAt"],
                               preview["preview"]["sourceRevision"])
        self.assertEqual(receipt["receipt"]["ownerId"], "demo-scrape")
        self.assertFalse((self.data / DB_NAME).exists())
        protected = self.data / PRIVATE_SUBDIR
        self.assertEqual(protected.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.data.stat().st_mode & 0o777), 0o755)
        self.assertTrue((protected / DB_NAME).exists())
        listed = read_index(str(self.data))
        self.assertEqual(listed["total"], 1)
        self.assertEqual(listed["items"][0]["id"], receipt["receipt"]["id"])
        self.assertEqual(self.crawl.read_bytes(), before)
        self.assertEqual(self.weather.read_bytes(), before_weather)

    def test_weather_preview_and_capture_without_owner_mutation(self):
        before = self.weather.read_bytes()
        witness = self.request("preview", "weather", "usgs|test-1",
                               "1760001000000")
        self.assertEqual(witness["preview"]["ownerId"], "weather-events")
        self.assertFalse((self.data / DB_NAME).exists())
        receipt = self.request("capture", "weather", "usgs|test-1",
                               "1760001000000",
                               witness["preview"]["sourceRevision"])
        self.assertEqual(receipt["receipt"]["ownerId"], "weather-events")
        saved = ArchiveStore(archive_directory(self.data)).read_verified(receipt["receipt"]["id"])
        self.assertEqual(json.loads(saved), event())
        self.assertEqual(self.weather.read_bytes(), before)

    def test_stale_demo_witness_fails_before_database_creation(self):
        d = page()
        witness = self.request("preview", "demo", d["url"], d["observedAt"])
        changed = copy.deepcopy(d)
        changed["snippets"] = ["changed without timestamp advance"]
        self.crawl.write_text(json.dumps([changed]), encoding="utf-8")
        with self.assertRaisesRegex(cli.CaptureCliError,
                                    "STALE_SOURCE_REFRESH_REQUIRED"):
            self.request("capture", "demo", d["url"], d["observedAt"],
                         witness["preview"]["sourceRevision"])
        self.assertFalse((self.data / DB_NAME).exists())

    def test_stale_weather_witness_fails_before_database_creation(self):
        original = event()
        witness = self.request("preview", "weather", "usgs|test-1",
                               "1760001000000")
        original["snapshots"][0]["payload"]["magnitude"] = 9.9
        self.weather.write_text(json.dumps({
            "schema": source.WEATHER_EVENT_SCHEMA, "version": 1, "revision": 2,
            "events": {"usgs|test-1": original}}), encoding="utf-8")
        with self.assertRaisesRegex(cli.CaptureCliError,
                                    "STALE_SOURCE_REFRESH_REQUIRED"):
            self.request("capture", "weather", "usgs|test-1",
                         "1760001000000",
                         witness["preview"]["sourceRevision"])
        self.assertFalse((self.data / DB_NAME).exists())

    def test_duplicate_source_snapshot_fails_closed(self):
        d = page()
        rev = self.request("preview", "demo", d["url"], d["observedAt"])
        witness = rev["preview"]["sourceRevision"]
        self.request("capture", "demo", d["url"], d["observedAt"], witness)
        with self.assertRaisesRegex(ArchiveError, "SNAPSHOT_ALREADY_EXISTS"):
            self.request("capture", "demo", d["url"], d["observedAt"], witness)
        self.assertEqual(ArchiveStore(archive_directory(self.data)).status()["total"], 1)

    def test_wrong_owner_arbitrary_path_and_unsafe_link_refused(self):
        with self.assertRaisesRegex(cli.CaptureCliError,
                                    "SOURCE_NOT_ALLOWLISTED"):
            self.request("preview", "hospital", "room", "1")
        with self.assertRaisesRegex(cli.AdapterError,
                                    "STALE_DEMO_SOURCE_REFRESH"):
            self.request("preview", "demo", "file:///etc/passwd", "2026")
        self.crawl.unlink()
        self.crawl.symlink_to(self.root / "unrelated.json")
        with self.assertRaises(cli.AdapterError):
            self.request("preview", "demo", page()["url"], page()["observedAt"])
        self.assertFalse((self.data / DB_NAME).exists())

    def test_only_preview_and_capture_cli_verbs_and_safe_json(self):
        for verb in ("trash", "burn", "burn-all", "restore", "migrate"):
            out = io.StringIO()
            with redirect_stdout(out):
                code = cli.main(["capture_cli.py", verb, str(self.data),
                                 "weather", "usgs|test-1", "1760001000000"])
            self.assertNotEqual(code, 0)
            result = json.loads(out.getvalue())
            self.assertFalse(result["ok"])
            self.assertEqual(result["error"], "PREVIEW_OR_CAPTURE_ONLY")
        self.assertFalse((self.data / DB_NAME).exists())

    def test_isolated_python_execution_with_fixed_home(self):
        env = dict(os.environ)
        env["HOME"] = str(self.home)
        cmd = [sys.executable, "-I", "-B", str(SCRIPT), "preview",
               str(self.data), "demo", page()["url"], page()["observedAt"]]
        run = subprocess.run(cmd, env=env, cwd=self.root,
                             capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        reply = json.loads(run.stdout)
        self.assertEqual(reply["kind"], "snapshot-preview-v2")
        self.assertFalse((self.data / DB_NAME).exists())

    def test_malformed_witness_fails_before_database_creation(self):
        d = page()
        for value in ("", "a", "Z"*64, "1"*65, None):
            with self.assertRaisesRegex(cli.CaptureCliError,
                                        "INVALID_SOURCE_WITNESS"):
                self.request("capture", "demo", d["url"], d["observedAt"],
                             value)
        self.assertFalse((self.data / DB_NAME).exists())


if __name__ == "__main__":
    unittest.main()
