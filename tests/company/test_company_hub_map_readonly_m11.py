"""M11 owner-local Company map read-only projection, with no real user files."""
from __future__ import annotations
import contextlib
import io
import json
import os
from pathlib import Path
from unittest.mock import patch
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "services" / "company"
sys.path.insert(0, str(SRC))
import CompanyHubDirectory as directory
import CompanyHubMapReadOnly as bridge

ENTRY = {
    "label":"Sensitive Demo Label",
    "organizationLabel":"Sensitive Example Organization",
    "city":"Example City",
    "regionCode":"MD",
    "countryCode":"US",
    "longitude":-76.4901,
    "latitude":38.9801,
    "serviceFamily":"HEALTHCARE",
}


def populated():
    return directory.apply(directory.initial(),
        {"action":"create","expectedRevision":0,**ENTRY})


class OwnerLocalMapReadOnlyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        env = patch.dict(os.environ, {"XDG_DATA_HOME":self.temp.name})
        env.start()
        self.addCleanup(env.stop)

    def test_projection_contains_only_location_claims(self):
        d=populated()
        result=bridge.projection(d)
        self.assertEqual(result["schema"],bridge.SCHEMA)
        self.assertEqual(result["revision"],1)
        self.assertEqual(result["authority"],
                         "OWNER_LOCAL_ONLY_NOT_ORGANIZATION_GRANT")
        self.assertEqual(result["hubs"],[{
            "id":"hub-1","longitude":ENTRY["longitude"],
            "latitude":ENTRY["latitude"],"reported":True
        }])
        raw=json.dumps(result)
        for secret in ("Sensitive", "Example City", "HEALTHCARE",
                       "organizationLabel", "serviceFamily",
                       "countryCode","regionCode","archived"):
            self.assertNotIn(secret,raw)

    def test_archived_not_emitted(self):
        doc=populated()
        archived=directory.apply(doc,{
            "action":"archive","expectedRevision":1,"hubId":"hub-1"})
        self.assertEqual(bridge.projection(archived)["hubs"],[])

    def test_no_implicit_read_or_file_creation_when_denied(self):
        with patch.object(directory,"load",side_effect=AssertionError("unexpected read")):
            with self.assertRaises(directory.HubError) as ctx:
                bridge.read_explicitly("read")
        self.assertEqual(ctx.exception.code,"EXPLICIT_OWNER_VIEW_REQUIRED")
        self.assertEqual(list(Path(self.temp.name).iterdir()),[])

    def test_root_or_mismatched_euid_denied_before_read(self):
        for uid,euid in ((0,0),(1000,0),(1000,1001)):
            with self.subTest(uid=uid,euid=euid):
                with patch.object(bridge.os,"getuid",return_value=uid),\
                     patch.object(bridge.os,"geteuid",return_value=euid),\
                     patch.object(directory,"load",
                                  side_effect=AssertionError("read on unsafe UID")):
                    with self.assertRaises(directory.HubError):
                        bridge.read_explicitly(bridge.ALLOWED_COMMAND)

    def test_owner_read_has_no_writes_or_directory_mutation(self):
        if os.geteuid()==0:
            self.skipTest("owner-only on a non-root CI identity")
        doc=populated()
        directory.save(doc)
        path=Path(self.temp.name)/"post-apollo"/"company"/"hubs-v1.json"
        original=path.read_bytes()
        original_stat=path.stat()
        with patch.object(bridge.os,"getuid",return_value=os.getuid()),\
             patch.object(bridge.os,"geteuid",return_value=os.geteuid()):
            result=bridge.read_explicitly(bridge.ALLOWED_COMMAND)
        self.assertEqual(len(result["hubs"]),1)
        self.assertEqual(path.read_bytes(),original)
        self.assertEqual(path.stat().st_mtime_ns,original_stat.st_mtime_ns)
        self.assertEqual(path.stat().st_mode & 0o777,0o600)

    def test_empty_owner_store_does_not_create_any_file(self):
        if os.geteuid()==0:
            self.skipTest("owner-only on a non-root CI identity")
        with patch.object(bridge.os,"getuid",return_value=os.getuid()),\
             patch.object(bridge.os,"geteuid",return_value=1000):
            self.assertEqual(bridge.read_explicitly(bridge.ALLOWED_COMMAND)["hubs"],[])
        self.assertEqual(list(Path(self.temp.name).iterdir()),[])

    def test_corrupt_or_unsafe_directory_fails_closed(self):
        if os.geteuid()==0:
            self.skipTest("owner-only on a non-root CI identity")
        directory.save(populated())
        path=Path(self.temp.name)/"post-apollo"/"company"/"hubs-v1.json"
        path.chmod(0o644)
        with patch.object(bridge.os,"getuid",return_value=os.getuid()),\
             patch.object(bridge.os,"geteuid",return_value=os.geteuid()):
            with self.assertRaises(directory.HubError):
                bridge.read_explicitly(bridge.ALLOWED_COMMAND)

    def test_cli_requires_exact_single_opt_in_argument(self):
        for args in ([],["read"],["--owner-local-view","--all"],
                     ["--owner-local-view","/tmp/other.json"]):
            with self.subTest(args=args),\
                 patch.object(directory,"load",
                              side_effect=AssertionError("unauthorized read")):
                output=io.StringIO()
                with contextlib.redirect_stdout(output):
                    status=bridge.main(args)
                self.assertEqual(status,2)
                self.assertEqual(json.loads(output.getvalue())["error"],
                                 "EXPLICIT_OWNER_VIEW_REQUIRED")

    def test_no_network_writer_or_arbitrary_file_path_support(self):
        code=(SRC/"CompanyHubMapReadOnly.py").read_text()
        self.assertIn("Source.load()",code)
        self.assertIn("Source.validate(doc)",code)
        self.assertIn("args != [ALLOWED_COMMAND]",code)
        for forbidden in ("Source.save(", "Source.apply(", "urlopen(",
                          "requests.", "socket.", "httpx.",
                          "sys.stdin", "QProcess", "FileView", "open(path"):
            self.assertNotIn(forbidden,code)


if __name__=="__main__":
    unittest.main()
