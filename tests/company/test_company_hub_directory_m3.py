"""Company Network M3: disposable private hub registry validation tests."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2] / "services/company/CompanyHubDirectory.py"
spec = importlib.util.spec_from_file_location("company_hub_directory", SOURCE)
hub = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(hub)

ENTRY = {
    "label": "Example Hub",
    "organizationLabel": "Example Partner",
    "city": "Annapolis",
    "regionCode": "MD",
    "countryCode": "US",
    "longitude": -76.49,
    "latitude": 38.98,
    "serviceFamily": "BENEFITS",
}


class CompanyHubDirectoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.xdg = Path(self.temp.name)
        self.context = patch.dict(os.environ, {"XDG_DATA_HOME": str(self.xdg)})
        self.context.start()
        self.addCleanup(self.context.stop)

    def request(self, operation="create", revision=0, **fields):
        payload = {"action": operation, "expectedRevision": revision}
        payload.update(fields)
        return payload

    def test_missing_read_is_empty_and_does_not_create_files(self):
        self.assertEqual(hub.load(), hub.initial())
        self.assertEqual(list(self.xdg.iterdir()), [])

    def test_create_archive_restore_and_revision(self):
        start = hub.initial()
        created = hub.apply(start, self.request(**ENTRY))
        self.assertEqual(created["revision"], 1)
        self.assertEqual(created["nextId"], 2)
        self.assertEqual(created["hubs"][0]["id"], "hub-1")
        self.assertTrue(created["hubs"][0]["reported"])
        self.assertFalse(created["hubs"][0]["archived"])
        with self.assertRaises(hub.HubError) as err:
            hub.apply(created, self.request(**ENTRY))
        self.assertEqual(err.exception.code, "REVISION_CONFLICT")
        archived = hub.apply(created, self.request("archive", 1, hubId="hub-1"))
        self.assertTrue(archived["hubs"][0]["archived"])
        restored = hub.apply(archived, self.request("restore", 2, hubId="hub-1"))
        self.assertFalse(restored["hubs"][0]["archived"])
        self.assertEqual(start, hub.initial())

    def test_schema_rejects_unbounded_or_personal_fields(self):
        request = self.request(**ENTRY)
        for extra in ("employeeName", "clientName", "apiKey", "notes", "claimedVerified"):
            with self.subTest(extra=extra):
                invalid = {**request, extra: "SECRET"}
                with self.assertRaises(hub.HubError) as err:
                    hub.apply(hub.initial(), invalid)
                self.assertEqual(err.exception.code, "INVALID_REQUEST")

    def test_invalid_coordinates_names_and_regions_refused(self):
        for changes in (
            {"longitude": 181},
            {"latitude": -91},
            {"longitude": float("nan")},
            {"latitude": "38.98"},
            {"label": "  "},
            {"label": "bad\ncontrol"},
            {"countryCode": "XX"},
            {"regionCode": "Maryland"},
            {"regionCode": "md"},
            {"serviceFamily": "OTHER"},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(hub.HubError):
                    hub.apply(hub.initial(), self.request(**{**ENTRY, **changes}))

    def test_disk_round_trip_and_owner_permissions(self):
        created = hub.apply(hub.initial(), self.request(**ENTRY))
        hub.save(created)
        folder = self.xdg / "post-apollo" / "company"
        saved_file = folder / "hubs-v1.json"
        self.assertEqual(saved_file.stat().st_mode & 0o777, 0o600)
        self.assertEqual(folder.stat().st_mode & 0o777, 0o700)
        self.assertEqual(hub.load(), created)
        archived = hub.apply(hub.load(), self.request("archive", 1, hubId="hub-1"))
        hub.save(archived)
        self.assertEqual(hub.load(), archived)

    def test_corrupt_and_future_version_refused_not_overwritten(self):
        hub.save(hub.initial())
        target = self.xdg / "post-apollo" / "company" / "hubs-v1.json"
        target.write_text("not json", encoding="utf-8")
        with self.assertRaises(hub.HubError) as err:
            hub.load()
        self.assertEqual(err.exception.code, "INVALID_JSON")
        self.assertEqual(target.read_text(encoding="utf-8"), "not json")
        target.write_text(json.dumps({**hub.initial(), "schema": "future.v2"}))
        with self.assertRaises(hub.HubError) as err:
            hub.load()
        self.assertEqual(err.exception.code, "UNSUPPORTED_VERSION")

    def test_symlink_and_public_files_refused(self):
        hub.save(hub.initial())
        target = self.xdg / "post-apollo" / "company" / "hubs-v1.json"
        target.chmod(0o644)
        with self.assertRaises(hub.HubError):
            hub.load()
        target.unlink()
        outside = self.xdg / "outside.json"
        outside.write_text("do not read")
        target.symlink_to(outside)
        with self.assertRaises(hub.HubError):
            hub.load()


if __name__ == "__main__":
    unittest.main()
