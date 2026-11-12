"""Trash++ V3b signed read-only witness, actual V2w fixture and hostile inputs.

Private Ed25519 keys exist ONLY in volatile test memory; V2w separately
creates a disposable signed file, not a live authority or archive.
"""
import base64
import copy
import hashlib
from pathlib import Path
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.trash.archive_v2_signed_capture import AUDIENCE, PURPOSE
from scripts.trash.archive_v3b_signed_rollback_witness import (
    KIND, PIN_ORIGIN, WitnessRefused, canonical_claim, compare,
)
import test_archive_v2_external_floor_reader as v2w


def pub(key):
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)


class TestV3bReadOnlyWitness(unittest.TestCase):
    def setUp(self):
        # Exercise the real V2w Ed25519 signature path and real disposable
        # V2s history, not merely a mocked "signatureVerified" string.
        self.v2w_fixture = v2w.ReadOnlyExternalFloorV2wTests("runTest")
        self.v2w_fixture.setUp()
        self.addCleanup(self.v2w_fixture.doCleanups)
        self.floor = self.v2w_fixture.verify()
        self.grant = self.v2w_fixture.previous.grant_sha
        self.key = Ed25519PrivateKey.generate()
        self.pin = {
            "rootKeyId": "independent-v3b-test-root",
            "publicKeyBytes": pub(self.key),
            "origin": PIN_ORIGIN,
        }
        self.floor_key = self.v2w_fixture.pin["publicKeyBytes"]
        self.claim = {
            "schema": KIND,
            "audience": AUDIENCE,
            "purpose": PURPOSE,
            "policyOrigin": "TEST_FIXTURE_ONLY",
            "rootKeyId": self.pin["rootKeyId"],
            "ownerId": self.floor["ownerId"],
            "grantSha256": self.grant,
            "epoch": self.floor["epoch"],
            "floorSequence": self.floor["sequence"],
            "floorSha256": self.floor["externalFloorSha256"],
            "releaseSha256": self.floor["releaseSha256"],
            "witnessSequence": 1,
            "previousWitnessSha256": "",
            "revoked": False,
        }
        self.anchor = self.sign(self.claim)
        self.current = copy.deepcopy(self.anchor)

    def sign(self, claim, *, signer=None):
        if signer is None:
            signer = self.key
        return {
            "claim": copy.deepcopy(claim),
            "signatureB64": base64.b64encode(
                signer.sign(canonical_claim(claim))).decode("ascii"),
        }

    def review(self, *, prior=None, current=None, pin=None, floor=None,
               floor_key=None, owner=None, grant=None):
        return compare(
            self.anchor if prior is None else prior,
            self.current if current is None else current,
            self.pin if pin is None else pin,
            self.floor if floor is None else floor,
            expected_owner_id=self.claim["ownerId"] if owner is None else owner,
            expected_grant_sha256=self.grant if grant is None else grant,
            floor_signer_public_key=(
                self.floor_key if floor_key is None else floor_key))

    def assertDenied(self, result):
        self.assertEqual(result["state"], "MANUAL_AUTHORITY_REVIEW_REQUIRED")
        self.assertTrue(result["readOnly"])
        self.assertTrue(result["requiresIndependentReview"])
        self.assertTrue(result["witnessSignatureValidFixtureOnly"])
        self.assertIs(result["externalAnchorAuthenticated"], False)
        for field in (
            "monotonicStorageVerified", "trustedTimeVerified",
            "sourceOwnerAuthorityVerified", "serviceIdentityVerified",
            "backupCustodyVerified", "humanConsentVerified",
            "captureAllowed", "productionAllowed", "restoreAllowed",
            "burnAllowed", "automaticRetryAllowed",
            "automaticRollbackAllowed", "deleteOriginalAllowed",
        ):
            self.assertIs(result[field], False, field)
        self.assertEqual(result["safeActions"], [])
        self.assertNotIn("privateKey", result)

    def test_independent_signed_fixture_and_real_v2w_floor_deny(self):
        result = self.review()
        self.assertDenied(result)
        self.assertEqual(result["witnessSequenceObserved"], 1)
        self.assertIn("same_uid_floor_fixture", result["holdReasons"])
        self.assertNotIn("witness_sequence_rollback", result["holdReasons"])
        self.assertNotIn("witness_chain_gap", result["holdReasons"])

    def test_valid_forward_witness_hash_link_does_not_grant_access(self):
        advanced = copy.deepcopy(self.claim)
        advanced["witnessSequence"] = 2
        advanced["previousWitnessSha256"] = hashlib.sha256(
            canonical_claim(self.claim)).hexdigest()
        result = self.review(current=self.sign(advanced))
        self.assertDenied(result)
        self.assertNotIn("witness_chain_gap", result["holdReasons"])
        self.assertNotIn("witness_chain_diverged", result["holdReasons"])
        self.assertIn("same_uid_floor_fixture", result["holdReasons"])

    def test_newer_pinned_checkpoint_refuses_older_signed_replay(self):
        advanced = copy.deepcopy(self.claim)
        advanced["witnessSequence"] = 2
        advanced["previousWitnessSha256"] = hashlib.sha256(
            canonical_claim(self.claim)).hexdigest()
        new_anchor = self.sign(advanced)
        result = self.review(prior=new_anchor, current=self.anchor)
        self.assertDenied(result)
        self.assertIn("witness_sequence_rollback", result["holdReasons"])

    def test_same_counter_fork_and_missing_or_wrong_predecessor(self):
        fork = copy.deepcopy(self.claim)
        fork["revoked"] = True
        result = self.review(current=self.sign(fork))
        self.assertIn("signed_witness_equivocation", result["holdReasons"])
        self.assertIn("revocation_witness_observed", result["holdReasons"])
        advanced = copy.deepcopy(self.claim)
        advanced["witnessSequence"] = 2
        advanced["previousWitnessSha256"] = "f" * 64
        result = self.review(current=self.sign(advanced))
        self.assertIn("witness_chain_diverged", result["holdReasons"])
        advanced["witnessSequence"] = 3
        result = self.review(current=self.sign(advanced))
        self.assertIn("witness_chain_gap", result["holdReasons"])

    def test_signed_release_epoch_sequence_and_content_rollback(self):
        baseline = copy.deepcopy(self.claim)
        baseline["epoch"] += 1
        prior = self.sign(baseline)
        out = self.review(prior=prior)
        self.assertIn("release_epoch_rollback", out["holdReasons"])
        baseline = copy.deepcopy(self.claim)
        baseline["floorSequence"] += 1
        prior = self.sign(baseline)
        out = self.review(prior=prior)
        self.assertIn("release_sequence_rollback", out["holdReasons"])
        fork = copy.deepcopy(self.claim)
        fork["releaseSha256"] = "c" * 64
        out = self.review(current=self.sign(fork))
        self.assertIn("release_same_version_changed", out["holdReasons"])
        self.assertIn("witness_release_digest_disagreement", out["holdReasons"])

    def test_revoked_anchor_does_not_unrevoke(self):
        previously_revoked = copy.deepcopy(self.claim)
        previously_revoked["revoked"] = True
        out = self.review(prior=self.sign(previously_revoked))
        self.assertIn("revocation_witness_observed", out["holdReasons"])

    def test_changed_v2w_floor_cannot_hide_from_signed_witness(self):
        changed = dict(self.floor, epoch=self.floor["epoch"]+1,
                       sequence=self.floor["sequence"]+1,
                       externalFloorSha256="d"*64,
                       releaseSha256="e"*64)
        out = self.review(floor=changed)
        self.assertDenied(out)
        for reason in (
            "witness_floor_epoch_disagreement",
            "witness_floor_sequence_disagreement",
            "witness_floor_digest_disagreement",
            "witness_release_digest_disagreement",
        ):
            self.assertIn(reason, out["holdReasons"])

    def test_off_uid_floor_still_lacks_anchored_authority(self):
        observed = dict(self.floor,
                        state="OFF_UID_FLOOR_OBSERVED_DENY_ONLY",
                        offUidFileObserved=True)
        out = self.review(floor=observed)
        self.assertDenied(out)
        self.assertIn("off_uid_file_not_monotonic_authority",
                      out["holdReasons"])

    def test_invalid_signer_and_cross_domain_key_refuse(self):
        bad = self.sign(self.claim, signer=Ed25519PrivateKey.generate())
        with self.assertRaisesRegex(WitnessRefused, "V3B_SIGNATURE_REFUSED"):
            self.review(current=bad)
        same_root = dict(self.pin, publicKeyBytes=self.floor_key)
        with self.assertRaisesRegex(
                WitnessRefused, "V3B_SEPARATE_TEST_SIGNER_REQUIRED"):
            self.review(pin=same_root)
        with self.assertRaises(WitnessRefused):
            self.review(pin=dict(self.pin, origin="EXTERNALLY_PINNED_SOURCE_ROOT"))
        with self.assertRaises(WitnessRefused):
            self.review(floor_key=pub(self.key))

    def test_wrong_owner_or_grant_refuse(self):
        with self.assertRaisesRegex(WitnessRefused,
                                    "V3B_OWNER_GRANT_BINDING_INVALID"):
            self.review(owner="weather-events")
        with self.assertRaisesRegex(WitnessRefused,
                                    "V3B_OWNER_GRANT_BINDING_INVALID"):
            self.review(grant="a"*64)
        changed = copy.deepcopy(self.claim)
        changed["ownerId"] = "weather-events"
        with self.assertRaises(WitnessRefused):
            self.review(current=self.sign(changed))

    def test_signature_tamper_and_noncanonical_encoding_refuse(self):
        changed = copy.deepcopy(self.current)
        changed["claim"]["revoked"] = True
        with self.assertRaisesRegex(WitnessRefused, "V3B_SIGNATURE_REFUSED"):
            self.review(current=changed)
        malformed = copy.deepcopy(self.current)
        malformed["signatureB64"] = "!"*88
        with self.assertRaises(WitnessRefused):
            self.review(current=malformed)
        malformed = copy.deepcopy(self.current)
        malformed["signatureB64"] = malformed["signatureB64"][:-2]
        with self.assertRaises(WitnessRefused):
            self.review(current=malformed)

    def test_schema_extra_fields_invalid_types_and_boolean_counter_refuse(self):
        changes = {
            "policyOrigin": "EXTERNAL_OWNER_AUTHORITY",
            "epoch": True,
            "floorSequence": 0,
            "floorSha256": "not-a-sha",
            "witnessSequence": True,
            "previousWitnessSha256": "b"*64,
            "revoked": 1,
            "ownerId": "foreign-owner",
        }
        for name, value in changes.items():
            with self.subTest(name=name):
                trial = copy.deepcopy(self.claim)
                trial[name] = value
                with self.assertRaises(WitnessRefused):
                    self.review(current=self.sign(trial))
        trial = copy.deepcopy(self.claim)
        trial["allowProduction"] = True
        with self.assertRaises(WitnessRefused):
            self.sign(trial)
        tampered = copy.deepcopy(self.current)
        tampered["allowProduction"] = True
        with self.assertRaises(WitnessRefused):
            self.review(current=tampered)
        floor = dict(self.floor, productionAllowed=True)
        with self.assertRaisesRegex(WitnessRefused,
                                    "V3B_FLOOR_OBSERVATION_INVALID"):
            self.review(floor=floor)

    def test_old_current_and_anchor_all_replaced_is_unprovable(self):
        # Self-selected old checkpoint, paired with a self-selected current
        # witness, can look consistent. This is WHY V3b requires independent
        # durable pinning before it could ever confer any real authority.
        old = self.sign(self.claim)
        out = self.review(prior=old, current=old)
        self.assertDenied(out)
        self.assertFalse(out["externalAnchorAuthenticated"])
        self.assertIn("same_uid_floor_fixture", out["holdReasons"])

    def test_no_production_or_storage_interfaces(self):
        from scripts.trash import archive_v3b_signed_rollback_witness as module
        data = Path(module.__file__).read_text("utf-8")
        for forbidden in (
            "Ed25519PrivateKey", "sqlite3.connect(", "os.open(",
            "os.unlink(", ".write_bytes(", "subprocess.", "systemctl",
            "ArchiveStore(", "productionAllowed\": True",
        ):
            self.assertNotIn(forbidden, data)
        for name in ("sign", "migrate", "restore", "install", "capture",
                     "main", "burn", "apply"):
            self.assertFalse(hasattr(module, name), name)


if __name__ == "__main__":
    unittest.main()
