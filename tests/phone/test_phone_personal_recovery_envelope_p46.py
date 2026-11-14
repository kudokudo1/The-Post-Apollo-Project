"""P46 in-memory AES-GCM recovery envelope + disposable P35 vault readback."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
import PhonePersonalRecoveryEnvelopeP46 as Recovery
import PhonePersonalContactVault as Vault
import PhonePersonalContactIdentity as Identity

MASTER = bytes(range(1, 33))
RECOVERY_KEY = bytes(range(35, 67))
PROFILE = "123e4567-e89b-42d3-a456-426614174000"


class EnvelopeTests(unittest.TestCase):
    def sealed(self, **overrides):
        values = iter((b"a" * 16, b"b" * 12))
        options = dict(
            master_key=MASTER, recovery_key=RECOVERY_KEY,
            profile=PROFILE, epoch=7, random_bytes=lambda n: next(values)
        )
        options.update(overrides)
        return Recovery.seal_master_for_recovery(**options)

    def test_recovery_with_separate_32_byte_key_and_new_epoch(self):
        blob = self.sealed()
        self.assertEqual(Recovery.unseal_master_for_recovery(
            envelope=blob, recovery_key=RECOVERY_KEY,
            profile=PROFILE, minimum_epoch=7), MASTER)
        self.assertNotIn(MASTER, blob)
        self.assertNotIn(RECOVERY_KEY, blob)
        self.assertNotIn(PROFILE.encode(), blob)
        doc = json.loads(blob)
        self.assertEqual(set(doc), Recovery.FIELDS)
        self.assertEqual(doc["schema"], Recovery.SCHEMA)
        self.assertEqual(doc["algorithm"], "AES-256-GCM")
        self.assertEqual(doc["epoch"], 7)

    def test_wrong_recovery_key_profile_epoch_or_tamper_refuses(self):
        raw = self.sealed()
        cases = (
            dict(recovery_key=b"x" * 32),
            dict(profile="223e4567-e89b-42d3-a456-426614174000"),
            dict(minimum_epoch=8),
            dict(minimum_epoch=0),
            dict(minimum_epoch=True),
        )
        for change in cases:
            args = dict(envelope=raw, recovery_key=RECOVERY_KEY,
                        profile=PROFILE, minimum_epoch=7)
            args.update(change)
            with self.subTest(change=list(change)):
                with self.assertRaisesRegex(
                    Recovery.RecoveryRefused,
                    "^PHONE_RECOVERY_ENVELOPE_REFUSED$"
                ):
                    Recovery.unseal_master_for_recovery(**args)
        parsed=json.loads(raw)
        mutations = (
            {**parsed, "sealed": "A" + parsed["sealed"][1:]},
            {**parsed, "nonce": "A" + parsed["nonce"][1:]},
            {**parsed, "salt": "A" + parsed["salt"][1:]},
            {**parsed, "epoch": 8},
            {**parsed, "schema": "P45"},
            {**parsed, "algorithm": "AES-128-GCM"},
            {**parsed, "authority": True},
        )
        for item in mutations:
            with self.subTest(fields=list(item)):
                mutated=json.dumps(item,sort_keys=True,
                                   separators=(",",":")).encode("ascii")
                with self.assertRaises(Recovery.RecoveryRefused):
                    Recovery.unseal_master_for_recovery(
                        envelope=mutated,recovery_key=RECOVERY_KEY,
                        profile=PROFILE,minimum_epoch=7)
        duplicate=raw[:-1] + b',"epoch":7}'
        with self.assertRaises(Recovery.RecoveryRefused):
            Recovery.unseal_master_for_recovery(
                envelope=duplicate,recovery_key=RECOVERY_KEY,
                profile=PROFILE,minimum_epoch=7)

    def test_cannot_use_master_as_own_recovery_secret(self):
        for change in (
            dict(master_key=RECOVERY_KEY),
            dict(master_key=bytes(32)),
            dict(recovery_key=b"short"),
            dict(profile=""),
            dict(epoch=0),
            dict(epoch=True),
            dict(random_bytes=lambda n: bytes(n)),
            dict(random_bytes=lambda n: "wrong"),
        ):
            with self.subTest(change=list(change)):
                with self.assertRaisesRegex(
                    Recovery.RecoveryRefused,
                    "^PHONE_RECOVERY_ENVELOPE_REFUSED$"
                ):
                    self.sealed(**change)

    def test_envelope_only_does_not_create_store_or_restore_host_authority(self):
        path=(ROOT / "services/phone/PhonePersonalRecoveryEnvelopeP46.py")
        src=path.read_text()
        for text in (
            "def main(", "if __name__ ==", "subprocess",
            "secret-tool", "import dbus", "Vault.commit(",
            "open(", "os.environ", "print(", "QtQuick",
        ):
            self.assertNotIn(text,src)
        self.assertNotIn(b"PRIVATE NOTE",self.sealed())

    def test_offline_restore_key_decrypts_existing_AES_GCM_vault_no_host_IO(self):
        blob=self.sealed()
        doc={
            "schema": Identity.SCHEMA, "version": Identity.VERSION,
            "revision": 1,
            "entries": [{
                "localId": "ab" * 16, "profileId": PROFILE,
                "matchProof": "a" * 64, "favorite": True,
                "note": "FICTIONAL PRIVATE NOTE TO ENCRYPT"
            }],
        }
        self.assertTrue(Identity.valid_document(doc))
        with TemporaryDirectory(prefix="p46-recovery-fixture-") as path:
            root=Path(path)/Vault.ROOT_NAME
            Vault.commit(MASTER,PROFILE,root,doc,expected_revision=0)
            recovered=Recovery.unseal_master_for_recovery(
                envelope=blob,recovery_key=RECOVERY_KEY,
                profile=PROFILE,minimum_epoch=7)
            read=Vault.read(recovered,PROFILE,root)
            self.assertEqual(read,doc)
            sealed_file=(root/Vault._filename(MASTER,PROFILE)).read_bytes()
            self.assertNotIn(b"FICTIONAL PRIVATE NOTE",sealed_file)
            self.assertNotIn(MASTER,sealed_file)


if __name__=="__main__":
    unittest.main()
