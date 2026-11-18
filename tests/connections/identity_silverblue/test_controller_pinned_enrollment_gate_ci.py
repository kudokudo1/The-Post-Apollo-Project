#!/usr/bin/env python3
"""C4b: controller-pinned source + enrollment root must precede guest receipt."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import sys
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/identity"))
from signed_command_receipt_v0 import ReceiptIssuer, LEGACY_RECEIPT_SCHEMA, _canonical
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_controller_challenge_ci as V
import controller_pinned_enrollment_gate_ci as E

def b64(raw: bytes) -> bytes:
    return base64.urlsafe_b64encode(raw).rstrip(b"=")

class ControllerPinnedEnrollmentTests(unittest.TestCase):
    def setUp(self):
        self.root = Ed25519PrivateKey.generate()
        self.gateway = Ed25519PrivateKey.generate()
        self.guest_public = self.gateway.public_key().public_bytes_raw()
        self.nonce = V.generate_controller_challenge()
        self.denied = _canonical({
            "schema": LEGACY_RECEIPT_SCHEMA,
            "state": "UNAVAILABLE", "requestId": None,
        }) + b"\n"
        self.frame = ReceiptIssuer(self.gateway).seal(
            "BEGIN", None, self.nonce, self.denied,
        )
        self.serial = self.proof(self.guest_public, self.frame)
        self.release = hashlib.sha256(b"independently-pinned-ci-release").hexdigest()
        self.host_id = "postapollo-identity-ci@silverblue-fixture-a"
        self.record = {
            "schema": E.SCHEMA, "role": E.ROLE,
            "package": E.PACKAGE, "unit": E.UNIT,
            "audience": E.AUDIENCE, "scope": E.SCOPE,
            "enrollmentId": "a"*32,
            "hostId": self.host_id,
            "releaseSha256": self.release,
            "receiptKeySha256": hashlib.sha256(self.guest_public).hexdigest(),
            "releaseEpoch": 3, "releaseSequence": 5,
        }
        self.sign()

    @staticmethod
    def proof(pub, frame):
        return V.PROOF_PREFIX+b"pub="+b64(pub)+b" frame="+b64(frame)+b"\n"

    def sign(self):
        self.raw = E.canonical(self.record)
        self.sig = self.root.sign(E.DOMAIN + self.raw)

    def params(self, **changed):
        values = {
            "serial": self.serial,
            "controller_challenge": self.nonce,
            "signed_enrollment": self.raw,
            "enrollment_signature": self.sig,
            "independently_pinned_controller_root": self.root.public_key(),
            "independently_pinned_release_sha256": self.release,
            "independently_pinned_host_id": self.host_id,
            "minimum_release_epoch": 3,
            "minimum_release_sequence": 5,
            "revoked_enrollment_ids": (),
        }
        values.update(changed)
        return values

    def check(self, **changed):
        return E.inspect_enrolled_controller_challenge_ci_only(
            **self.params(**changed),
        )

    def refuse(self, **changed):
        with self.assertRaises(E.Refused):
            self.check(**changed)

    def test_01_separate_root_signed_exact_gateway_and_nonce_is_diagnostic_only(self):
        found=self.check()
        self.assertIs(found["ciControllerRootSignatureAndSourcePinsMatch"], True)
        self.assertIs(found["receiptSignerMatchesControllerSignedEnrollmentInCI"], True)
        self.assertIs(found["signedDenialMatchesFreshControllerNonceInCI"], True)
        for field in E.NEGATIVE:
            self.assertIs(found[field], False, field)

    def test_02_no_controller_root_is_strictly_refused(self):
        self.refuse(independently_pinned_controller_root=None)

    def test_03_guest_supplied_controller_root_is_not_a_root_enrollment(self):
        self.refuse(independently_pinned_controller_root=self.gateway.public_key())

    def test_04_different_controller_root_refused(self):
        self.refuse(independently_pinned_controller_root=
                    Ed25519PrivateKey.generate().public_key())

    def test_05_invalid_enrollment_signature_refused(self):
        self.refuse(enrollment_signature=b"\0"*64)

    def test_06_non_64_byte_signature_refused(self):
        self.refuse(enrollment_signature=b"")
        self.refuse(enrollment_signature="abc")

    def test_07_tampered_signed_enrollment_bytes_refused(self):
        self.refuse(signed_enrollment=self.raw+b" ")

    def test_08_duplicate_json_fields_refused_even_if_signed(self):
        duplicate=self.raw.replace(b'"releaseEpoch":3',
                                   b'"releaseEpoch":3,"releaseEpoch":3',1)
        self.refuse(signed_enrollment=duplicate,
                    enrollment_signature=self.root.sign(E.DOMAIN+duplicate))

    def test_09_noncanonical_or_whitespace_json_refused_even_if_signed(self):
        pretty=json.dumps(self.record, sort_keys=True, indent=1).encode()
        self.refuse(signed_enrollment=pretty,
                    enrollment_signature=self.root.sign(E.DOMAIN+pretty))

    def test_10_wrong_enrollment_audience_refused(self):
        self.record["audience"]="production-signin"
        self.sign()
        self.refuse()

    def test_11_wrong_enrollment_role_refused(self):
        self.record["role"]="postapollo.connections.other-role"
        self.sign()
        self.refuse()

    def test_12_wrong_unit_refused(self):
        self.record["unit"]="malicious-gateway.service"
        self.sign()
        self.refuse()

    def test_13_wrong_package_refused(self):
        self.record["package"]="malicious-package"
        self.sign()
        self.refuse()

    def test_14_wrong_schema_refused(self):
        self.record["schema"]="postapollo.identity.production-v1"
        self.sign()
        self.refuse()

    def test_15_wrong_scope_refused(self):
        self.record["scope"]="credentials-authorized"
        self.sign()
        self.refuse()

    def test_16_different_signed_release_pin_refused(self):
        self.refuse(independently_pinned_release_sha256="f"*64)

    def test_17_downgrade_epoch_refused(self):
        self.refuse(minimum_release_epoch=4)

    def test_18_downgrade_sequence_refused(self):
        self.refuse(minimum_release_sequence=6)

    def test_19_revoked_enrollment_identifier_refused(self):
        self.refuse(revoked_enrollment_ids=("a"*32,))

    def test_20_empty_revocation_list_allowed_in_fixture_only(self):
        found=self.check(revoked_enrollment_ids=())
        self.assertIs(found["externallyProtectedRevocationLedgerVerified"],False)

    def test_21_boolean_floors_or_missing_revocation_source_refused(self):
        self.refuse(minimum_release_epoch=True)
        self.refuse(minimum_release_sequence=False)
        self.refuse(revoked_enrollment_ids=None)
        self.refuse(revoked_enrollment_ids=[])
        self.refuse(revoked_enrollment_ids=("a"*32,"a"*32))

    def test_22_guest_changes_both_key_and_valid_receipt_still_refused(self):
        impostor=Ed25519PrivateKey.generate()
        public=impostor.public_key().public_bytes_raw()
        valid_impostor=ReceiptIssuer(impostor).seal(
            "BEGIN", None, self.nonce, self.denied,
        )
        self.refuse(serial=self.proof(public, valid_impostor))

    def test_23_forged_guest_key_but_real_enrolled_receipt_refused(self):
        impostor=Ed25519PrivateKey.generate().public_key().public_bytes_raw()
        self.refuse(serial=self.proof(impostor,self.frame))

    def test_24_replayed_old_signed_denial_with_valid_enrollment_refused(self):
        self.refuse(controller_challenge=V.generate_controller_challenge())

    def test_25_signed_non_denial_using_enrolled_gateway_refused(self):
        requested=_canonical({
            "schema":LEGACY_RECEIPT_SCHEMA,
            "state":"REQUESTED", "requestId":"CI_NO_LOGIN_REQUEST_01234567",
        })+b"\n"
        frame=ReceiptIssuer(self.gateway).seal(
            "BEGIN",None,self.nonce,requested,
        )
        self.refuse(serial=self.proof(self.guest_public,frame))

    def test_26_wrong_action_or_bad_request_id_refused(self):
        frame=ReceiptIssuer(self.gateway).seal(
            "STATUS","CI_NO_LOGIN_REQUEST_01234567",self.nonce,self.denied,
        )
        self.refuse(serial=self.proof(self.guest_public,frame))

    def test_27_duplicate_or_missing_serial_proof_refused(self):
        self.refuse(serial=self.serial+self.serial)
        self.refuse(serial=b"C4B_ID_PASS // SOMETHING\n")

    def test_28_missing_extra_or_boolean_certificate_fields_refused(self):
        del self.record["unit"]
        self.sign()
        self.refuse()
        self.record["unit"]=E.UNIT
        self.record["productionAuthority"]=True
        self.sign()
        self.refuse()
        del self.record["productionAuthority"]
        self.record["releaseSequence"]=True
        self.sign()
        self.refuse()

    def test_29_wrong_signed_receipt_key_hash_refused(self):
        self.record["receiptKeySha256"]="f"*64
        self.sign()
        self.refuse()

    def test_30_enrollment_root_must_not_equal_receipt_signer(self):
        self.root=self.gateway
        self.sign()
        self.refuse()

    def test_31_invalid_enrollment_identity_or_digest_refused(self):
        self.record["enrollmentId"]="Z"*32
        self.sign()
        self.refuse()
        self.record["enrollmentId"]="a"*32
        self.record["releaseSha256"]="zz"
        self.sign()
        self.refuse()

    def test_32_untrusted_certificate_must_not_enable_real_connections(self):
        self.assertEqual(len(E.NEGATIVE),11)
        self.assertTrue(all(x is False for x in E.NEGATIVE.values()))
        src=(Path(__file__).parent/"controller_pinned_enrollment_gate_ci.py").read_text()
        for forbidden in ("Ed25519PrivateKey.generate(", "systemctl start",
                          "rpm-ostree install","credentialActionsEnabled\": True",
                          "productionAuthority\": True"):
            self.assertNotIn(forbidden,src)

    def test_33_signed_host_scope_cannot_be_reused_on_different_host(self):
        self.refuse(independently_pinned_host_id="postapollo-identity-ci@silverblue-fixture-b")

    def test_34_controller_signs_wrong_host_still_refused(self):
        self.record["hostId"]="postapollo-identity-ci@silverblue-fixture-b"
        self.sign()
        self.refuse()

    def test_35_malformed_or_guest_chosen_host_scope_refused(self):
        self.refuse(independently_pinned_host_id="")
        self.refuse(independently_pinned_host_id="postapollo-identity-ci@HOST#A")
        self.refuse(independently_pinned_host_id=None)
        self.record["hostId"]=True
        self.sign()
        self.refuse()

if __name__=="__main__":
    unittest.main(verbosity=2)
