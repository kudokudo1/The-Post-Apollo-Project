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

    def v2(self, action, **fields):
        return self.call(action, schema=catalog.SCHEMA_V2, **fields)

    def extended(self):
        return {"capacityGiB": None, "swappiness": None,
                "zram": {"deviceHint": "/dev/zram0", "sizeKiB": 8388608, "algorithm": "zstd"},
                "priority": {"deviceHint": "/var/swap/base", "sizeKiB": 16777216, "value": 20},
                "advanced": {"cachePressure": 100, "background": {"unit": "%", "value": 10},
                             "writer": {"unit": "B", "value": 1048576},
                             "writebackCentisecs": 500, "expireCentisecs": None}}

    def test_v2_read_projection_and_explicit_migration(self):
        before = self.create()
        path = self.folder / "profiles.json"
        raw = path.read_bytes()
        view = self.v2("list")
        self.assertEqual(view["schema"], catalog.SCHEMA_V2)
        self.assertEqual(view["revision"], before["revision"])
        self.assertEqual(view["profiles"][0]["targets"], {
            "capacityGiB": 24, "swappiness": None, "zram": None, "priority": None, "advanced": None})
        self.assertEqual(path.read_bytes(), raw)
        after = self.v2("create", expectedRevision=1, name="Extended", targets=self.extended())
        self.assertEqual(after["revision"], 2)
        self.assertEqual(after["profiles"][1]["targets"], self.extended())
        self.assertEqual(self.v2("list"), after)
        with self.assertRaises(ValueError):
            self.call("list")
        with self.assertRaises(ValueError):
            self.call("delete", expectedRevision=2, name="Extended")
        self.assertEqual(self.v2("list"), after)

    def test_v2_empty_list_no_file(self):
        self.assertEqual(self.v2("list"), {"schema":catalog.SCHEMA_V2,"revision":0,"profiles":[]})
        self.assertFalse(self.folder.exists())

    def test_v2_invalid_fields_refused(self):
        for key, value in [
            ("zram", {"deviceHint":"/dev/sda","sizeKiB":1,"algorithm":"zstd"}),
            ("zram", {"deviceHint":"/dev/zram0","sizeKiB":1,"algorithm":"bad algo"}),
            ("priority", {"deviceHint":"/var/../swap","sizeKiB":1,"value":20}),
            ("priority", {"deviceHint":"/dev/zram0","sizeKiB":1,"value":-1}),
            ("advanced", {**self.extended()["advanced"],"background":{"unit":"B","value":0}}),
            ("advanced", {**self.extended()["advanced"],"writer":{"unit":"%","value":101}}),
            ("advanced", {**self.extended()["advanced"],"automation":True}),
        ]:
            with self.assertRaises(ValueError):
                self.v2("create", expectedRevision=0, name="Work", targets={**self.extended(),key:value})
            self.assertFalse(self.folder.exists())

    def test_v2_crud_stale_and_preserve(self):
        first = self.v2("create", expectedRevision=0, name="Work", targets=self.extended())
        with self.assertRaises(ValueError):
            self.v2("edit", expectedRevision=0, name="Work", targets=self.extended())
        renamed = self.v2("rename", expectedRevision=1, name="Work", newName="Office")
        self.assertEqual(renamed["profiles"][0]["targets"], first["profiles"][0]["targets"])
        changed = {**self.extended(),"priority":None}
        edited = self.v2("edit", expectedRevision=2, name="Office", targets=changed)
        self.assertEqual(edited["profiles"][0]["targets"], changed)
        self.assertEqual(self.v2("delete",expectedRevision=3,name="Office")["profiles"], [])
        self.assertEqual(self.v2("list")["revision"],4)

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
