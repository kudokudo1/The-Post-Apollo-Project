#!/usr/bin/env python3
"""32 fail-closed cutover tests. No NAS, SQLite, host, keys or signer created."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "tests/connections/c3e_release_trust"
MOD = SRC / "C3eCustodianCutoverNegativePreflight.py"

spec = importlib.util.spec_from_file_location("c3e_cutover_negative", MOD)
if spec is None or spec.loader is None:
    raise RuntimeError("C3E_CUTOVER_TEST_SOURCE_MISSING")
M = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = M
spec.loader.exec_module(M)


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


class CutoverNeverAuthorizesTests(unittest.TestCase):
    def setUp(self):
        self.old_head = sha("local-sqlite-untrusted-head")
        self.old_epoch = "a0" * 16
        self.old_root = sha("untrusted-local-root")
        self.old_history_signer = sha("untrusted-local-history-signer")
        self.old_challenge = sha("untrusted-local-challenge")
        self.local = {
            "schema": M.S.SCHEMA,
            "status": M.S.STATUS_LOCAL,
            "source": M.S.LOCAL_DEVELOPMENT,
            "testHeadSha256": self.old_head,
            "testSequence": 41,
            **M.S.DENIED,
        }
        self.candidate = {
            "schema": M.CANDIDATE_SCHEMA,
            "purpose": M.PURPOSE,
            "status": M.CANDIDATE,
            "hostId": "fixture-host-identity",
            "rootPublicKeySha256": sha("untrusted-candidate-root"),
            "historySignerSha256": sha("untrusted-candidate-history"),
            "newEpoch": "b1" * 16,
            "newGenesisHeadSha256": sha("untrusted-candidate-genesis"),
            "newSequence": 1,
            "importedChallengeDigests": [],
        }
        self.opts = {
            "known_development_role_fingerprints":
                (self.old_root, self.old_history_signer),
            "known_development_epochs": (self.old_epoch,),
            "locally_issued_challenge_digests": (self.old_challenge,),
        }

    def inspect(self, *, local=None, candidate=None, **kw):
        return M.inspect_candidate_ci_only(
            local_snapshot=self.local if local is None else local,
            candidate=self.candidate if candidate is None else candidate,
            **{**self.opts, **kw},
        )

    def refused(self, reason, *, local=None, candidate=None, **kw):
        with self.assertRaisesRegex(M.Refused, reason):
            self.inspect(local=local, candidate=candidate, **kw)

    def candidate_with(self, **changes):
        return {**self.candidate, **changes}

    def local_with(self, **changes):
        return {**self.local, **changes}

    def test_01_proposed_new_custodian_format_still_all_authority_false(self):
        out = self.inspect()
        self.assertEqual(out["status"], M.HOLD)
        self.assertEqual(out["schema"], M.SCHEMA)
        self.assertIs(out["candidateFieldsConsistentInCI"], True)
        for flag in M.DENIED:
            self.assertIs(out[flag], False, flag)

    def test_02_protected_cutover_has_no_callable_activation(self):
        with self.assertRaisesRegex(M.Refused, "NO_PROTECTED_AUTHORITY"):
            M.protected_cutover(self.candidate)

    def test_03_local_authentication_flag_cannot_be_true(self):
        self.refused("LOCAL_AUTHORITY_INJECTION",
                     local=self.local_with(hostAuthenticated=True))

    def test_04_local_extra_field_cannot_grant(self):
        self.refused("LOCAL_EXACT_FIELDS",
                     local=self.local_with(operatorApproved=True))

    def test_05_wrong_local_schema_refused(self):
        self.refused("LOCAL_SNAPSHOT_NOT_UNTRUSTED_FIXTURE",
                     local=self.local_with(schema="unknown"))

    def test_06_claimed_protected_source_as_local_refused(self):
        self.refused("LOCAL_SNAPSHOT_NOT_UNTRUSTED_FIXTURE",
                     local=self.local_with(source=M.S.PROTECTED_REQUIRED))

    def test_07_old_local_head_cannot_become_new_genesis(self):
        self.refused("LOCAL_HEAD_CANNOT_BECOME_GENESIS",
                     candidate=self.candidate_with(
                         newGenesisHeadSha256=self.old_head))

    def test_08_local_root_key_cannot_become_candidate_root(self):
        self.refused("OLD_OR_ALIASED_SIGNER",
                     candidate=self.candidate_with(
                         rootPublicKeySha256=self.old_root))

    def test_09_local_history_signer_cannot_become_candidate_history_signer(self):
        self.refused("OLD_OR_ALIASED_SIGNER",
                     candidate=self.candidate_with(
                         historySignerSha256=self.old_history_signer))

    def test_10_candidate_root_and_history_signer_must_not_alias(self):
        self.refused("OLD_OR_ALIASED_SIGNER",
                     candidate=self.candidate_with(
                         historySignerSha256=self.candidate["rootPublicKeySha256"]))

    def test_11_local_epoch_reuse_refused(self):
        self.refused("LOCAL_EPOCH_CANNOT_BECOME_PROTECTED",
                     candidate=self.candidate_with(newEpoch=self.old_epoch))

    def test_12_local_challenge_cannot_be_imported(self):
        self.refused("LOCAL_CHALLENGE_TRANSFER_FORBIDDEN",
                     candidate=self.candidate_with(
                         importedChallengeDigests=[self.old_challenge]))

    def test_13_any_imported_nonce_is_refused_even_if_claimed_new(self):
        self.refused("LOCAL_CHALLENGE_TRANSFER_FORBIDDEN",
                     candidate=self.candidate_with(
                         importedChallengeDigests=[sha("different-fixture")]))

    def test_14_claimed_candidate_production_authority_field_refused(self):
        self.refused("CANDIDATE_EXACT_FIELDS",
                     candidate=self.candidate_with(productionAuthority=True))

    def test_15_claimed_enrolled_status_refused(self):
        self.refused("CANDIDATE_DOMAIN_OR_HOST",
                     candidate=self.candidate_with(
                         status="INDEPENDENT_CUSTODIAN_ENROLLED"))

    def test_16_cross_purpose_c5_role_refused(self):
        self.refused("CANDIDATE_DOMAIN_OR_HOST",
                     candidate=self.candidate_with(
                         purpose="postapollo.connections.timew-c5-spend"))

    def test_17_bad_root_fingerprint_refused(self):
        self.refused("NEW_GENESIS_OR_KEY_FORMAT",
                     candidate=self.candidate_with(rootPublicKeySha256="abc"))

    def test_18_boolean_sequence_refused(self):
        self.refused("NEW_GENESIS_OR_KEY_FORMAT",
                     candidate=self.candidate_with(newSequence=True))

    def test_19_old_local_sequence_not_carried_forward(self):
        self.refused("NEW_GENESIS_OR_KEY_FORMAT",
                     candidate=self.candidate_with(newSequence=41))

    def test_20_malformed_epoch_refused(self):
        self.refused("NEW_GENESIS_OR_KEY_FORMAT",
                     candidate=self.candidate_with(newEpoch="bad"))

    def test_21_invalid_host_refused(self):
        self.refused("CANDIDATE_DOMAIN_OR_HOST",
                     candidate=self.candidate_with(hostId="host\nspoof"))

    def test_22_local_head_format_refused(self):
        self.refused("LOCAL_SNAPSHOT_NOT_UNTRUSTED_FIXTURE",
                     local=self.local_with(testHeadSha256="00"))

    def test_23_local_boolean_sequence_refused(self):
        self.refused("LOCAL_SNAPSHOT_NOT_UNTRUSTED_FIXTURE",
                     local=self.local_with(testSequence=True))

    def test_24_malformed_known_old_key_roster_refused(self):
        self.refused("LOCAL_ROLE_FINGERPRINTS_INVALID",
                     known_development_role_fingerprints=("bad",))

    def test_25_duplicate_old_role_key_roster_refused(self):
        self.refused("LOCAL_ROLE_FINGERPRINTS_INVALID",
                     known_development_role_fingerprints=(self.old_root, self.old_root))

    def test_26_duplicate_locally_issued_nonce_roster_refused(self):
        self.refused("OLD_CHALLENGE_ROSTER_INVALID",
                     locally_issued_challenge_digests=(
                         self.old_challenge, self.old_challenge))

    def test_27_imported_nonce_wrong_type_refused(self):
        self.refused("IMPORTED_CHALLENGES_INVALID",
                     candidate=self.candidate_with(importedChallengeDigests=None))

    def test_28_candidate_result_is_audit_only_not_an_independent_head(self):
        result = self.inspect()
        self.assertEqual(
            result["nextRequiredAction"],
            "OPERATOR_ENROLL_INDEPENDENT_CUSTODIAN_SEPARATELY")
        self.assertEqual(result["status"], M.HOLD)
        self.assertEqual(
            result["localHistoryAuditReferenceOnlySha256"],
            hashlib.sha256(
                b"C3E_LOCAL_AUDIT_ONLY\x00"
                + self.old_head.encode("ascii") + b"\x00" + b"41"
            ).hexdigest())
        self.assertNotIn("trustedCurrentHeadSha256", result)
        self.assertNotIn("signedOperatorEnrollment", result)
        self.assertNotIn("remoteServiceConnection", result)


    def test_29_omitted_old_root_roster_never_claims_real_custody(self):
        # If the caller omits the old root, format checks cannot detect reuse.
        # That must NEVER become independent-enrollment approval.
        candidate = self.candidate_with(rootPublicKeySha256=self.old_root)
        out = self.inspect(candidate=candidate,
                           known_development_role_fingerprints=())
        self.assertEqual(out["status"], M.HOLD)
        self.assertIs(out["candidateFieldsConsistentInCI"], True)
        for flag in M.DENIED:
            self.assertIs(out[flag], False, flag)

    def test_30_omitted_old_epoch_roster_never_claims_real_custody(self):
        # Distinctness is only relative to known fixture data.
        out = self.inspect(
            candidate=self.candidate_with(newEpoch=self.old_epoch),
            known_development_epochs=(),
        )
        self.assertEqual(out["status"], M.HOLD)
        self.assertIs(out["operatorRootPinnedOutOfBand"], False)
        self.assertIs(out["cutoverAuthorized"], False)

    def test_31_missing_issued_nonce_inventory_does_not_allow_import(self):
        # No old challenge inventory can prove no challenge existed.
        self.refused(
            "LOCAL_CHALLENGE_TRANSFER_FORBIDDEN",
            candidate=self.candidate_with(
                importedChallengeDigests=[sha("omitted-issued-nonce")]),
            locally_issued_challenge_digests=(),
        )

    def test_32_no_local_inventory_still_cannot_claim_cutover(self):
        out = self.inspect(
            known_development_role_fingerprints=(),
            known_development_epochs=(),
            locally_issued_challenge_digests=(),
        )
        self.assertEqual(out["status"], M.HOLD)
        self.assertEqual(
            out["nextRequiredAction"],
            "OPERATOR_ENROLL_INDEPENDENT_CUSTODIAN_SEPARATELY",
        )
        self.assertNotIn("approvedEnrollment", out)
        self.assertNotIn("trustedCurrentHeadSha256", out)
        for flag in M.DENIED:
            self.assertIs(out[flag], False, flag)


if __name__ == "__main__":
    unittest.main(verbosity=2)
