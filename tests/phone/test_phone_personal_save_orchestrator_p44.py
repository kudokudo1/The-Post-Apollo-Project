"""P44 end-to-end disposable PHONE Favorite + Notes transaction matrix.

Uses P43 parser, P36 one-use synthetic coordinator, P34 contact matching,
P35 AES-256-GCM encrypted CAS and readback. Never uses a real iPhone or keyring.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
import PhonePersonalContactVault as Vault
import PhonePersonalHostGateP36 as P36
import PhonePersonalSaveOrchestratorP44 as P44
import PhonePersonalVaultRecoveryP40R as Recovery

PROFILE = "123e4567-e89b-42d3-a456-426614174000"
MASTER = b"X" * 32
ROW = "123e4567:epoch-19:row-7"
CARD = {
    "id": ROW, "serviceId": "blueferry", "deviceProfileId": PROFILE,
    "displayNameInProfile": "Synthetic Person", "hasAddressDetails": True,
    "phoneNumbers": ["+15550001001"],
    "emailAddresses": ["fiction@example.invalid"],
    "phoneCount": 1, "emailCount": 1,
}


def entry(action, **kw):
    return dict(schema="post-apollo.phone.personal-editor-intent.p43.v1",
                selectedContactId=ROW, action=action, **kw)


def plan(*operations):
    return {
        "schema": P44.PLAN_SCHEMA,
        "status": "UNTRUSTED_REVIEW_ONLY",
        "operations": list(operations),
    }


class DisposableWorkflowTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory(prefix="p44-disposable-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / Vault.ROOT_NAME
        self.allow = True
        self.approved_actions = {"LINK", "FAVORITE", "NOTE", "UNLINK"}
        self.observe_calls = 0
        self.gesture_calls = []
        self.key_calls = 0
        self.active = True
        self.owner = ":1.123"
        self.epoch = 19

        def observe():
            self.observe_calls += 1
            return P36.ObservedFixture(
                profile=PROFILE, provider_owner=self.owner,
                session="synthetic-session-19", snapshot_epoch=self.epoch,
                expires_at=150, personal_scope=True,
                contacts_approved=self.active, device_connected=True,
                cards=(dict(CARD),),
            )
        def gesture(intent, _state):
            self.gesture_calls.append(intent.action)
            return self.allow and intent.action in self.approved_actions
        def lookup():
            self.key_calls += 1
            return MASTER

        self.coordinator = P36.FixtureCoordinator(
            observe=observe, verify_gesture=gesture, key_lookup=lookup,
            clock=lambda: 100, root=self.root
        )
        self.coordinator.apply(P36.ActionFixture(
            action="LINK", selected_row=ROW, expected_revision=0,
            nonce="0" * 32
        ))
        self.before = Vault.read(MASTER, PROFILE, self.root)
        self.assertEqual(self.before["revision"], 1)
        self.key_calls = 0
        self.gesture_calls = []

    def encrypted_bytes(self):
        return (self.root / Vault._filename(MASTER, PROFILE)).read_bytes()

    def apply(self, ops, revision=1, nonces=None):
        if nonces is None:
            nonces = iter(("a" * 32, "b" * 32))
        return P44.run_disposable_plan(
            plan=plan(*ops), coordinator=self.coordinator,
            initial_revision=revision, issue_nonce=lambda: next(nonces)
        )

    def test_complete_two_action_real_encrypted_fixture_workflow(self):
        result = self.apply((
            entry("FAVORITE", favorite=True),
            entry("NOTE", note="FICTIONAL PRIVATE NOTE")
        ))
        self.assertEqual(result, {
            **P44.DONE, "completedActions": 2
        })
        self.assertTrue(all(result[field] is False for field in (
            "productionEnabled", "humanConsentVerified",
            "durableCommitProven", "retryAuthorized",
            "vaultWriteAuthorizedForProduction"
        )))
        self.assertEqual(self.key_calls, 2)
        self.assertGreaterEqual(self.gesture_calls.count("FAVORITE"), 3)
        self.assertGreaterEqual(self.gesture_calls.count("NOTE"), 3)
        document = Vault.read(MASTER, PROFILE, self.root)
        self.assertEqual(document["revision"], 3)
        self.assertEqual(len(document["entries"]), 1)
        self.assertTrue(document["entries"][0]["favorite"])
        self.assertEqual(document["entries"][0]["note"], "FICTIONAL PRIVATE NOTE")
        ciphertext = self.encrypted_bytes()
        self.assertNotIn(b"FICTIONAL PRIVATE NOTE", ciphertext)
        self.assertNotIn(b"fiction@example.invalid", ciphertext)
        self.assertNotIn(b"Synthetic Person", ciphertext)
        self.assertNotIn("FICTIONAL PRIVATE NOTE", repr(result))

    def test_independent_note_clear_and_favorite_off(self):
        self.apply((entry("FAVORITE", favorite=True),
                    entry("NOTE", note="FICTIONAL PRIVATE NOTE")))
        result = self.apply((
            entry("FAVORITE", favorite=False),
            entry("NOTE", note="")
        ), revision=3, nonces=iter(("c" * 32, "d" * 32)))
        self.assertEqual(result["completedActions"], 2)
        document = Vault.read(MASTER, PROFILE, self.root)
        self.assertEqual(document["revision"], 5)
        self.assertFalse(document["entries"][0]["favorite"])
        self.assertEqual(document["entries"][0]["note"], "")

    def test_revoke_before_second_action_stops_and_reports_partial(self):
        self.approved_actions.remove("NOTE")
        result = self.apply((
            entry("FAVORITE", favorite=True),
            entry("NOTE", note="FICTIONAL PRIVATE NOTE")
        ))
        self.assertEqual(result, {**P44.STOPPED, "completedActions": 1})
        document = Vault.read(MASTER, PROFILE, self.root)
        self.assertEqual(document["revision"], 2)
        self.assertTrue(document["entries"][0]["favorite"])
        self.assertEqual(document["entries"][0]["note"], "")
        self.assertEqual(self.key_calls, 1)  # no key release for revoked step

    def test_stale_cas_refusal_never_retries_or_overwrites(self):
        original = self.encrypted_bytes()
        result = self.apply((entry("NOTE", note="private"),), revision=0)
        self.assertEqual(result, {**P44.STOPPED, "completedActions": 0})
        self.assertEqual(self.encrypted_bytes(), original)
        self.assertEqual(self.key_calls, 1)

    def test_duplicate_one_use_nonces_stop_before_second_action(self):
        result = self.apply((
            entry("FAVORITE", favorite=True),
            entry("NOTE", note="PRIVATE NEVER SAVED")
        ), nonces=iter(("a" * 32, "a" * 32)))
        self.assertEqual(result, {**P44.STOPPED, "completedActions": 1})
        self.assertEqual(self.key_calls, 1)
        state = Vault.read(MASTER, PROFILE, self.root)
        self.assertEqual(state["revision"], 2)
        self.assertEqual(state["entries"][0]["note"], "")

    def test_invalid_whole_plan_rejected_before_any_key_or_mutation(self):
        original = self.encrypted_bytes()
        cases = (
            plan(entry("LINK")),
            plan(entry("UNLINK")),
            plan(entry("NOTE", note="private"),
                 entry("FAVORITE", favorite=True)),
            plan(entry("FAVORITE", favorite=True),
                 entry("FAVORITE", favorite=False)),
            plan(entry("NOTE", note="bad"),
                 entry("NOTE", note="twice")),
            plan(entry("FAVORITE", favorite=True),
                 {**entry("NOTE", note="private"), "approved": True}),
            plan({**entry("NOTE", note="private"), "selectedContactId": "../bad"}),
            plan({**entry("NOTE", note="private"), "note": "\ud800"}),
            plan(entry("NOTE", note="private"), entry("NOTE", note="too"),
                 entry("FAVORITE", favorite=True)),
            {"schema": P44.PLAN_SCHEMA,
             "status": "SAVED",
             "operations": [entry("FAVORITE", favorite=True)]},
            {"schema": P44.PLAN_SCHEMA,
             "status": "UNTRUSTED_REVIEW_ONLY",
             "operations": [entry("NOTE", note="private")],
             "productionEnabled": True},
        )
        for bad in cases:
            with self.subTest(test_case=str(len(str(bad)))):
                result = P44.run_disposable_plan(
                    plan=bad, coordinator=self.coordinator, initial_revision=1,
                    issue_nonce=lambda: self.fail("nonce called for bad plan"),
                )
                self.assertEqual(result, P44.REFUSED)
                self.assertEqual(self.encrypted_bytes(), original)
                self.assertEqual(self.key_calls, 0)

    def test_second_action_different_selection_refused_preflight(self):
        other = {**entry("NOTE", note="private"),
                 "selectedContactId": "different:row"}
        result = self.apply((entry("FAVORITE", favorite=True), other))
        self.assertEqual(result, P44.REFUSED)
        self.assertEqual(self.key_calls, 0)

    def test_fs_sync_after_replace_is_ambiguous_and_never_retried(self):
        old = self.encrypted_bytes()
        real_fsync = os.fsync
        calls = []
        def flaky(fd):
            calls.append(fd)
            if len(calls) == 2:  # output file synced, rename happened
                raise OSError("SIMULATED PRIVATE DIRECTORY FSYNC FAILURE")
            return real_fsync(fd)
        with patch.object(Vault.os, "fsync", side_effect=flaky):
            result = self.apply((entry("NOTE", note="UNCERTAIN PRIVATE NOTE"),))
        self.assertEqual(result, {**P44.STOPPED, "completedActions": 0})
        self.assertEqual(len(calls), 2)
        self.assertNotIn("UNCERTAIN PRIVATE NOTE", str(result))
        self.assertNotIn("SIMULATED", str(result))
        # The new sealed state can be present despite failed acknowledgment.
        # P40R is an OBSERVATION and cannot issue a durable commit receipt.
        current = Vault.read(MASTER, PROFILE, self.root)
        self.assertEqual(current["revision"], 2)
        self.assertNotEqual(self.encrypted_bytes(), old)
        observed = Recovery.inspect_after_uncertain_save(
            master_key=MASTER, profile=PROFILE, root=self.root,
            pending_document=current, expected_revision=1,
        )
        self.assertEqual(observed["status"],
                         "CURRENT_CIPHERTEXT_MATCHES_PENDING")
        self.assertFalse(observed["durableCommitProven"])
        self.assertFalse(observed["retryAuthorized"])

    def test_denied_state_prevents_key_release(self):
        self.active = False
        result = self.apply((entry("NOTE", note="private"),))
        self.assertEqual(result["completedActions"], 0)
        self.assertEqual(self.key_calls, 0)
        self.assertEqual(Vault.read(MASTER, PROFILE, self.root), self.before)

    def test_no_exposed_production_endpoint_or_signer(self):
        source = (ROOT / "services/phone/PhonePersonalSaveOrchestratorP44.py").read_text()
        for forbidden in (
            "def main(", "if __name__ ==", "import socket",
            "import dbus", "subprocess.", "QtQuick", "print(",
            "secret-tool", "productionEnabled\": True",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
