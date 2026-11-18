#!/usr/bin/env python3
"""C4b controller-only fixture intake and strict source refusal tests."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/identity"))
from signed_command_receipt_v0 import ReceiptIssuer, LEGACY_RECEIPT_SCHEMA, _canonical
sys.path.insert(0, str(Path(__file__).resolve().parent))
import controller_owned_policy_intake_ci as P
import controller_pinned_enrollment_gate_ci as E
import verify_controller_challenge_ci as V

def _b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=")

class ControllerOwnedPolicyIntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="c4b-policy-owner-")
        self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name)
        self.directory.chmod(0o700)
        self.root=Ed25519PrivateKey.generate()
        self.gateway=Ed25519PrivateKey.generate()
        self.root_pub=self.root.public_key().public_bytes_raw()
        self.gateway_pub=self.gateway.public_key().public_bytes_raw()
        self.host="postapollo-identity-ci@silverblue-fixture-a"
        self.release=hashlib.sha256(b"separately selected synthetic release").hexdigest()
        self.nonce=V.generate_controller_challenge()
        denial=_canonical({
            "schema": LEGACY_RECEIPT_SCHEMA, "state": "UNAVAILABLE",
            "requestId": None,
        })+b"\n"
        self.frame=ReceiptIssuer(self.gateway).seal(
            "BEGIN", None, self.nonce, denial,
        )
        self.serial=self.proof(self.gateway_pub,self.frame)
        self.enrollment={
            "schema":E.SCHEMA, "role":E.ROLE, "package":E.PACKAGE,
            "unit":E.UNIT, "audience":E.AUDIENCE, "scope":E.SCOPE,
            "enrollmentId":"a"*32, "hostId":self.host,
            "releaseSha256":self.release,
            "receiptKeySha256":hashlib.sha256(self.gateway_pub).hexdigest(),
            "releaseEpoch":3, "releaseSequence":5,
        }
        self.policy={
            "schema":P.SCHEMA, "audience":P.AUDIENCE, "scope":P.SCOPE,
            "hostId":self.host, "releaseSha256":self.release,
            "rootPublicSha256":hashlib.sha256(self.root_pub).hexdigest(),
            "minimumReleaseEpoch":3, "minimumReleaseSequence":5,
            "revokedEnrollmentIds":[],
        }
        self.write("root", self.root_pub)
        self.sign_enrollment()
        self.sign_policy()

    @staticmethod
    def proof(pub,frame):
        return V.PROOF_PREFIX+b"pub="+_b64(pub)+b" frame="+_b64(frame)+b"\n"

    def path(self,key):
        return self.directory/P.FILES[key][0]

    def write(self,key,raw):
        file=self.path(key)
        file.write_bytes(raw)
        file.chmod(0o600)

    def sign_enrollment(self):
        encoded=E.canonical(self.enrollment)
        self.write("enrollment",encoded)
        self.write("signature",self.root.sign(E.DOMAIN+encoded))

    def sign_policy(self):
        self.write("policy",json.dumps(
            self.policy,sort_keys=True,separators=(",",":"),
        ).encode("ascii"))

    def check(self,**kwargs):
        data={
            "controller_dir":self.directory,"serial":self.serial,
            "controller_challenge":self.nonce,
        }
        data.update(kwargs)
        return P.inspect_controller_owned_ci_only(**data)

    def refuse(self,**kwargs):
        with self.assertRaises(P.Refused):
            self.check(**kwargs)

    def test_01_exact_fixture_signed_gateway_nonce_and_pins_no_grant(self):
        result=self.check()
        self.assertIs(result["localControllerFixturePinsConsumedInCI"],True)
        self.assertIs(result["enrolledReceiptKeyMatchesSignedFreshDenialInCI"],True)
        self.assertEqual(result["hostId"],self.host)
        for field in {**P.NEGATIVE,**E.NEGATIVE}:
            self.assertIs(result[field],False,field)

    def test_02_missing_controller_directory_fails_closed(self):
        self.refuse(controller_dir=self.directory/"missing")

    def test_03_nonabsolute_controller_directory_fails_closed(self):
        self.refuse(controller_dir=Path("relative"))

    def test_04_controller_directory_cannot_be_world_readable(self):
        self.directory.chmod(0o755)
        self.refuse()

    def test_05_controller_directory_cannot_be_group_writable(self):
        self.directory.chmod(0o770)
        self.refuse()

    def test_06_symlink_controller_directory_fails_closed(self):
        alias=self.directory.parent/(self.directory.name+"-alias")
        alias.symlink_to(self.directory, target_is_directory=True)
        self.addCleanup(alias.unlink)
        self.refuse(controller_dir=alias)

    def test_07_missing_controller_root_fails_closed(self):
        self.path("root").unlink()
        self.refuse()

    def test_08_untrusted_root_key_swap_refused_even_if_enrollment_is_valid(self):
        other=Ed25519PrivateKey.generate().public_key().public_bytes_raw()
        self.write("root",other)
        self.refuse()

    def test_09_wrong_root_hash_in_controller_policy_refused(self):
        self.policy["rootPublicSha256"]="f"*64
        self.sign_policy()
        self.refuse()

    def test_10_symlinked_controller_root_file_refused(self):
        root=self.path("root")
        backup=self.directory/"backup-root"
        root.rename(backup)
        root.symlink_to(backup)
        self.refuse()

    def test_11_hardlinked_controller_policy_refused(self):
        old=self.path("policy")
        old.rename(self.directory/"policy-backup")
        os.link(self.directory/"policy-backup",old)
        self.refuse()

    def test_12_world_readable_enrollment_certificate_refused(self):
        self.path("enrollment").chmod(0o644)
        self.refuse()

    def test_13_world_writable_signed_enrollment_signature_refused(self):
        self.path("signature").chmod(0o666)
        self.refuse()

    def test_14_truncated_root_or_signature_refused(self):
        self.write("root",self.root_pub[:-1])
        self.refuse()
        self.write("root",self.root_pub)
        self.write("signature",self.path("signature").read_bytes()[:-1])
        self.refuse()

    def test_15_extra_json_policy_field_refused(self):
        self.policy["hostAuthenticated"]=True
        self.sign_policy()
        self.refuse()

    def test_16_noncanonical_policy_whitespace_refused(self):
        self.write("policy",json.dumps(self.policy,indent=2).encode())
        self.refuse()

    def test_17_duplicate_policy_fields_refused(self):
        raw=self.path("policy").read_bytes()
        raw=raw.replace(b'"schema":',b'"schema":"evil","schema":',1)
        self.write("policy",raw)
        self.refuse()

    def test_18_wrong_host_id_refused_even_when_enrollment_valid(self):
        self.policy["hostId"]="postapollo-identity-ci@silverblue-fixture-b"
        self.sign_policy()
        self.refuse()

    def test_19_wrong_release_pin_refused(self):
        self.policy["releaseSha256"]="f"*64
        self.sign_policy()
        self.refuse()

    def test_20_higher_controller_minimum_floor_refuses_rollback(self):
        self.policy["minimumReleaseEpoch"]=4
        self.sign_policy()
        self.refuse()
        self.policy["minimumReleaseEpoch"]=3
        self.policy["minimumReleaseSequence"]=6
        self.sign_policy()
        self.refuse()

    def test_21_revoked_identity_refused(self):
        self.policy["revokedEnrollmentIds"]=["a"*32]
        self.sign_policy()
        self.refuse()

    def test_22_duplicate_or_unsorted_revocation_entries_refused(self):
        self.policy["revokedEnrollmentIds"]=["a"*32,"a"*32]
        self.sign_policy()
        self.refuse()
        self.policy["revokedEnrollmentIds"]=["b"*32,"a"*32]
        self.sign_policy()
        self.refuse()

    def test_23_invalid_policy_role_or_scope_refused(self):
        self.policy["scope"]="allow-login"
        self.sign_policy()
        self.refuse()

    def test_24_fake_guest_signs_correct_nonce_using_own_key_still_refused(self):
        impostor=Ed25519PrivateKey.generate()
        proof=ReceiptIssuer(impostor).seal(
            "BEGIN",None,self.nonce,
            _canonical({"schema":LEGACY_RECEIPT_SCHEMA,
                        "state":"UNAVAILABLE","requestId":None})+b"\n",
        )
        self.refuse(serial=self.proof(impostor.public_key().public_bytes_raw(),proof))

    def test_25_nonce_replay_refused_with_unmodified_valid_certificate(self):
        self.refuse(controller_challenge=V.generate_controller_challenge())

    def test_26_modified_enrollment_signature_refused(self):
        self.write("signature",b"\0"*64)
        self.refuse()

    def test_27_signed_non_denial_refused(self):
        requested=_canonical({
            "schema":LEGACY_RECEIPT_SCHEMA,
            "state":"REQUESTED","requestId":"CI_NO_LOGIN_REQUEST_01234567",
        })+b"\n"
        frame=ReceiptIssuer(self.gateway).seal("BEGIN",None,self.nonce,requested)
        self.refuse(serial=self.proof(self.gateway_pub,frame))

    def test_28_no_production_key_creation_or_permission_grants(self):
        source=Path(P.__file__).read_text()
        for forbidden in (
            "Ed25519PrivateKey.generate(", "systemctl start",
            "rpm-ostree install", '"hostAuthenticated": True',
            '"productionAuthority": True', "export PRIVATE",
        ):
            self.assertNotIn(forbidden,source)
        self.assertTrue(all(x is False for x in P.NEGATIVE.values()))

if __name__=="__main__":
    unittest.main(verbosity=2)
