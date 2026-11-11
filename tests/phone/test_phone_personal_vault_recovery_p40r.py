"""P40R: synthetic observation after uncertain encrypted Personal writes.

No real contacts, keyring, Quickshell, phone, HOME state or provider IPC.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import sys
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))

import PhonePersonalContactIdentity as Identity
import PhonePersonalContactVault as Vault
import PhonePersonalVaultRecoveryP40R as Recovery

PROFILE = "123e4567-e89b-42d3-a456-426614174000"
OTHER_PROFILE = "223e4567-e89b-42d3-a456-426614174000"
KEY = b"p" * 32


def sample_card():
    return {
        "id": "temporary-legacy-row-9",
        "serviceId": "blueferry",
        "deviceProfileId": PROFILE,
        "displayNameInProfile": "Synthetic Person",
        "hasAddressDetails": True,
        "phoneNumbers": ["+15550001001"],
        "emailAddresses": ["synthetic@example.invalid"],
        "phoneCount": 1,
        "emailCount": 1,
    }


def revisions():
    card = sample_card()
    linked = Identity.link(
        Identity.empty_document(), card, [card], PROFILE,
        Vault.contact_matching_key(KEY), user_confirmed=True,
        create_id=lambda: uuid.UUID(int=2),
    )
    assert linked["ok"] is True
    updated = Identity.edit(
        linked["document"], linked["localId"], 1,
        note="PRIVATE SYNTHETIC NOTE", favorite=True, user_confirmed=True,
    )
    assert updated["ok"] is True
    return linked["document"], updated["document"]


class PostWriteObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="p40r-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / Vault.ROOT_NAME
        self.first, self.pending = revisions()

    def inspect(self, **overrides):
        params = {
            "master_key": KEY, "profile": PROFILE, "root": self.root,
            "pending_document": self.pending, "expected_revision": 1,
        }
        params.update(overrides)
        return Recovery.inspect_after_uncertain_save(**params)

    def assert_denied_capabilities(self, response):
        self.assertEqual(response["schema"], Recovery.SCHEMA)
        for name in ("productionEnabled", "writeAuthorized",
                     "retryAuthorized", "durableCommitProven"):
            self.assertIs(response[name], False)
        for secret in ("Synthetic Person", "PRIVATE SYNTHETIC NOTE",
                       "synthetic@example.invalid", PROFILE):
            self.assertNotIn(secret, str(response))

    def first_save(self):
        Vault.commit(KEY, PROFILE, self.root, self.first, expected_revision=0)

    def test_no_file_is_created_for_absent_vault(self):
        self.assertFalse(self.root.exists())
        result = self.inspect()
        self.assertEqual(result["status"], Recovery.OTHER["status"])
        self.assertFalse(self.root.exists())
        self.assert_denied_capabilities(result)

    def test_prior_revision_is_observation_not_retry_permission(self):
        self.first_save()
        before = (self.root / Vault._filename(KEY, PROFILE)).read_bytes()
        result = self.inspect()
        self.assertEqual(result["status"], Recovery.PRIOR["status"])
        self.assert_denied_capabilities(result)
        self.assertEqual((self.root / Vault._filename(KEY, PROFILE)).read_bytes(), before)

    def test_full_match_is_not_proof_of_fsync_or_durable_receipt(self):
        self.first_save()
        Vault.commit(KEY, PROFILE, self.root, self.pending, expected_revision=1)
        before = (self.root / Vault._filename(KEY, PROFILE)).read_bytes()
        result = self.inspect()
        self.assertEqual(result["status"], Recovery.MATCH["status"])
        self.assert_denied_capabilities(result)
        self.assertEqual((self.root / Vault._filename(KEY, PROFILE)).read_bytes(), before)

    def test_directory_fsync_failure_after_rename_is_detected_without_retry(self):
        self.first_save()
        original_fsync = Vault.os.fsync
        calls = [0]

        def fail_directory_sync(fd):
            calls[0] += 1
            if calls[0] == 2:
                raise OSError("injected directory sync failure")
            return original_fsync(fd)

        with patch.object(Vault.os, "fsync", side_effect=fail_directory_sync):
            with self.assertRaises(Vault.VaultRefused):
                Vault.commit(KEY, PROFILE, self.root, self.pending,
                             expected_revision=1)
        # The atomic rename completed, but the commit response was uncertain.
        self.assertEqual(self.inspect()["status"], Recovery.MATCH["status"])
        self.assert_denied_capabilities(self.inspect())

    def test_rename_failure_leaves_prior_sealed_content(self):
        self.first_save()
        with patch.object(Vault.os, "replace", side_effect=OSError("injected")):
            with self.assertRaises(Vault.VaultRefused):
                Vault.commit(KEY, PROFILE, self.root, self.pending,
                             expected_revision=1)
        self.assertEqual(self.inspect()["status"], Recovery.PRIOR["status"])

    def test_same_revision_different_document_is_unresolved(self):
        self.first_save()
        altered = deepcopy(self.pending)
        altered["entries"][0]["note"] = "ANOTHER SYNTHETIC NOTE"
        Vault.commit(KEY, PROFILE, self.root, altered, expected_revision=1)
        response = self.inspect()
        self.assertEqual(response["status"], Recovery.OTHER["status"])
        self.assert_denied_capabilities(response)

    def test_wrong_key_profile_invalid_shapes_and_corruption_fail_closed(self):
        self.first_save()
        bad = [
            {"master_key": b"wrong" * 6 + b"ab"},
            {"profile": OTHER_PROFILE},
            {"expected_revision": True},
            {"expected_revision": -1},
            {"pending_document": {"revision": 2}},
            {"root": Path(self.temp.name)},
            {"root": "untrusted string"},
        ]
        for change in bad:
            with self.subTest(change=list(change)):
                result = self.inspect(**change)
                self.assertEqual(result, Recovery.REFUSED)
                self.assert_denied_capabilities(result)
        file = self.root / Vault._filename(KEY, PROFILE)
        file.write_bytes(b"damaged sealed content")
        result = self.inspect()
        self.assertEqual(result, Recovery.REFUSED)
        self.assert_denied_capabilities(result)

    def test_reads_do_not_call_commit_erase_or_create_files(self):
        self.first_save()
        before_names = sorted(p.name for p in self.root.iterdir())
        with patch.object(Vault, "commit", side_effect=AssertionError("write")):
            with patch.object(Vault, "erase", side_effect=AssertionError("erase")):
                response = self.inspect()
        self.assertEqual(response["status"], Recovery.PRIOR["status"])
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), before_names)


if __name__ == "__main__":
    unittest.main()
