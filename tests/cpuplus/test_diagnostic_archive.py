import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import cpuplus_diagnostic_archive as archive


def record(n, text="private report"):
    return {"id": "session-abc-def-" + str(n), "kind": "memory",
            "status": "COMPLETE", "summary": "summary", "text": text,
            "finishedAt": "2026-11-24T12:00:00.000Z"}


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name) / "archive"

    def save(self, row):
        return archive.execute(self.folder, {"action": "save", "record": row})

    def read(self):
        return archive.execute(self.folder, {"action": "list"})

    def test_empty_list_and_private_modes(self):
        self.assertEqual(self.read()["rows"], [])
        self.assertFalse(self.folder.exists())
        result = self.save(record(1))
        self.assertEqual(result["savedId"], record(1)["id"])
        self.assertEqual(self.read()["rows"], [record(1)])
        self.assertEqual(self.folder.stat().st_mode & 0o777, 0o700)
        for name in ("reports.json", "archive.lock"):
            self.assertEqual((self.folder/name).stat().st_mode & 0o777, 0o600)

    def test_rolling_bound_exact_id_and_idempotence(self):
        for i in range(1, 11):
            self.save(record(i))
        self.assertEqual(self.read()["rows"], [record(i) for i in range(10, 2, -1)])
        self.save(record(10))
        with self.assertRaises(ValueError):
            self.save(record(10, "different"))
        self.assertEqual(self.read()["rows"][0], record(10))

    def test_invalid_record_and_corrupt_archive_fail_closed(self):
        with self.assertRaises(ValueError):
            self.save(record(1, "x"*65537))
        self.save(record(1))
        path = self.folder / "reports.json"
        path.write_bytes(b"not json")
        with self.assertRaises(ValueError):
            self.save(record(2))
        self.assertEqual(path.read_bytes(), b"not json")

    def test_symlink_and_fifo_refusal(self):
        self.save(record(1))
        path = self.folder/"reports.json"
        outside = Path(self.tmp.name)/"outside"
        outside.write_text("unchanged")
        path.unlink()
        path.symlink_to(outside)
        with self.assertRaises(OSError):
            self.save(record(2))
        self.assertEqual(outside.read_text(), "unchanged")
        path.unlink()
        os.mkfifo(path,0o600)
        with self.assertRaises(ValueError):
            self.read()

    def test_interrupted_replace_preserves_old_document(self):
        self.save(record(1))
        with patch.object(archive.os, "replace", side_effect=OSError("fixture")):
            with self.assertRaises(OSError):
                self.save(record(2))
        self.assertEqual(self.read()["rows"], [record(1)])
        self.assertEqual(sorted(p.name for p in self.folder.iterdir()), ["archive.lock","reports.json"])

    def test_abandoned_private_staging_recovered(self):
        self.save(record(1))
        pending = self.folder / ".pending"
        pending.write_bytes(b"interrupted write")
        pending.chmod(0o600)
        self.save(record(2))
        self.assertFalse(pending.exists())
        self.assertEqual(self.read()["rows"], [record(2), record(1)])

    def test_insecure_mode_and_duplicate_id_refused(self):
        self.save(record(1))
        (self.folder/"reports.json").chmod(0o644)
        with self.assertRaises(ValueError):
            self.read()
        with self.assertRaises(ValueError):
            archive.validate_rows([record(1),record(1)])

    def test_gpu_kind(self):
        row = dict(record(1), kind="gpu")
        self.save(row)
        self.assertEqual(self.read()["rows"], [row])

    def test_host_cpu_kind(self):
        row = dict(record(1), kind="hostcpu")
        self.save(row)
        self.assertEqual(self.read()["rows"], [row])

    def test_workflow_limit_and_aggregate_retention(self):
        large = dict(record(1, chr(92)*300000), kind="workflow")
        self.assertEqual(len(large["text"]),300000)
        self.save(large)
        self.assertEqual(self.read()["rows"], [large])
        with self.assertRaises(ValueError):
            self.save(dict(record(2,"x"*300001),kind="workflow"))
        with self.assertRaises(ValueError):
            self.save(dict(record(2,"é"),kind="workflow"))
        for i in range(2,10):
            self.save(dict(large,id=record(i)["id"]))
        result=self.read()
        self.assertEqual(result["rows"][0]["id"],record(9)["id"])
        self.assertLess(len(archive.encode(result)),archive.MAX_FILE)
        self.assertLess(len(result["rows"]),archive.LIMIT)
        self.assertEqual(len({r["id"] for r in result["rows"]}),len(result["rows"]))
        self.save(record(10))
        self.assertEqual(self.read()["rows"][0],record(10))


if __name__ == "__main__":
    unittest.main()
