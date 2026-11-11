"""Trash++ record index contract: synthetic owner data only, no user writes."""
import importlib.util
import io
import json
from pathlib import Path
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/trash/record_index.py"
spec = importlib.util.spec_from_file_location("postapollo_record_index", SCRIPT)
indexer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(indexer)


def event_doc():
    return {
        "schema": indexer.EVENT_SCHEMA, "version": 1, "revision": 3,
        "events": {
            "usgs|quake-17": {
                "sourceId": "usgs", "eventId": "quake-17",
                "title": "Earthquake test marker",
                "snapshots": [
                    {"capturedAtMs": 1760000000000},
                    {"capturedAtMs": 1760001000000},
                ],
            },
        }
    }


def dossier_doc():
    return {
        "schema": indexer.DOSSIER_SCHEMA, "version": 1, "revision": 6,
        "entries": [
            {
                "sourceId": "gdacs", "eventId": "storm-1", "sequence": 4,
                "capturedAtMs": 1760002000000,
                "transport": "opaque-authored-envelope-do-not-copy-into-index",
            },
        ],
    }


def crawl_doc():
    return [{
        "schemaVersion": 1, "source": "finance-demo-scrapy",
        "readOnly": True,
        "url": "https://quotes.toscrape.com/page/1/",
        "title": "Demo saved quote crawl",
        "observedAt": "2026-10-12T10:30:00Z",
        "links": ["https://quotes.toscrape.com/author/Example"],
        "snippets": ["Not indexed: account number or source extract"],
    }]


def hub_notes_doc():
    return {
        "version": 1, "nextId": 3,
        "notes": [{
            "id": "n2", "title": "Garden notes",
            "body": "PRIVATE BODY // keep out of Trash inventory",
            "revision": 4,
            "createdAtMs": 1760000000000,
            "updatedAtMs": 1760002000000,
        }],
    }


def hub_todo_doc():
    return {
        "version": 3, "nextId": 3, "nextProjectId": 2,
        "projects": [{
            "id": "p1", "name": "Home",
            "createdAtMs": 1760000000000,
            "updatedAtMs": 1760000000000,
        }],
        "tasks": [{
            "id": "t2", "title": "Review receipts", "done": False,
            "createdAtMs": 1760000000000,
            "updatedAtMs": 1760003000000,
            "priority": "medium",
            "description": "PRIVATE TASK DESCRIPTION // do not export",
            "dueDate": "2026-11-30", "projectId": "p1",
        }],
    }


class RecordIndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = self.root / "quickshell-data"
        self.data.mkdir()
        self.home = self.root / "home"
        self.home.mkdir()
        self.crawl_path = (self.home / ".local/share/post-apollo/finance-crawler/"
                           "crawl-records.json")
        self.crawl_path.parent.mkdir(parents=True)

    def save(self, path, document):
        path.write_text(json.dumps(document), encoding="utf-8")

    def test_known_archive_sources_render_records_with_identity_and_time(self):
        self.save(self.data / "weather-event-archive-v1.json", event_doc())
        self.save(self.data / "weather-dossier-archive-v1.json", dossier_doc())
        self.save(self.crawl_path, crawl_doc())
        result = indexer.index(str(self.data), self.home)
        self.assertTrue(result["ok"])
        self.assertTrue(result["readOnly"])
        self.assertEqual(result["kind"], "record-index")
        self.assertEqual(result["total"], 3)
        self.assertEqual([s["state"] for s in result["sources"]],
                         ["READY", "READY", "READY", "EMPTY", "EMPTY"])
        rows = {x["kind"]: x for x in result["items"]}
        self.assertEqual(rows["EVENT HISTORY"]["title"], "Earthquake test marker")
        self.assertIn("2 SNAPSHOTS", rows["EVENT HISTORY"]["details"])
        self.assertEqual(rows["EVENT HISTORY"]["sourceEventKey"], "usgs|quake-17")
        self.assertEqual(rows["EVENT HISTORY"]["sourceLastCapturedAtMs"],
                         1760001000000)
        self.assertEqual(rows["SAVED DOSSIER"]["title"], "storm-1")
        self.assertEqual(rows["WEB SCRAPE"]["title"], "Demo saved quote crawl")
        self.assertEqual(rows["WEB SCRAPE"]["sourceUrl"],
                         "https://quotes.toscrape.com/page/1/")
        self.assertEqual(rows["WEB SCRAPE"]["sourceObservedAt"],
                         "2026-10-12T10:30:00Z")
        for row in result["items"]:
            self.assertTrue(row["capabilities"]["inspect"])
            for op in ("archive", "trash", "restore", "burn"):
                self.assertFalse(row["capabilities"][op])
            self.assertEqual(row["retention"], "SOURCE OWNED // READ ONLY")
            self.assertIn("UTC", row["recordedAt"])
            self.assertGreater(row["recordedAtMs"], 0)
            self.assertNotIn("opaque-authored-envelope", str(row))
            self.assertNotIn("Not indexed: account number", str(row))

    def test_no_sources_is_successfully_empty_not_claimed_live_data(self):
        result = indexer.index(str(self.data), self.home)
        self.assertEqual(result["total"], 0)
        self.assertEqual([s["state"] for s in result["sources"]],
                         ["EMPTY", "EMPTY", "EMPTY", "EMPTY", "EMPTY"])

    def test_each_source_failure_isolated_and_never_erases_other_rows(self):
        self.save(self.data / "weather-event-archive-v1.json", event_doc())
        (self.data / "weather-dossier-archive-v1.json").write_text("not-json")
        self.save(self.crawl_path, crawl_doc())
        result = indexer.index(str(self.data), self.home)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["sources"][0]["state"], "READY")
        self.assertEqual(result["sources"][1]["state"], "INVALID_SOURCE_JSON")
        self.assertEqual(result["sources"][2]["state"], "READY")

    def test_symlink_and_directory_refused_without_following(self):
        hidden = self.root / "hidden.json"
        self.save(hidden, event_doc())
        (self.data / "weather-event-archive-v1.json").symlink_to(hidden)
        (self.data / "weather-dossier-archive-v1.json").mkdir()
        result = indexer.index(str(self.data), self.home)
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["sources"][0]["state"], "SOURCE_UNREADABLE")
        self.assertEqual(result["sources"][1]["state"], "SOURCE_UNSAFE_OR_OVERSIZE")

    def test_oversize_and_malformed_schema_refuse_without_fallback_writes(self):
        (self.data / "weather-event-archive-v1.json").write_bytes(b"x" * 100)
        self.save(self.data / "weather-dossier-archive-v1.json",
                  {"schema": "unknown", "entries": []})
        limited_sources = ((indexer.SOURCES[0][0], indexer.SOURCES[0][1],
                            indexer.SOURCES[0][2], 50),) + indexer.SOURCES[1:]
        with patch.object(indexer, "SOURCES", limited_sources):
            result = indexer.index(str(self.data), self.home)
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["sources"][0]["state"], "SOURCE_UNSAFE_OR_OVERSIZE")
        self.assertEqual(result["sources"][1]["state"], "INVALID_SOURCE_SCHEMA")

    def test_rejects_unknown_weather_identity_instead_of_guessing(self):
        doc = event_doc()
        doc["events"]["usgs|quake-17"]["sourceId"] = "finance"
        self.save(self.data / "weather-event-archive-v1.json", doc)
        result = indexer.index(str(self.data), self.home)
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["sources"][0]["state"], "INVALID_SOURCE_SCHEMA")

    def test_rejects_real_finance_or_arbitrary_web_crawls(self):
        for field, value in (
            ("source", "finance-transactions"),
            ("readOnly", False),
            ("url", "https://bank.example/private"),
            ("url", "https://quotes.toscrape.com:abc/private"),
        ):
            with self.subTest(field=field):
                doc = crawl_doc()
                doc[0][field] = value
                self.save(self.crawl_path, doc)
                result = indexer.index(str(self.data), self.home)
                self.assertEqual(result["sources"][2]["state"],
                                 "INVALID_SOURCE_SCHEMA")
                self.assertEqual(result["total"], 0)

    def test_hub_notes_and_tasks_are_read_only_metadata_only(self):
        notes_path = self.data / "apollo-hub-notes-v1.json"
        tasks_path = self.data / "apollo-hub-todo-v1.json"
        self.save(notes_path, hub_notes_doc())
        self.save(tasks_path, hub_todo_doc())
        old_notes = notes_path.read_bytes()
        old_tasks = tasks_path.read_bytes()
        result = indexer.index(str(self.data), self.home)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["resourceContract"], indexer.RESOURCE_CONTRACT)
        self.assertEqual([s["state"] for s in result["sources"]],
                         ["EMPTY", "EMPTY", "EMPTY", "READY", "READY"])
        rows = {row["kind"]: row for row in result["items"]}
        self.assertEqual(rows["HUB NOTE"]["id"], "hub-note:n2")
        self.assertEqual(rows["HUB NOTE"]["ownerId"], "apollo-hub-notes")
        self.assertEqual(rows["HUB NOTE"]["title"], "Garden notes")
        self.assertEqual(rows["HUB TASK"]["id"], "hub-task:t2")
        self.assertEqual(rows["HUB TASK"]["ownerId"], "apollo-hub-todo")
        self.assertIn("OPEN", rows["HUB TASK"]["details"])
        for row in rows.values():
            self.assertEqual(row["resourceContract"], indexer.RESOURCE_CONTRACT)
            self.assertEqual(row["resourceId"], row["id"])
            self.assertEqual(row["retention"], "SOURCE OWNED // READ ONLY")
            self.assertTrue(row["capabilities"]["inspect"])
            self.assertFalse(row["capabilities"]["saveCopy"])
            for action in ("archive", "trash", "restore", "burn"):
                self.assertFalse(row["capabilities"][action])
        serial = json.dumps(result)
        self.assertNotIn("PRIVATE BODY", serial)
        self.assertNotIn("PRIVATE TASK DESCRIPTION", serial)
        self.assertNotIn("apollo-hub-notes-v1.json", serial)
        self.assertNotIn("apollo-hub-todo-v1.json", serial)
        self.assertEqual(notes_path.read_bytes(), old_notes)
        self.assertEqual(tasks_path.read_bytes(), old_tasks)

    def test_existing_event_and_demo_copy_permissions_are_explicit(self):
        self.save(self.data / "weather-event-archive-v1.json", event_doc())
        self.save(self.crawl_path, crawl_doc())
        data = indexer.index(str(self.data), self.home)
        self.assertEqual({r["kind"] for r in data["items"]},
                         {"EVENT HISTORY", "WEB SCRAPE"})
        self.assertTrue(all(r["capabilities"]["saveCopy"] for r in data["items"]))
        self.assertTrue(all(r["capabilities"]["burn"] is False for r in data["items"]))

    def test_hub_future_schema_malformed_record_and_stale_ids_fail_closed(self):
        notes_path = self.data / "apollo-hub-notes-v1.json"
        for edit in (
            lambda d: d.update(version=44),
            lambda d: d["notes"][0].update(id="n999"),
            lambda d: d["notes"][0].update(body="broken" + chr(0) + "control"),
            lambda d: d["notes"].append(dict(d["notes"][0])),
        ):
            doc = hub_notes_doc()
            edit(doc)
            self.save(notes_path, doc)
            result = indexer.index(str(self.data), self.home)
            self.assertEqual(result["sources"][3]["state"],
                             "INVALID_SOURCE_SCHEMA")
            self.assertEqual(result["total"], 0)

    def test_hub_todo_versions_and_invalid_project_refs(self):
        tasks_path = self.data / "apollo-hub-todo-v1.json"
        self.save(tasks_path, hub_todo_doc())
        result = indexer.index(str(self.data), self.home)
        self.assertEqual(result["total"], 1)
        invalid = hub_todo_doc()
        invalid["tasks"][0]["projectId"] = "p999"
        self.save(tasks_path, invalid)
        result = indexer.index(str(self.data), self.home)
        self.assertEqual(result["sources"][4]["state"], "INVALID_SOURCE_SCHEMA")
        old = hub_todo_doc()
        old["version"] = 1
        old["tasks"][0] = {
            "id": "t2", "title": "Legacy task", "done": True,
            "createdAtMs": 1760000000000, "updatedAtMs": 1760003000000,
        }
        old.pop("nextProjectId")
        old.pop("projects")
        self.save(tasks_path, old)
        rows = indexer.index(str(self.data), self.home)["items"]
        self.assertEqual(rows[0]["title"], "Legacy task")
        self.assertIn("DONE", rows[0]["details"])

    def test_new_source_symlinks_and_oversize_fail_without_following(self):
        secret = self.root / "unrelated-notes.json"
        self.save(secret, hub_notes_doc())
        notes_path = self.data / "apollo-hub-notes-v1.json"
        notes_path.symlink_to(secret)
        tasks_path = self.data / "apollo-hub-todo-v1.json"
        self.save(tasks_path, hub_todo_doc())
        result = indexer.index(str(self.data), self.home)
        self.assertEqual(result["sources"][3]["state"], "SOURCE_UNREADABLE")
        self.assertEqual(result["sources"][4]["state"], "READY")
        self.assertEqual(result["total"], 1)
        self.assertEqual(secret.read_bytes(), json.dumps(hub_notes_doc()).encode())
        tasks_path.write_bytes(b"x" * (indexer.MAX_HUB_DOC_BYTES + 1))
        result = indexer.index(str(self.data), self.home)
        self.assertEqual(result["sources"][4]["state"],
                         "SOURCE_UNSAFE_OR_OVERSIZE")
        self.assertEqual(result["total"], 0)

    def test_unlisted_hospital_and_finance_records_never_discovered(self):
        self.save(self.data / "hospital-room-evidence.json",
                  {"reports": [{"title": "PROTECTED PRIVATE EVIDENCE"}]})
        self.save(self.data / "finance-transaction-v1.json",
                  {"transactions": [{"title": "PROTECTED FINANCE"}]})
        result = indexer.index(str(self.data), self.home)
        self.assertEqual(result["total"], 0)
        self.assertEqual(len(result["sources"]), 5)
        self.assertNotIn("PROTECTED", json.dumps(result))
        self.assertFalse(any(row["capabilities"].get("burn")
                             for row in result["items"]))

    def test_only_index_cli_action_exposed(self):
        for args in (["record_index.py", "burn", str(self.data)],
                     ["record_index.py", "delete", str(self.data)],
                     ["record_index.py", "index"],
                     ["record_index.py", "restore", str(self.data)]):
            with self.subTest(args=args):
                output = io.StringIO()
                with redirect_stdout(output):
                    status = indexer.main(args)
                self.assertEqual(status, 1)
                self.assertEqual(json.loads(output.getvalue())["error"],
                                 "READ_ONLY_INDEX_ONLY")
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(indexer.main(["record_index.py", "index",
                                           str(self.data)]), 0)
        self.assertTrue(json.loads(output.getvalue())["readOnly"])

    def test_index_is_not_an_arbitrary_directory_scanner(self):
        with self.assertRaises(indexer.IndexErrorSafe):
            indexer.index("../../home", self.home)
        # This implementation opens only five fixed, approved source filenames; it has
        # neither traversal nor a mutating syscall.
        source = SCRIPT.read_text()
        for unsafe in ("subprocess.run(", "shutil.rmtree(", "os.unlink(",
                       "os.remove(", "os.rename(", "os.replace(", "os.mkdir(",
                       "Path.write_text(", "Path.unlink("):
            self.assertNotIn(unsafe, source)


if __name__ == "__main__":
    unittest.main()
