#!/usr/bin/env python3
"""C4b Package 1: fresh external witness vs root-only ledger and rotation."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c4b_signed_external_checkpoint_ci as W
import c4b_root_owned_controller_ledger_ci as L
import test_c4b_root_owned_controller_ledger_ci as F


def sha(data):
    return hashlib.sha256(data).hexdigest()


class ExternalControllerCheckpointTests(unittest.TestCase):
    def setUp(self):
        # Real Linux root-owned /run CI state, not a substitute file mock.
        self.base = F.C4bRootOwnedControllerLedgerTests(
            "test_01_root_only_staged_dual_signature_consumes_once")
        self.base.setUp()
        self.addCleanup(self.base.doCleanups)
        self.witness = Ed25519PrivateKey.generate()
        self.challenge = secrets.token_bytes(32)
        self.signed_state = self._state()
        self.make_statement()

    def _state(self):
        current = self.base.current()
        return {name: current[name] for name in W.STATE_FIELDS}

    def make_statement(self):
        self.record = {
            "schema": W.SCHEMA, "audience": W.AUDIENCE,
            "scope": W.SCOPE, "challenge": sha(self.challenge),
            **self.signed_state,
        }
        self.refresh_signatures()

    def refresh_signatures(self):
        self.raw = W._canonical(self.record)
        self.sig = self.witness.sign(W.DOMAIN + self.raw)

    def external(self, **overrides):
        args = {
            "signed_checkpoint": self.raw,
            "checkpoint_signature": self.sig,
            "independently_pinned_witness_root": self.witness.public_key(),
            "independently_pinned_witness_sha256": sha(
                self.witness.public_key().public_bytes_raw()),
            "independently_issued_challenge": self.challenge,
        }
        args.update(overrides)
        return args

    def inspect(self, **overrides):
        return W.inspect_current_checkpoint_ci_only(
            controller_state=self._state(), **self.external(**overrides))

    def refuse(self, **overrides):
        with self.assertRaises(W.Refused):
            self.inspect(**overrides)

    def commit(self, **overrides):
        return L.verify_and_commit_rotation_with_checkpoint_ci_only(
            self.base.root,
            signed_external_checkpoint=self.external(**overrides),
            **self.base.args(),
        )

    def reject_commit(self, **overrides):
        with self.assertRaises(L.Refused):
            self.commit(**overrides)

    def test_01_separate_signed_fresh_checkpoint_matches_root_owned_state(self):
        checked = self.inspect()
        self.assertTrue(checked[
            "externalPinnedSignedCheckpointMatchesRootOwnedLedgerInCi"])
        self.assertTrue(checked["signedCheckpointMatchesCallerFreshNonceInCi"])
        self.assertTrue(all(v is False for v in W.NEGATIVE.values()))

    def test_02_witnessed_rotation_consumes_staged_intent_once(self):
        self.base.stage()
        self.commit()
        self.assertEqual(self.base.current()["transitionSequence"], 5)
        self.assertFalse(self.base.current()["pendingIntentExists"])
        self.reject_commit()

    def test_03_missing_witness_blocks_witnessed_rotation(self):
        self.base.stage()
        with self.assertRaises(L.Refused):
            L.verify_and_commit_rotation_with_checkpoint_ci_only(
                self.base.root, signed_external_checkpoint=None,
                **self.base.args())
        self.assertEqual(self.base.current()["transitionSequence"], 4)

    def test_04_wrong_independently_pinned_witness_key_is_refused(self):
        impostor = Ed25519PrivateKey.generate().public_key()
        self.refuse(independently_pinned_witness_root=impostor)

    def test_05_wrong_witness_hash_is_refused(self):
        self.refuse(independently_pinned_witness_sha256="f" * 64)

    def test_06_witness_signature_tamper_is_refused_and_cannot_commit(self):
        self.refuse(checkpoint_signature=b"\0" * 64)
        self.base.stage()
        self.reject_commit(checkpoint_signature=b"\0" * 64)
        self.assertTrue(self.base.current()["pendingIntentExists"])

    def test_07_new_challenge_cannot_replay_older_witness_statement(self):
        self.refuse(independently_issued_challenge=secrets.token_bytes(32))
        self.base.stage()
        self.reject_commit(
            independently_issued_challenge=secrets.token_bytes(32))

    def test_08_signed_witness_host_mismatch_is_refused(self):
        self.record["hostId"] = "postapollo-identity-ci@different-host"
        self.refresh_signatures()
        self.refuse()

    def test_09_signed_transition_sequence_ahead_of_controller_refuses(self):
        self.record["transitionSequence"] += 1
        self.refresh_signatures()
        self.refuse()

    def test_10_signed_transition_chain_head_mismatch_is_refused(self):
        self.record["transitionSha256"] = "a" * 64
        self.refresh_signatures()
        self.refuse()

    def test_11_signed_release_floor_mismatch_is_refused(self):
        self.record["minimumReleaseSequence"] += 1
        self.refresh_signatures()
        self.refuse()

    def test_12_signed_controller_root_mismatch_is_refused(self):
        self.record["controllerRootSha256"] = "b" * 64
        self.refresh_signatures()
        self.refuse()

    def test_13_signed_controller_policy_mismatch_is_refused(self):
        self.record["controllerPolicySha256"] = "c" * 64
        self.refresh_signatures()
        self.refuse()

    def test_14_production_scope_masquerade_is_refused(self):
        self.record["scope"] = "production-host-admission"
        self.refresh_signatures()
        self.refuse()

    def test_15_duplicate_signed_field_is_refused(self):
        duplicated = self.raw.replace(
            b'"schema":', b'"schema":"forged","schema":', 1)
        self.refuse(signed_checkpoint=duplicated)

    def test_16_noncanonical_signed_json_is_refused(self):
        self.refuse(signed_checkpoint=json.dumps(
            self.record, indent=2).encode("ascii"))

    def test_17_old_controller_root_cannot_double_as_witness_signer(self):
        old_root = self.base.rot.previous_root
        self.witness = old_root
        self.refresh_signatures()
        self.refuse()

    def test_18_restored_older_db_refused_by_newer_externally_signed_cursor(self):
        # The external fixture witness signs the NEWER cursor first; restore
        # prior SQLite file bytes afterwards. Only an independently CURRENT
        # witness can detect a full privileged state rollback.
        self.base.stage()
        path = self.base.root / L.DB_FILE
        older_db_bytes = path.read_bytes()
        self.commit()
        self.signed_state = self._state()
        self.make_statement()  # the separately signed newer state
        self.assertEqual(self.inspect()["transitionSequence"], 5)
        with path.open("wb") as out:
            out.write(older_db_bytes)
            out.flush()
            os.fsync(out.fileno())
        self.assertEqual(self.base.current()["transitionSequence"], 4)
        self.refuse()
        self.reject_commit()
        self.assertEqual(self.base.current()["transitionSequence"], 4)

    def test_19_both_fixtures_can_replay_old_state_without_protected_witness(self):
        # This openly documents the trust assumption. If an attacker controls
        # BOTH the DB and witness signing key, a new consistent signed proof
        # cannot be distinguished from a trusted historical state here.
        self.base.stage()
        path = self.base.root / L.DB_FILE
        older = path.read_bytes()
        self.commit()
        with path.open("wb") as out:
            out.write(older)
        self.assertEqual(self.base.current()["transitionSequence"], 4)
        self.assertTrue(self.inspect()[
            "externalPinnedSignedCheckpointMatchesRootOwnedLedgerInCi"])
        self.assertFalse(W.NEGATIVE["realWitnessSignerCustodyVerified"])
        self.assertFalse(W.NEGATIVE["hardwareRollbackResistanceVerified"])

    def test_20_malformed_witness_and_controller_types_refuse(self):
        self.refuse(signed_checkpoint="not bytes")
        self.refuse(checkpoint_signature=b"x")
        self.refuse(independently_issued_challenge=b"x")
        with self.assertRaises(W.Refused):
            W.inspect_current_checkpoint_ci_only(
                controller_state={"hostId": "bad"},
                **self.external())

    def test_21_signed_witness_source_is_never_a_production_grant(self):
        source = Path(W.__file__).read_text()
        ledger = Path(L.__file__).read_text()
        for forbidden in ("Ed25519PrivateKey.generate(", "systemctl start",
                          "rpm-ostree install", '"hostAuthenticated": True',
                          '"productionAuthority": True'):
            self.assertNotIn(forbidden, source)
        self.assertIn("verify_and_commit_rotation_with_checkpoint_ci_only", ledger)
        self.assertTrue(all(v is False for v in W.NEGATIVE.values()))

    def test_22_witness_nonce_consumed_in_same_rotation_commit(self):
        self.base.stage()
        result = self.commit()
        self.assertTrue(result["singlePrivilegedTestIntentConsumedInCi"])
        db = L._connect(self.base.root)
        try:
            rows = db.execute(
                "SELECT challenge_sha256,witness_public_sha256,"
                "committed_transition_sha256 "
                "FROM consumed_external_witness_challenges").fetchall()
        finally:
            db.close()
        self.assertEqual(rows, [(
            sha(self.challenge),
            sha(self.witness.public_key().public_bytes_raw()),
            sha(self.base.rot.encoded))])

    def test_23_rejected_bad_rotation_does_not_spend_witness_nonce(self):
        self.base.stage()
        with self.assertRaises(L.Refused):
            L.verify_and_commit_rotation_with_checkpoint_ci_only(
                self.base.root, signed_external_checkpoint=self.external(),
                **self.base.args(proposed_signature=b"\0" * 64))
        db = L._connect(self.base.root)
        try:
            total = db.execute(
                "SELECT count(*) FROM consumed_external_witness_challenges"
            ).fetchone()[0]
        finally:
            db.close()
        self.assertEqual(total, 0)
        self.assertEqual(self.base.current()["transitionSequence"], 4)
        self.commit()
        self.assertEqual(self.base.current()["transitionSequence"], 5)

    def test_24_preconsumed_witness_nonce_blocks_valid_double_use(self):
        self.base.stage()
        db = L._connect(self.base.root)
        try:
            db.execute(
                "INSERT INTO consumed_external_witness_challenges "
                "(challenge_sha256,witness_public_sha256,"
                "committed_transition_sha256) VALUES(?,?,?)",
                (sha(self.challenge),
                 sha(self.witness.public_key().public_bytes_raw()),
                 "e" * 64))
        finally:
            db.close()
        with self.assertRaisesRegex(
                L.Refused, "C4B_P1_SIGNED_WITNESS_CHALLENGE_ALREADY_CONSUMED"):
            self.commit()
        self.assertEqual(self.base.current()["transitionSequence"], 4)
        self.assertTrue(self.base.current()["pendingIntentExists"])

    def test_25_missing_consumption_table_refuses_not_resets(self):
        self.base.stage()
        db = L._connect(self.base.root)
        try:
            db.execute("DROP TABLE consumed_external_witness_challenges")
        finally:
            db.close()
        self.reject_commit()
        self.assertEqual(self.base.current()["transitionSequence"], 4)
        self.assertTrue(self.base.current()["pendingIntentExists"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
