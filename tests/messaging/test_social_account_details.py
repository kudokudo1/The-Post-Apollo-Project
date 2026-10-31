"""Social account-details backend, privacy and identity-isolation tests.

The only runtime values used are synthetic. No provider is contacted and no
actual local Post-Apollo data directory is read/written by these tests.
"""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
BACKEND=ROOT/"services/social/SocialAccountDetails.py"
SPEC=importlib.util.spec_from_file_location("social_account_details",BACKEND)
assert SPEC is not None and SPEC.loader is not None
module=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class AccountDetailsTests(unittest.TestCase):
    def setUp(self):
        self.workspace=tempfile.TemporaryDirectory(prefix="apollo-account-tests-")
        self.addCleanup(self.workspace.cleanup)
        self.env=patch.dict(os.environ,{"XDG_DATA_HOME":self.workspace.name})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_missing_file_is_empty_until_explicit_write(self):
        root=module.root_path()
        loaded=module.load()
        self.assertEqual(loaded,module.new_document())
        self.assertFalse(root.exists())
        self.assertEqual(module.storage_path().name,"identity-account-details-v1.json")

    def test_separate_contact_defaults_and_aliases(self):
        original=module.load()
        personal=module.apply(original,{
            "action":"save_contact","identityId":"identity-1",
            "expectedRevision":0,"email":"  user@example.org  ",
            "phone":"+1 (202) 555-0133"})
        self.assertEqual(personal["revision"],1)
        self.assertEqual(personal["identities"]["identity-1"]["email"],"user@example.org")
        self.assertEqual(original["identities"],{})
        personal=module.apply(personal,{
            "action":"set_account_label","identityId":"identity-1",
            "expectedRevision":1,"serviceId":"discord","label":"My community account"})
        self.assertEqual(personal["identities"]["identity-1"]["accounts"]["discord"],
                         "My community account")
        work=module.apply(personal,{
            "action":"save_contact","identityId":"identity-2",
            "expectedRevision":2,"email":"work@example.net","phone":""})
        self.assertEqual(work["identities"]["identity-2"]["accounts"],{})
        self.assertEqual(work["identities"]["identity-1"]["email"],"user@example.org")
        self.assertEqual(work["identities"]["identity-1"]["accounts"]["discord"],
                         "My community account")
        module.save(work)
        saved=module.load()
        self.assertEqual(saved,work)
        self.assertEqual(stat.S_IMODE(module.root_path().stat().st_mode),0o700)
        self.assertEqual(stat.S_IMODE(module.storage_path().stat().st_mode),0o600)

    def test_multi_account_names_preserve_legacy_and_sort_within_identity(self):
        def update(doc, action, identity="identity-1", service="discord", **fields):
            return module.apply(doc, {
                "action": action, "identityId": identity,
                "expectedRevision": doc["revision"], "serviceId": service,
                **fields,
            })

        doc = update(module.new_document(), "set_account_label", label="Original")
        legacy = json.loads(json.dumps(doc))
        self.assertEqual(doc["identities"]["identity-1"]["accounts"]["discord"],
                         "Original")
        doc = update(doc, "add_account", label="Gaming")
        self.assertEqual(legacy["identities"]["identity-1"]["accounts"]["discord"],
                         "Original")
        entries = doc["identities"]["identity-1"]["accounts"]["discord"]
        self.assertEqual(entries, [
            {"id": "account-1", "label": "Original"},
            {"id": "account-2", "label": "Gaming"},
        ])
        doc = update(doc, "add_account", label="Community")
        doc = update(doc, "move_account", accountId="account-3", direction=-1)
        self.assertEqual([x["label"] for x in
            doc["identities"]["identity-1"]["accounts"]["discord"]],
            ["Original", "Community", "Gaming"])
        doc = update(doc, "rename_account", accountId="account-2", label="Work")
        self.assertEqual([x["label"] for x in
            doc["identities"]["identity-1"]["accounts"]["discord"]],
            ["Original", "Community", "Work"])
        doc = update(doc, "add_account", identity="identity-2", label="Private")
        self.assertEqual(
            doc["identities"]["identity-2"]["accounts"]["discord"],
            [{"id": "account-1", "label": "Private"}],
        )
        doc = update(doc, "remove_account", accountId="account-1")
        doc = update(doc, "remove_account", accountId="account-3")
        doc = update(doc, "remove_account", accountId="account-2")
        self.assertNotIn("identity-1", doc["identities"])
        self.assertIn("identity-2", doc["identities"])
        module.save(doc)
        self.assertEqual(module.load(), doc)

    def test_account_name_edits_reject_ambiguity_and_credentials(self):
        def update(doc, action, **fields):
            return module.apply(doc, {
                "action": action, "identityId": "identity-1",
                "serviceId": "discord", "expectedRevision": doc["revision"],
                **fields,
            })
        doc = module.new_document()
        doc = update(doc, "add_account", label="Personal")
        unchanged = json.loads(json.dumps(doc))
        invalid = [
            ("move_account", {"accountId": "account-1", "direction": -1},
             "NO_CHANGE"),
            ("move_account", {"accountId": "account-1", "direction": 0},
             "INVALID_DIRECTION"),
            ("rename_account", {"accountId": "account-999", "label": "Other"},
             "ACCOUNT_NOT_FOUND"),
            ("remove_account", {"accountId": "bad id"}, "INVALID_ACCOUNT"),
            ("add_account", {"label": "password\nsecret"}, "INVALID_FIELD"),
            ("add_account", {"label": ""}, "INVALID_FIELD"),
            ("add_account", {"label": "demo", "accessToken": "fake"},
             "INVALID_REQUEST"),
            ("set_account_label", {"label": "overwrite all"},
             "MULTI_ACCOUNT_MODE"),
        ]
        for action, fields, expected in invalid:
            with self.subTest(action=action, fields=fields):
                with self.assertRaises(module.StoreError) as error:
                    update(doc, action, **fields)
                self.assertEqual(error.exception.code, expected)
        self.assertEqual(doc, unchanged)
        for n in range(2, module.MAX_NAMES_PER_SERVICE + 1):
            doc = update(doc, "add_account", label=f"Alias {n}")
        with self.assertRaises(module.StoreError) as error:
            update(doc, "add_account", label="Too many")
        self.assertEqual(error.exception.code, "ACCOUNT_CAPACITY")
        self.assertEqual(len(doc["identities"]["identity-1"]["accounts"]["discord"]),
                         module.MAX_NAMES_PER_SERVICE)

    def test_multi_name_storage_rejects_untrusted_or_malformed_records(self):
        initial = module.new_document()
        bad_values = [
            [],
            [{"id": "account-1", "label": "Personal"},
             {"id": "account-1", "label": "Duplicate"}],
            [{"id": "../escape", "label": "Bad"}],
            [{"id": "account-1", "label": "OK", "token": "NO"}],
            [{"id": "account-1", "label": ""}],
        ]
        for value in bad_values:
            with self.subTest(value=value):
                doc = json.loads(json.dumps(initial))
                doc["identities"] = {
                    "identity-1": {"email": "", "phone": "",
                                   "accounts": {"discord": value}}
                }
                with self.assertRaises(module.StoreError):
                    module.validate_document(doc)
        # Legacy v1 single-label records still validate without migration.
        legacy = {
            "schema": module.SCHEMA, "revision": 1,
            "identities": {"identity-1": {"email": "", "phone": "",
                "accounts": {"discord": "My old saved name"}}},
        }
        self.assertEqual(module.validate_document(legacy), legacy)

    def test_notes_are_not_login_or_link_status(self):
        cmd={"action":"set_account_label","identityId":"identity-1",
             "expectedRevision":0,"serviceId":"telegram","label":"Personal Telegram"}
        edited=module.apply(module.new_document(),cmd)
        record=edited["identities"]["identity-1"]
        self.assertEqual(set(record),{"email","phone","accounts"})
        self.assertNotIn("authenticated",json.dumps(edited))
        self.assertNotIn("apiHash",json.dumps(edited))
        self.assertNotIn("sessionPath",json.dumps(edited))
        removed=module.apply(edited,{
            "action":"set_account_label","identityId":"identity-1",
            "expectedRevision":1,"serviceId":"telegram","label":""})
        self.assertEqual(removed["identities"],{})  # No stale empty record.

    def test_refuse_revision_conflicts_and_unknown_services(self):
        saved=module.apply(module.new_document(),{
            "action":"save_contact","identityId":"identity-1",
            "expectedRevision":0,"email":"","phone":""})
        for bad,reason in [
            ({"action":"save_contact","identityId":"identity-1",
              "expectedRevision":0,"email":"x@x.org","phone":""},"REVISION_CONFLICT"),
            ({"action":"set_account_label","identityId":"identity-1",
              "expectedRevision":1,"serviceId":"secretwebsite","label":"demo"},"INVALID_SERVICE"),
            ({"action":"save_contact","identityId":"../telegram",
              "expectedRevision":1,"email":"","phone":""},"INVALID_IDENTITY"),
            ({"action":"save_contact","identityId":"identity-1",
              "expectedRevision":1,"email":"not-an-email","phone":""},"INVALID_EMAIL"),
            ({"action":"save_contact","identityId":"identity-1",
              "expectedRevision":1,"email":"","phone":"123"},"INVALID_PHONE"),
            ({"action":"set_account_label","identityId":"identity-1",
              "expectedRevision":1,"serviceId":"discord",
              "label":"password\nentry"},"INVALID_FIELD"),
            ({"action":"set_account_label","identityId":"identity-1",
              "expectedRevision":1,"serviceId":"discord",
              "label":"ok","unexpected":"field"},"INVALID_REQUEST"),
        ]:
            with self.subTest(reason=reason):
                with self.assertRaises(module.StoreError) as ctx:
                    module.apply(saved,bad)
                self.assertEqual(ctx.exception.code,reason)
        self.assertEqual(saved["revision"],1)

    def test_corrupt_version_and_insecure_files_block_writes(self):
        root=module.root_path()
        root.mkdir(parents=True,mode=0o700)
        target=module.storage_path()
        target.write_text('{"schema":"future-version","revision":0,"identities":{}}')
        target.chmod(0o600)
        with self.assertRaises(module.StoreError) as ctx:
            module.load()
        self.assertEqual(ctx.exception.code,"UNSUPPORTED_VERSION")
        target.write_text("{garbled")
        with self.assertRaises(module.StoreError) as ctx:
            module.load()
        self.assertEqual(ctx.exception.code,"INVALID_JSON")
        target.write_text(json.dumps(module.new_document()))
        target.chmod(0o644)
        with self.assertRaises(module.StoreError) as ctx:
            module.load()
        self.assertEqual(ctx.exception.code,"UNSAFE_FILE")
        with self.assertRaises(module.StoreError) as ctx:
            module.save(module.new_document())
        self.assertEqual(ctx.exception.code,"UNSAFE_FILE")
        target.unlink()
        target.symlink_to(Path(self.workspace.name)/"outside.json")
        with self.assertRaises(module.StoreError) as ctx:
            module.load()
        self.assertEqual(ctx.exception.code,"UNSAFE_FILE")

    def test_insecure_directory_blocks_before_file_write(self):
        root=module.root_path()
        root.mkdir(parents=True,mode=0o700)
        root.chmod(0o755)
        with self.assertRaises(module.StoreError) as ctx:
            module.save(module.new_document())
        self.assertEqual(ctx.exception.code,"UNSAFE_DIRECTORY")
        self.assertFalse(module.storage_path().exists())

    def test_cli_stdin_transaction_and_redacted_errors(self):
        env={**os.environ,"XDG_DATA_HOME":self.workspace.name}
        def invoke(action,payload=None):
            return subprocess.run(
                [sys.executable,str(BACKEND),action],
                input=None if payload is None else json.dumps(payload)+"\n",
                capture_output=True,text=True,env=env,check=False)
        read=invoke("read")
        self.assertEqual(read.returncode,0)
        self.assertEqual(json.loads(read.stdout)["document"]["revision"],0)
        request={"action":"save_contact","identityId":"identity-1",
                 "expectedRevision":0,"email":"me@example.org",
                 "phone":"+12025550133"}
        write=invoke("update",request)
        self.assertEqual(write.returncode,0)
        self.assertEqual(json.loads(write.stdout)["document"]["revision"],1)
        self.assertEqual(module.load()["identities"]["identity-1"]["email"],
                         "me@example.org")
        failed=invoke("update",request)
        self.assertNotEqual(failed.returncode,0)
        self.assertEqual(json.loads(failed.stdout)["error"],"REVISION_CONFLICT")
        self.assertNotIn("me@example.org",failed.stdout+failed.stderr)
        self.assertNotIn("Traceback",failed.stderr)
        self.assertEqual(module.load()["revision"],1)
        self.assertEqual(stat.S_IMODE(module.storage_path().stat().st_mode),0o600)

    def test_simultaneous_updates_are_serialized(self):
        from concurrent.futures import ThreadPoolExecutor

        payloads = [
            {"action":"save_contact","identityId":"identity-1",
             "expectedRevision":0,"email":"first@example.org","phone":""},
            {"action":"save_contact","identityId":"identity-2",
             "expectedRevision":0,"email":"second@example.org","phone":""},
        ]
        def one(payload):
            return subprocess.run(
                [sys.executable, str(BACKEND), "update"],
                input=json.dumps(payload)+"\n",
                capture_output=True, text=True, env=dict(os.environ),
                check=False)
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(one, payloads))
        successes = [r for r in results if r.returncode == 0]
        failures = [r for r in results if r.returncode != 0]
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        self.assertEqual(json.loads(failures[0].stdout)["error"],"REVISION_CONFLICT")
        saved = module.load()
        self.assertEqual(saved["revision"],1)
        self.assertEqual(len(saved["identities"]),1)
        self.assertEqual(stat.S_IMODE(
            (module.root_path()/".account-details.lock").stat().st_mode), 0o600)

    def test_file_capacity_and_whitelist(self):
        initial=module.new_document()
        initial["token"]="private"
        with self.assertRaises(module.StoreError) as ctx:
            module.validate_document(initial)
        self.assertEqual(ctx.exception.code,"INVALID_DOCUMENT")
        oversized="x"*65_537
        root=module.root_path()
        root.mkdir(parents=True,mode=0o700)
        module.storage_path().write_text(oversized)
        module.storage_path().chmod(0o600)
        with self.assertRaises(module.StoreError) as ctx:
            module.load()
        self.assertEqual(ctx.exception.code,"FILE_TOO_LARGE")


if __name__=="__main__":
    unittest.main()
