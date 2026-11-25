#!/usr/bin/env python3
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/cpuplus_profile_catalog.py"
spec = importlib.util.spec_from_file_location("catalog", SCRIPT)
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name) / "profiles"

    def call(self, action, **fields):
        return catalog.execute(self.folder, {"action": action, **fields})

    def create(self, revision=0, name="Work"):
        return self.call("create", expectedRevision=revision, name=name,
                         targets={"capacityGiB": 24, "swappiness": None})

    def test_roundtrip(self):
        self.assertEqual(self.call("list"), catalog.initial())
        self.assertFalse(self.folder.exists())
        self.assertEqual(self.create()["revision"], 1)
        self.assertEqual(self.call("list")["profiles"][0]["name"], "Work")
        edit = self.call("edit", expectedRevision=1, name="Work",
                         targets={"capacityGiB": None, "swappiness": 60})
        self.assertEqual(edit["profiles"][0]["targets"]["swappiness"], 60)
        renamed = self.call("rename", expectedRevision=2, name="Work", newName="Office")
        self.assertEqual(renamed["profiles"][0]["name"], "Office")
        self.assertEqual(self.call("delete", expectedRevision=3, name="Office")["profiles"], [])
        self.assertEqual(self.call("list")["revision"], 4)

    def test_stale_collision_and_reserved(self):
        before = self.create()
        for request in [
            {"action":"create","expectedRevision":0,"name":"Other","targets":{"capacityGiB":4,"swappiness":None}},
            {"action":"create","expectedRevision":1,"name":"work","targets":{"capacityGiB":4,"swappiness":None}},
            {"action":"create","expectedRevision":1,"name":"GAMING","targets":{"capacityGiB":4,"swappiness":None}},
            {"action":"delete","expectedRevision":1,"name":"work"},
            {"action":"apply","expectedRevision":1,"name":"Work"},
        ]:
            with self.assertRaises(ValueError):
                catalog.execute(self.folder, request)
            self.assertEqual(self.call("list"), before)

    def test_invalid_values_and_unknown_fields(self):
        for target in [
            {"capacityGiB":17,"swappiness":None},
            {"capacityGiB":True,"swappiness":None},
            {"capacityGiB":None,"swappiness":201},
            {"capacityGiB":None,"swappiness":None},
            {"capacityGiB":16,"swappiness":60,"automation":True},
        ]:
            with self.assertRaises(ValueError):
                self.call("create", expectedRevision=0, name="Work", targets=target)
        self.assertFalse(self.folder.exists())

    def test_corrupt_not_overwritten(self):
        self.create()
        file = self.folder / "profiles.json"
        file.write_text('{"schema":"future","revision":1,"profiles":[]}')
        original = file.read_bytes()
        with self.assertRaises(ValueError):
            self.create(1, "Other")
        self.assertEqual(file.read_bytes(), original)

    def test_unsafe_file_and_stage(self):
        self.create()
        path = self.folder / "profiles.json"
        path.chmod(0o644)
        with self.assertRaises(ValueError):
            self.call("list")
        path.chmod(0o600)
        stage = self.folder / ".pending"
        stage.symlink_to(path)
        original = path.read_bytes()
        with self.assertRaises(OSError):
            self.create(1, "Other")
        self.assertEqual(path.read_bytes(), original)

    def test_duplicate_json(self):
        with self.assertRaises(ValueError):
            catalog.parse('{"action":"list","action":"delete"}')

    def test_bound(self):
        for i in range(catalog.LIMIT):
            self.create(i, "Profile "+str(i))
        with self.assertRaises(ValueError):
            self.create(catalog.LIMIT, "Overflow")
        self.assertEqual(len(self.call("list")["profiles"]), catalog.LIMIT)

    def test_process_restart(self):
        env = dict(os.environ, XDG_STATE_HOME=self.tmp.name)
        def run(request):
            result = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT)],
                input=json.dumps(request)+"\n", text=True, capture_output=True, env=env, check=True)
            return json.loads(result.stdout)
        created = run({"action":"create","expectedRevision":0,"name":"Local test",
                       "targets":{"capacityGiB":16,"swappiness":10}})
        self.assertEqual(run({"action":"list"}), created)
        self.assertEqual((Path(self.tmp.name)/"post-apollo-cpuplus-profiles"/"profiles.json").stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    os.umask(0o077)
    unittest.main()
