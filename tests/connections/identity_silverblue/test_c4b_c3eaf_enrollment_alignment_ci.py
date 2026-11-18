#!/usr/bin/env python3
"""C4b+C3e-AF source-alignment contract: signed host, version, key and denial."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_controller_owned_policy_intake_ci as F
import c4b_c3eaf_enrollment_alignment_ci as C

def pubhex(key):
    return key.public_key().public_bytes_raw().hex()

class CrossEnrollmentAlignmentTests(unittest.TestCase):
    def setUp(self):
        # Actual C4b policy-intake fixture, not a second fake C4b verifier.
        self.c4b = F.ControllerOwnedPolicyIntakeTests(
            "test_01_exact_fixture_signed_gateway_nonce_and_pins_no_grant")
        self.c4b.setUp()
        self.addCleanup(self.c4b.doCleanups)
        self.c3e_root=Ed25519PrivateKey.generate()
        self.release_root=Ed25519PrivateKey.generate()
        self.witness=Ed25519PrivateKey.generate()
        X=C.A.Z.Y.X
        self.snapshot={
            "rpmSha256":"a"*64,
            "entrypointSha256":"b"*64,
            "exeSha256":"c"*64,
            "exePath":X.EXECUTABLE,
            "unit":X.UNIT,
            "pid":2048,
            "startTicks":987654,
            "uid":992,
            "gid":995,
            "cgroup":X.CGROUP,
            "selinux":X.SELINUX,
            "socketPath":X.SOCKET,
        }
        self.role={
            "schema":C.A.SCHEMA,
            "role":C.A.Z.I.ROLE,
            "purpose":C.A.PURPOSE,
            "hostId":self.c4b.host,
            "releaseEpoch":3,
            "releaseSequence":5,
            "releaseRootPublicHex":pubhex(self.release_root),
            "hostWitnessPublicHex":pubhex(self.witness),
            "receiptPublicHex":pubhex(self.c4b.gateway),
            "runtimeSnapshotSha256":hashlib.sha256(
                X._canonical(self.snapshot)).hexdigest(),
        }
        self.sign()

    def sign(self):
        self.enrollment=C.A._canonical(self.role)
        self.signature=self.c3e_root.sign(C.A.DOMAIN+self.enrollment)

    def params(self,**changes):
        params={
            "controller_dir":self.c4b.directory,
            "serial":self.c4b.serial,
            "controller_challenge":self.c4b.nonce,
            "c3e_signed_role_enrollment":self.enrollment,
            "c3e_role_signature":self.signature,
            "separately_pinned_c3e_enrollment_root":self.c3e_root.public_key(),
            "independently_supplied_runtime_snapshot":self.snapshot,
        }
        params.update(changes)
        return params

    def check(self,**changes):
        return C.inspect_aligned_ci_only(**self.params(**changes))

    def refuse(self,**changes):
        with self.assertRaises(C.Refused):
            self.check(**changes)

    def test_01_controller_and_c3e_signed_host_and_receipt_key_match_deny_only(self):
        out=self.check()
        for key in ("c4bFreshSignedDenialMatchedControllerEnrollmentInCI",
                    "c3eSignedRoleEnrollmentMatchedHostAndVersionInCI",
                    "sameReceiptKeyBoundToC4bAndC3eRolesInCI"):
            self.assertIs(out[key],True,key)
        self.assertEqual(out["hostId"],self.c4b.host)
        self.assertEqual((out["releaseEpoch"],out["releaseSequence"]),(3,5))
        for flag in (*C.NEGATIVE,*C.P.NEGATIVE,*C.E.NEGATIVE,*C.A.NEGATIVE):
            self.assertIs(out[flag],False,flag)

    def test_02_valid_second_host_certificate_cannot_authorize_first_host(self):
        self.role["hostId"]="postapollo-identity-ci@silverblue-fixture-b"
        self.sign()
        self.refuse()

    def test_03_c3e_controller_host_cannot_be_selected_from_role_document(self):
        self.role["hostId"]="postapollo-identity-ci@silverblue-fixture-b"
        self.sign()
        self.refuse()

    def test_04_valid_but_different_c3e_receipt_signer_fails(self):
        self.role["receiptPublicHex"]=pubhex(Ed25519PrivateKey.generate())
        self.sign()
        self.refuse()

    def test_05_different_signed_c3e_epoch_refuses(self):
        self.role["releaseEpoch"]=4
        self.sign()
        self.refuse()

    def test_06_different_signed_c3e_sequence_refuses(self):
        self.role["releaseSequence"]=6
        self.sign()
        self.refuse()

    def test_07_c3e_enrollment_key_swap_refuses(self):
        self.refuse(separately_pinned_c3e_enrollment_root=
                    Ed25519PrivateKey.generate().public_key())

    def test_08_c3e_enrollment_signature_tamper_refuses(self):
        self.refuse(c3e_role_signature=b"\0"*64)

    def test_09_c3e_enrollment_bytes_tamper_refuses(self):
        self.refuse(c3e_signed_role_enrollment=self.enrollment+b" ")

    def test_10_c3e_snapshot_changed_after_signing_refuses(self):
        snapshot=dict(self.snapshot)
        snapshot["pid"]+=1
        self.refuse(independently_supplied_runtime_snapshot=snapshot)

    def test_11_c3e_snapshot_digest_forged_by_signed_doc_refuses(self):
        self.role["runtimeSnapshotSha256"]="0"*64
        self.sign()
        self.refuse()

    def test_12_c3e_root_cannot_be_c4b_controller_root(self):
        self.c3e_root=self.c4b.root
        self.sign()
        self.refuse()

    def test_13_c3e_release_role_cannot_alias_c4b_root(self):
        self.role["releaseRootPublicHex"]=pubhex(self.c4b.root)
        self.sign()
        self.refuse()

    def test_14_c3e_host_witness_cannot_alias_c4b_root(self):
        self.role["hostWitnessPublicHex"]=pubhex(self.c4b.root)
        self.sign()
        self.refuse()

    def test_15_c3e_role_key_alias_refused_by_existing_c3e_contract(self):
        self.role["hostWitnessPublicHex"]=self.role["releaseRootPublicHex"]
        self.sign()
        self.refuse()

    def test_16_c4b_policy_root_hash_swap_refuses(self):
        self.c4b.policy["rootPublicSha256"]="f"*64
        self.c4b.sign_policy()
        self.refuse()

    def test_17_c4b_controller_host_pin_changed_refuses(self):
        self.c4b.policy["hostId"]="postapollo-identity-ci@silverblue-fixture-b"
        self.c4b.sign_policy()
        self.refuse()

    def test_18_revoked_c4b_enrollment_blocks_c3e_composition(self):
        self.c4b.policy["revokedEnrollmentIds"]=["a"*32]
        self.c4b.sign_policy()
        self.refuse()

    def test_19_c4b_version_downgrade_blocks_composition(self):
        self.c4b.policy["minimumReleaseEpoch"]=4
        self.c4b.sign_policy()
        self.refuse()

    def test_20_c4b_replayed_nonce_refuses(self):
        self.refuse(controller_challenge=F.V.generate_controller_challenge())

    def test_21_wrong_guest_signer_even_with_correct_c3e_enrollment_fails(self):
        impostor=Ed25519PrivateKey.generate()
        proof=F.ReceiptIssuer(impostor).seal(
            "BEGIN",None,self.c4b.nonce,
            F._canonical({"schema":F.LEGACY_RECEIPT_SCHEMA,
                          "state":"UNAVAILABLE","requestId":None})+b"\n",
        )
        self.refuse(serial=self.c4b.proof(
            impostor.public_key().public_bytes_raw(),proof,
        ))

    def test_22_duplicate_guest_uart_proofs_refuse(self):
        self.refuse(serial=self.c4b.serial+self.c4b.serial)

    def test_23_missing_controller_policy_bundle_refuses(self):
        self.c4b.path("enrollment").unlink()
        self.refuse()

    def test_24_wrong_c3e_role_scope_refused(self):
        self.role["purpose"]="production-authorization"
        self.sign()
        self.refuse()

    def test_25_invalid_c3e_runtime_snapshot_refused(self):
        self.refuse(independently_supplied_runtime_snapshot=None)
        self.refuse(independently_supplied_runtime_snapshot={})

    def test_26_false_grants_are_constant_and_cross_release_unproven(self):
        self.assertFalse(C.NEGATIVE["crossReleaseArtifactDigestAuthenticated"])
        self.assertFalse(C.NEGATIVE["operatorControlledEnrollmentRootsVerified"])
        out=self.check()
        self.assertEqual(out["c4bReleaseSha256"],self.c4b.release)
        self.assertEqual(out["c3eRuntimeSnapshotSha256"],self.role["runtimeSnapshotSha256"])
        self.assertNotEqual(out["c4bReleaseSha256"],self.snapshot["rpmSha256"])
        self.assertIs(out["crossReleaseArtifactDigestAuthenticated"],False)

if __name__ == "__main__":
    unittest.main(verbosity=2)
