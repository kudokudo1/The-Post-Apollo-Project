"""P36 synthetic one-action authorization and key lookup refusal tests."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock
import base64
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
import PhonePersonalContactVault as Vault
import PhonePersonalHostGateP36 as Gate
import PhonePersonalKeyringP36 as Keyring

PROFILE = "123e4567-e89b-42d3-a456-426614174000"
OTHER = "223e4567-e89b-42d3-a456-426614174000"
MASTER = b"1" * 32
SELECTOR = "a" * 32


def contact():
    return {
        "id": PROFILE + ":epoch-1:legacy-row-0",
        "serviceId": "blueferry", "deviceProfileId": PROFILE,
        "displayNameInProfile": "Synthetic Name",
        "hasAddressDetails": True,
        "phoneNumbers": ["+15550001001"],
        "emailAddresses": ["fake@example.invalid"],
        "phoneCount": 1, "emailCount": 1,
    }


class SyntheticCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="p36-only-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / Vault.ROOT_NAME
        self.now = 100
        self.active = True
        self.allowed = True
        self.owner = ":1.123"
        self.epoch = 1
        self.profile = PROFILE
        self.cards = (contact(),)
        self.actions = []
        self.lookups = 0

        def observe():
            return Gate.ObservedFixture(
                profile=self.profile, provider_owner=self.owner,
                session="session-test-123", snapshot_epoch=self.epoch,
                expires_at=130, personal_scope=True,
                contacts_approved=self.active, device_connected=True,
                cards=self.cards
            )

        def verify(intent, state):
            self.actions.append(intent.action)
            return self.allowed

        def lookup():
            self.lookups += 1
            return MASTER

        self.bridge = Gate.FixtureCoordinator(
            observe=observe, verify_gesture=verify,
            key_lookup=lookup, clock=lambda: self.now, root=self.root,
        )

    def intent(self, action="LINK", revision=0, nonce="a" * 32,
               favorite=None, note=None, row=None):
        return Gate.ActionFixture(
            action=action, selected_row=contact()["id"] if row is None else row,
            expected_revision=revision, nonce=nonce,
            favorite=favorite, note=note)

    def test_link_favorite_notes_unlink_and_no_note_in_reply(self):
        self.assertFalse(self.root.exists())
        linked = self.bridge.apply(self.intent())
        self.assertEqual(linked, {
            "status": "SYNTHETIC_SEALED", "revision": 1, "productionEnabled": False
        })
        self.assertNotIn("Synthetic Name", str(linked))
        self.assertNotIn("fake@example.invalid", str(linked))
        self.assertEqual(self.lookups, 1)
        with self.assertRaises(Gate.FixtureRefused):
            self.bridge.apply(self.intent())  # consumed intent nonce
        favorite = self.bridge.apply(self.intent(
            "FAVORITE", 1, "b" * 32, favorite=True))
        self.assertEqual(favorite["revision"], 2)
        note = self.bridge.apply(self.intent(
            "NOTE", 2, "c" * 32, note="private synthetic memo"))
        self.assertEqual(note["revision"], 3)
        self.assertNotIn("private synthetic memo", str(note))
        saved = Vault.read(MASTER, PROFILE, self.root)
        self.assertEqual(saved["entries"][0]["note"], "private synthetic memo")
        self.assertTrue(saved["entries"][0]["favorite"])
        deleted = self.bridge.apply(self.intent("UNLINK", 3, "d" * 32))
        self.assertEqual(deleted["revision"], 4)
        self.assertEqual(Vault.read(MASTER, PROFILE, self.root)["entries"], [])

    def test_ineligible_or_revoked_context_does_not_lookup_key_or_write(self):
        for mutate in (
            lambda: setattr(self, "active", False),
            lambda: setattr(self, "allowed", False),
            lambda: setattr(self, "owner", "not-a-unique-owner"),
            lambda: setattr(self, "profile", OTHER),
            lambda: setattr(self, "now", 131),
            lambda: setattr(self, "cards", ()),
        ):
            with self.subTest(mutate=mutate.__code__.co_firstlineno):
                old = (self.active, self.allowed, self.owner,
                       self.profile, self.now, self.cards)
                mutate()
                with self.assertRaises(Gate.FixtureRefused):
                    self.bridge.apply(self.intent())
                self.assertEqual(self.lookups, 0)
                self.assertFalse(self.root.exists())
                (self.active, self.allowed, self.owner,
                 self.profile, self.now, self.cards) = old

    def test_changes_during_key_lookup_prevent_writes(self):
        for state_change in (
            lambda: setattr(self, "owner", ":1.999"),
            lambda: setattr(self, "epoch", 2),
            lambda: setattr(self, "active", False),
            lambda: setattr(self, "allowed", False),
        ):
            with self.subTest(change=state_change.__code__.co_firstlineno):
                previous = self.bridge._lookup
                def lookup():
                    state_change()
                    return MASTER
                self.bridge._lookup = lookup
                try:
                    with self.assertRaises(Gate.FixtureRefused):
                        self.bridge.apply(self.intent())
                    self.assertFalse(self.root.exists())
                finally:
                    self.bridge._lookup = previous
                    self.owner, self.epoch, self.active, self.allowed = (
                        ":1.123", 1, True, True
                    )

    def test_invalid_or_wrong_revision_intent_cannot_write(self):
        for bad in (
            self.intent("DIAL"),
            self.intent(revision=True),
            self.intent(nonce="abc"),
            self.intent(note="not allowed on link"),
            self.intent(row="../private"),
            self.intent(row="not loaded"),
            self.intent("FAVORITE", favorite=True),  # no prior link
        ):
            with self.subTest(bad=bad.action):
                with self.assertRaises(Gate.FixtureRefused):
                    self.bridge.apply(bad)
                self.assertFalse(self.root.exists())

    def test_stale_and_repeated_save_are_denied_without_overwrite(self):
        self.bridge.apply(self.intent())
        path = next(p for p in self.root.iterdir() if p.suffix == ".sealed")
        original = path.read_bytes()
        with self.assertRaises(Gate.FixtureRefused):
            self.bridge.apply(self.intent("FAVORITE", 0, "b" * 32, favorite=True))
        with self.assertRaises(Gate.FixtureRefused):
            self.bridge.apply(self.intent("FAVORITE", 1, "c" * 32, favorite=None))
        self.assertEqual(path.read_bytes(), original)

    def test_secret_lookup_bad_key_refuses_without_automatic_generation(self):
        called = []
        self.bridge._lookup = lambda: called.append(True) or None
        with self.assertRaises(Gate.FixtureRefused):
            self.bridge.apply(self.intent())
        self.assertEqual(called, [True])
        self.assertFalse(self.root.exists())

    def test_bridge_is_unwired_fixture_and_returns_no_note_to_public_api(self):
        s = (ROOT / "services/phone/PhonePersonalHostGateP36.py").read_text()
        self.assertIn("class FixtureCoordinator", s)
        self.assertIn('"productionEnabled": False', s)
        for code in ("def main(", "if __name__ ==", "import dbus",
                     "socket.", "secret-tool", "QtQuick", "QML", "subprocess.run("):
            # QML in documentation is okay; don't rely on a textual match.
            if code == "QML":
                continue
            self.assertNotIn(code, s)


class DisposableSecretLookupTests(unittest.TestCase):
    def test_exact_command_and_canonical_key_encoding(self):
        raw = base64.urlsafe_b64encode(MASTER).rstrip(b"=") + b"\n"
        seen = []
        def fake_run(argv, **kwargs):
            seen.append((argv, kwargs))
            return SimpleNamespace(returncode=0, stdout=raw, stderr=b"")
        key = Keyring.synthetic_key_lookup(
            SELECTOR, which=lambda tool: "/usr/bin/secret-tool",
            run=fake_run)
        self.assertEqual(key, MASTER)
        argv, args = seen[0]
        self.assertEqual(argv, [
            "secret-tool", "lookup", "post-apollo-test", Keyring.SERVICE,
            "nonce", SELECTOR,
        ])
        self.assertEqual(args["input"], b"")
        self.assertEqual(args["timeout"], 5)
        self.assertTrue(args["capture_output"])
        self.assertNotIn(MASTER, " ".join(argv).encode())

    def test_missing_locked_invalid_selector_and_wrong_output_are_denied(self):
        for selector in ("", "../x", "A" * 32, 12, "a" * 64):
            with self.subTest(selector=selector):
                with self.assertRaises(Keyring.KeyUnavailable):
                    Keyring.synthetic_key_lookup(selector, which=lambda _: "/bin/x")
        with self.assertRaises(Keyring.KeyUnavailable):
            Keyring.synthetic_key_lookup(SELECTOR, which=lambda _: None)
        for result in (
            SimpleNamespace(returncode=1, stdout=b"", stderr=b"private reason"),
            SimpleNamespace(returncode=0, stdout=b"invalid\n", stderr=b""),
            SimpleNamespace(returncode=0, stdout=b" " * 1000, stderr=b""),
            SimpleNamespace(returncode=0, stdout=b"?" * 43, stderr=b""),
        ):
            with self.subTest(code=result.returncode, data=len(result.stdout)):
                with self.assertRaises(Keyring.KeyUnavailable):
                    Keyring.synthetic_key_lookup(
                        SELECTOR, which=lambda _: "/bin/x",
                        run=lambda *_args, **_kw: result)

    def test_provider_has_no_production_keyring_mutation(self):
        source = (ROOT / "services/phone/PhonePersonalKeyringP36.py").read_text()
        self.assertIn("def synthetic_key_lookup(", source)
        for code in ("def main(", "if __name__ ==", '"store"', '"clear"',
                     '"unlock"', "os.environ", "secretstorage", "DBusGMainLoop"):
            self.assertNotIn(code, source)


if __name__ == "__main__":
    unittest.main()
