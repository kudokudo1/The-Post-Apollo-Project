"""P41a // Synthetic P35 in-lock final check and P36 revocation regression.

No production authority, keyring calls, provider IPC or real Personal data.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import os
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
import PhonePersonalHostGateP36 as Gate

PROFILE = "123e4567-e89b-42d3-a456-426614174000"
KEY = b"k" * 32
CARD = {
    "id": "transient-row-1",
    "serviceId": "blueferry",
    "deviceProfileId": PROFILE,
    "displayNameInProfile": "Fictional Example",
    "hasAddressDetails": True,
    "phoneNumbers": ["+15550001001"],
    "emailAddresses": ["example@invalid.test"],
    "phoneCount": 1,
    "emailCount": 1,
}


def linked_and_pending():
    result = Identity.link(
        Identity.empty_document(), CARD, [CARD], PROFILE,
        Vault.contact_matching_key(KEY),
        user_confirmed=True, create_id=lambda: uuid.UUID(int=7),
    )
    if result.get("ok") is not True:
        raise AssertionError("Synthetic fixture setup failed")
    edit = Identity.edit(
        result["document"], result["localId"], 1,
        note="FICTIONAL PRIVATE NOTE", favorite=True,
        user_confirmed=True,
    )
    if edit.get("ok") is not True:
        raise AssertionError("Synthetic fixture edit failed")
    return result["document"], edit["document"]


class UnderLockTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix="p41a-fixture-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / Vault.ROOT_NAME
        self.before, self.pending = linked_and_pending()
        Vault.commit(KEY, PROFILE, self.root, self.before,
                     expected_revision=0)

    def sealed(self):
        return (self.root / Vault._filename(KEY, PROFILE)).read_bytes()

    def test_predicate_runs_under_actual_file_lock(self):
        calls = []

        def verify_lock():
            lockfd = os.open(self.root / Vault.LOCK_NAME, os.O_RDWR)
            try:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                calls.append("locked")
            finally:
                os.close(lockfd)
            return True

        saved = Vault.commit(
            KEY, PROFILE, self.root, self.pending, expected_revision=1,
            pre_publish_check=verify_lock,
        )
        self.assertEqual(calls, ["locked"])
        self.assertEqual(saved["revision"], 2)
        self.assertEqual(Vault.read(KEY, PROFILE, self.root), self.pending)

    def test_denied_non_boolean_and_crashing_checks_do_not_publish(self):
        original = self.sealed()

        def explode():
            raise RuntimeError("PRIVATE SYNTHETIC ERROR DETAILS")

        for check in (
            lambda: False, lambda: None, lambda: 1,
            lambda: "true", explode,
        ):
            with self.subTest(check=repr(check)):
                with self.assertRaisesRegex(
                    Vault.VaultRefused, "^PERSONAL_CONTACT_VAULT_REFUSED$"
                ):
                    Vault.commit(
                        KEY, PROFILE, self.root, self.pending,
                        expected_revision=1, pre_publish_check=check,
                    )
                self.assertEqual(self.sealed(), original)
                self.assertEqual(
                    Vault.read(KEY, PROFILE, self.root), self.before
                )
        with self.assertRaises(Vault.VaultRefused):
            Vault.commit(
                KEY, PROFILE, self.root, self.pending,
                expected_revision=1, pre_publish_check="fake-token",
            )
        self.assertEqual(self.sealed(), original)

    def test_stale_revision_never_invokes_check(self):
        called = []
        Vault.commit(KEY, PROFILE, self.root, self.pending, expected_revision=1)
        ciphertext = self.sealed()
        with self.assertRaises(Vault.VaultRefused):
            Vault.commit(
                KEY, PROFILE, self.root, self.pending,
                expected_revision=1,
                pre_publish_check=lambda: called.append(1) or True,
            )
        self.assertEqual(called, [])
        self.assertEqual(self.sealed(), ciphertext)

    def test_p36_revoke_after_preparation_but_before_locked_publish(self):
        state = {"allow": True, "checks": 0}

        def observe():
            return Gate.ObservedFixture(
                profile=PROFILE, provider_owner=":1.123",
                session="synthetic-session-123", snapshot_epoch=1,
                expires_at=150, personal_scope=True,
                contacts_approved=True, device_connected=True,
                cards=(CARD,),
            )

        def gesture(_intent, _state):
            state["checks"] += 1
            return state["allow"]

        coordinator = Gate.FixtureCoordinator(
            observe=observe, verify_gesture=gesture,
            key_lookup=lambda: KEY, clock=lambda: 100,
            root=self.root,
        )
        # Inject revocation ONLY once P35 has obtained its file lock.
        # Without the new hook, the old P36 pre-commit check would pass.
        existing_lock = Vault._write_lock

        @contextmanager
        def revoke_under_lock(dfd):
            with existing_lock(dfd):
                state["allow"] = False
                yield

        original = self.sealed()
        intent = Gate.ActionFixture(
            action="FAVORITE", selected_row=CARD["id"],
            expected_revision=1, nonce="b" * 32, favorite=True,
        )
        with patch.object(Vault, "_write_lock", new=revoke_under_lock):
            with self.assertRaisesRegex(
                Gate.FixtureRefused, "^P36_UNAUTHORIZED_OR_UNAVAILABLE$"
            ):
                coordinator.apply(intent)
        self.assertFalse(state["allow"])
        self.assertGreaterEqual(state["checks"], 3)
        self.assertEqual(self.sealed(), original)
        self.assertEqual(Vault.read(KEY, PROFILE, self.root), self.before)

    def test_synthetic_checker_does_not_create_a_public_host(self):
        for mod in (Vault, Gate):
            self.assertFalse(hasattr(mod, "main"))
        # A passing predicate does not establish an installed trusted host.
        self.assertFalse("productionEnabled" in Vault.commit.__annotations__)


if __name__ == "__main__":
    unittest.main()
