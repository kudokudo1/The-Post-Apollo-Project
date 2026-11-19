"""Safe unit tests of combined ALL Burn. Mocks BOTH destructive backends."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2] / "scripts/trash/trash_all_cli.py"
spec = importlib.util.spec_from_file_location("trash_all_cli", SOURCE)
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)
H = "a" * 64
M = "b" * 64


class AllBurnTests(unittest.TestCase):
    def command(self, *, files=1, copies=1, fail="", stale=""):
        calls = []
        def backend(script, argv, timeout):
            name = script.name
            calls.append((name, list(argv)))
            if name == "trash_cli.py" and argv[0] == "index":
                return {"ok": True, "kind": "index", "complete": True,
                        "revision": "c" * 64 if stale == "files" else H,
                        "total": files + (1 if stale == "count" else 0)}
            if name == "research_records.py" and argv[0] == "list":
                return {"ok": True, "kind": "managed-research",
                        "revision": 7 if stale == "copies" else 6,
                        "binCount": copies,
                        "binDigest": "d" * 64 if stale == "digest" else M,
                        "items": ([{"state": "trashed"}] * copies
                                  + [{"state": "archived"}])}
            if fail == "managed" and name == "research_records.py":
                raise subject.Refused("MANAGED_IO_UNCERTAIN")
            if name == "research_records.py":
                return {"ok": True, "kind": "managed-research",
                        "verified": fail != "managed-unverified",
                        "burnedCount": copies,
                        "burnedItems": [
                            {"name": "Disposable copy", "kind": "SAVED RESEARCH",
                             "source": "DEMO"} for _ in range(copies)]}
            if fail == "gio":
                raise subject.Refused("GIO_IO_UNCERTAIN")
            return {"ok": True, "kind": "burn-all", "count": files,
                    "verified": fail != "gio-unverified",
                    "partial": fail == "gio-unverified",
                    "remainingCount": 0 if fail != "gio-unverified" else files,
                    "burnedCount": files,
                    "burnedItems": [
                        {"name": "Disposable file", "kind": "SYSTEM FILE",
                         "original": "/private/disposable.txt"}
                        for _ in range(files)]}
        with patch.object(subject, "_run", side_effect=backend):
            if stale:
                with self.assertRaisesRegex(subject.Refused, "STALE_"):
                    subject.combined("/private/test", H, files, 6, copies, M,
                                     subject.CONFIRM)
                return calls, None
            return calls, subject.combined(
                "/private/test", H, files, 6, copies, M, subject.CONFIRM)

    def test_both_scopes_report_only_backend_verified_items(self):
        calls, result = self.command()
        self.assertTrue(result["verified"])
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["burnedCount"], 2)
        self.assertEqual([c[1][0] for c in calls],
                         ["index", "list", "burn-all", "burn-all"])
        self.assertEqual(calls[2][0], "research_records.py")
        self.assertEqual(calls[3][0], "trash_cli.py")

    def test_missing_confirmation_cannot_call_either_backend(self):
        with patch.object(subject, "_run") as backend:
            with self.assertRaisesRegex(subject.Refused, "CONFIRMATION_REQUIRED"):
                subject.combined("/private/test", H, 1, 6, 1, M, "NO")
            backend.assert_not_called()

    def test_stale_any_scope_refuses_without_mutation(self):
        for stale in ("files", "count", "copies", "digest"):
            with self.subTest(stale=stale):
                calls, result = self.command(stale=stale)
                self.assertIsNone(result)
                self.assertEqual([c[1][0] for c in calls], ["index", "list"]
                                 if stale in ("copies", "digest") else ["index"])

    def test_first_scope_failure_never_empties_gio(self):
        calls, result = self.command(fail="managed")
        self.assertFalse(result["verified"])
        self.assertTrue(result["partial"])
        self.assertEqual(result["burnedCount"], 0)
        self.assertEqual(result["failureStage"], "MANAGED")
        self.assertNotIn(("trash_cli.py", ["burn-all", H, "1",
                                          "BURN_ALL_CONFIRMED"]), calls)

    def test_second_scope_failure_reports_partial(self):
        calls, result = self.command(fail="gio")
        self.assertFalse(result["verified"])
        self.assertTrue(result["partial"])
        self.assertEqual(result["burnedCount"], 1)
        self.assertEqual(result["failureStage"], "SYSTEM")
        self.assertEqual([x["kind"] for x in result["burnedItems"]],
                         ["SAVED RESEARCH"])
        self.assertEqual(calls[-1][0], "trash_cli.py")

    def test_unverified_receipt_stops_before_next_backend(self):
        calls, result = self.command(fail="managed-unverified")
        self.assertFalse(result["verified"])
        self.assertTrue(result["partial"])
        self.assertEqual(result["burnedCount"], 1)
        self.assertEqual([c[1][0] for c in calls],
                         ["index", "list", "burn-all"])

    def test_one_empty_scope_skips_that_writer(self):
        for files, copies in ((0, 1), (1, 0)):
            with self.subTest(files=files, copies=copies):
                calls, result = self.command(files=files, copies=copies)
                self.assertTrue(result["verified"])
                self.assertEqual(result["count"], 1)
                mutations = [c[0] for c in calls if c[1][0] == "burn-all"]
                self.assertEqual(mutations,
                                 ["research_records.py"] if copies else
                                 ["trash_cli.py"])

    def test_empty_all_and_invalid_witness_are_denied(self):
        with patch.object(subject, "_run") as backend:
            for files, copies, digest in ((0, 0, M), (1, 1, "bad")):
                with self.assertRaises(subject.Refused):
                    subject.combined("/private/test", H, files, 6, copies,
                                     digest, subject.CONFIRM)
            backend.assert_not_called()


if __name__ == "__main__":
    unittest.main()
