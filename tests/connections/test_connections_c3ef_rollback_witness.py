#!/usr/bin/env python3
"""C3e-F: separate witness detects restored authority state (CI-only).

All real GPG keys and all three ledgers live in TEMPORARY CI directories.
The witness is a separate logical store, not a separately secured machine.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "tests/connections/c3e_release_trust"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


witness = load("c3ef_witness_test", HERE / "C3eRollbackWitness.py")
previous = load("c3ef_previous_fixture", ROOT / "tests/connections/test_connections_c3ee_authority_owned_floor.py")


class C3eFRollbackWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous.C3eEAuthorityOwnedFloorTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        previous.C3eEAuthorityOwnedFloorTests.tearDownClass()

    def setUp(self):
        self.fx = previous.C3eEAuthorityOwnedFloorTests("test_01_explicitly_bootstrapped_but_empty_authority_will_not_attest")
        self.fx.setUp()
        self.location = self.fx.folder / "independent-witness.sqlite"
        self.node = self.fx.node
        self.root_pin = self.fx.fprs["release-root"]
        self.anchor_pin = self.fx.fprs["external-anchor"]
        witness.bootstrap_witness(
            self.location, authority_anchor_pin=self.anchor_pin,
            release_root_pin=self.root_pin, node_id=self.node,
            initial_policy_epoch=3, initial_release_sequence=8)

    def tearDown(self):
        self.fx.tearDown()

    def request(self, **changes):
        args = dict(
            witness_db=self.location, client_db=self.fx.client_db,
            authority_anchor_public=self.fx.public["external-anchor"],
            authority_anchor_pin=self.anchor_pin, node_id=self.node,
            release_root_pin=self.root_pin,
            request_proof=self.fx.remote_proof,
            release_root_public=self.fx.public["release-root"],
            policy=self.fx.policy, policy_signature=self.fx.policy_sig,
            delegated_public=self.fx.public["release-delegated"],
            manifest=self.fx.manifest, manifest_signature=self.fx.manifest_sig,
            artifact=self.fx.artifact,
        )
        args.update(changes)
        return witness.admit_with_witness(**args)

    def assert_refused(self, code, **kwargs):
        with self.assertRaises(witness.Refused) as result:
            self.request(**kwargs)
        self.assertEqual(str(result.exception), code)

    def stored(self):
        return witness.inspect_witness(self.location)

    def test_01_bootstrap_does_not_authorize_unsigned_release_or_attestation(self):
        self.assertEqual(self.stored()[3:], (3, 8))
        self.assert_refused("AUTHORITY_CALLBACK_UNAVAILABLE")
        self.assertEqual(self.stored()[3:], (3, 8))

    def test_02_signed_release_eight_passes_distinct_witness_gate(self):
        self.fx.advance()
        self.assertEqual(self.request(), witness.SUCCESS)
        self.assertEqual(self.stored()[3:], (3, 8))
        self.assertEqual(self.fx.client_db.exists(), True)

    def test_03_signed_advance_moves_all_three_ledger_floors(self):
        self.fx.advance()
        self.request()
        self.fx.issue(4, 9, b"fake-signed-release-9")
        self.fx.advance()
        self.assertEqual(self.request(), witness.SUCCESS)
        self.assertEqual(self.stored()[3:], (4, 9))
        self.assertEqual(witness.durable.inspect(self.fx.authority_db)[1:3], (4, 9))
        self.assertEqual(witness.durable.inspect(self.fx.client_db)[1:3], (4, 9))

    def test_04_rolled_back_authority_cannot_sign_accepted_old_floor(self):
        self.fx.advance()
        self.request()
        prior_authority = self.fx.folder / "old-authority"
        shutil.copy2(self.fx.authority_db, prior_authority)
        self.fx.issue(4, 9, b"fake-signed-release-9")
        self.fx.advance()
        self.request()
        shutil.copy2(prior_authority, self.fx.authority_db)
        self.fx.issue(3, 8, b"fake-signed-release-8")
        self.assert_refused("WITNESS_POLICY_ROLLBACK_REFUSED")
        self.assertEqual(self.stored()[3:], (4, 9))

    def test_05_client_and_authority_both_restored_but_witness_remembers_newer(self):
        self.fx.advance()
        self.request()
        old_authority = self.fx.folder / "old-authority"
        old_client = self.fx.folder / "old-client"
        shutil.copy2(self.fx.authority_db, old_authority)
        shutil.copy2(self.fx.client_db, old_client)
        self.fx.issue(4, 9, b"fake-signed-release-9")
        self.fx.advance()
        self.request()
        shutil.copy2(old_authority, self.fx.authority_db)
        shutil.copy2(old_client, self.fx.client_db)
        self.fx.issue(3, 8, b"fake-signed-release-8")
        self.assert_refused("WITNESS_POLICY_ROLLBACK_REFUSED")
        self.assertEqual(self.stored()[3:], (4, 9))

    def test_06_restoring_witness_too_exposes_last_unsolved_rollback(self):
        self.fx.advance()
        self.request()
        old_authority = self.fx.folder / "old-authority"
        old_client = self.fx.folder / "old-client"
        old_witness = self.fx.folder / "old-witness"
        for source, dest in (
            (self.fx.authority_db, old_authority),
            (self.fx.client_db, old_client), (self.location, old_witness)):
            shutil.copy2(source, dest)
        self.fx.issue(4, 9, b"fake-signed-release-9")
        self.fx.advance()
        self.request()
        for source, dest in (
            (old_authority, self.fx.authority_db),
            (old_client, self.fx.client_db), (old_witness, self.location)):
            shutil.copy2(source, dest)
        self.fx.issue(3, 8, b"fake-signed-release-8")
        # KNOWN UNSOLVED: shared privileged rollback defeats all ordinary DBs.
        self.assertEqual(self.request(), witness.SUCCESS)
        self.assertEqual(self.stored()[3:], (3, 8))

    def test_07_false_anchor_key_cannot_imitate_real_authority(self):
        self.fx.advance()
        before = self.stored()
        self.assert_refused(
            "AUTHORITY_SIGNATURE_REFUSED_EXTERNAL_ANCHOR_PIN_MISMATCH",
            authority_anchor_public=self.fx.public["forger"])
        self.assertEqual(self.stored(), before)

    def test_08_mismatched_witness_enrolled_identity_fails(self):
        self.fx.advance()
        # A witness with an unexpected stored node/pin cannot silently
        # migrate to a valid but differently scoped authority response.
        with sqlite3.connect(self.location) as db:
            db.execute("UPDATE witness SET node_id=? WHERE id=1",
                       ("other-synthetic-node-01",))
        self.assert_refused("WITNESS_ENROLLED_IDENTITY_MISMATCH")
        with sqlite3.connect(self.location) as db:
            db.execute("UPDATE witness SET node_id=?, authority_anchor_pin=? WHERE id=1",
                       (self.node, self.fx.fprs["forger"]))
        self.assert_refused("WITNESS_ENROLLED_IDENTITY_MISMATCH")
        self.assertEqual(self.stored()[3:], (3, 8))

    def test_09_replayed_signature_refused_for_fresh_verifier_challenge(self):
        self.fx.advance()
        replay = self.fx.remote_proof("b" * 64)
        self.assert_refused(
            "AUTHORITY_SIGNATURE_REFUSED_REPLAYED_OR_UNSOLICITED_PROOF",
            request_proof=lambda challenge: replay)

    def test_10_tampered_release_does_not_advance_witness(self):
        self.fx.advance()
        before = self.stored()
        self.fx.manifest.write_text(self.fx.manifest.read_text() + " ")
        self.assert_refused(
            "CLIENT_RELEASE_REFUSED_CRYPTO_REFUSED_INVALID_DETACHED_SIGNATURE")
        self.assertEqual(self.stored(), before)

    def test_11_missing_witness_denies_with_no_auto_bootstrap(self):
        self.fx.advance()
        self.location.unlink()
        self.assert_refused("WITNESS_STATE_UNAVAILABLE")
        self.assertFalse(self.location.exists())

    def test_12_bad_witness_permissions_and_symlink_denied(self):
        self.fx.advance()
        self.location.chmod(0o644)
        self.assert_refused("WITNESS_STATE_UNAVAILABLE")
        self.location.chmod(0o600)
        linked = self.fx.folder / "witness-symlink"
        linked.symlink_to(self.location)
        self.assert_refused("WITNESS_STATE_UNAVAILABLE", witness_db=linked)

    def test_13_client_and_witness_must_not_share_a_database(self):
        self.fx.advance()
        self.assert_refused("WITNESS_AND_CLIENT_STATE_NOT_SEPARATE",
                            client_db=self.location)

    def test_14_missing_client_database_refuses_without_witness_commit(self):
        self.fx.advance()
        before = self.stored()
        lost = self.fx.folder / "lost-client.db"
        self.assert_refused(
            "CLIENT_RELEASE_REFUSED_LEDGER_MISSING_REQUIRES_EXPLICIT_BOOTSTRAP",
            client_db=lost)
        self.assertEqual(self.stored(), before)
        self.assertFalse(lost.exists())

    def test_15_no_silent_witness_rebootstrap(self):
        with self.assertRaises(witness.Refused) as err:
            witness.bootstrap_witness(
                self.location, authority_anchor_pin=self.anchor_pin,
                release_root_pin=self.root_pin, node_id=self.node,
                initial_policy_epoch=3, initial_release_sequence=8)
        self.assertEqual(str(err.exception), "WITNESS_EXISTS_OR_UNSAFE_PATH")

    def test_16_production_connections_broker_unmodified(self):
        base = ROOT / "services/connections"
        self.assertIn("readonly property bool credentialActionsEnabled: false",
                      (base / "ConnectionsBroker.qml").read_text())
        self.assertIn("readonly property bool hostAuthenticated: false",
                      (base / "ConnectionsRequestStatus.qml").read_text())
        for path in (*base.glob("*.qml"), *base.glob("*.js"), base / "qmldir"):
            self.assertNotIn("C3eRollbackWitness", path.read_text(), path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
