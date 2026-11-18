#!/usr/bin/env python3
"""C5 Hospital strict Room scope and PX v12 signed grant compatibility tests.

PX source is checked out from the exact owner PR SHA in GitHub Actions. This
test never installs a signer, writes the real Hospital database, accesses
workstation keys or treats disposable fixture signatures as operator consent.
"""
from __future__ import annotations

import base64
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "services/connections/hospital/HospitalRoomGrantAdmissionCI.py"

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C5H_REQUIRED_VERIFIER_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

C = load("c5h_hospital_room_admission", SOURCE)
PX_SOURCE = os.environ.get("C5H_PX_AUTH_SOURCE")
if not PX_SOURCE or not Path(PX_SOURCE).is_absolute():
    raise RuntimeError("C5H_PINNED_PX_SOURCE_CHECKOUT_REQUIRED")
PX = load("c5h_px_room_authority", Path(PX_SOURCE))

def b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

class HospitalRoomGrantAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.root = Ed25519PrivateKey.generate()
        self.time = 2_000_000_000
        self.room = "hospital-room-001"
        self.patient = "patient-001"
        self.repository = "kudokudo1/The-Post-Apollo-Project"
        self.operator = "native-operator-ci"
        self.seat = "native-seat-fixture-01"
        self.host = "a" * 64
        self.digest = "b" * 64
        self.nonce = b64(bytes(range(32)))
        self.review = {
            "roomId": self.room, "state": "ACTIVE", "revision": 7,
            "digest": self.digest, "canTrash": True, "canRestore": False,
            "operatorAuthenticated": False, "requiresOwnerReview": True,
            "blockers": [],
        }
        self.request = {
            "schema": C.REQUEST_SCHEMA,
            "scope": C.HOSPITAL_SCOPES["TRASH"],
            "action": "TRASH", "roomId": self.room,
            "patientId": self.patient, "repository": self.repository,
            "expectedRevision": 7, "expectedDigest": self.digest,
            "requestNonce": self.nonce,
        }
        self.grant = {
            "schema": C.PX_SCHEMA, "audience": C.PX_AUDIENCE,
            "action": "TRASH", "roomId": self.room,
            "patientId": self.patient, "repository": self.repository,
            "expectedRevision": 7, "expectedDigest": self.digest,
            "operatorId": self.operator, "approvalId": "approval-fixture-01",
            "seatId": self.seat, "hostId": self.host,
            "retentionApproved": True, "nonce": self.nonce,
            "issuedAt": self.time - 2, "expiresAt": self.time + 23,
        }
        self.sign()

    def sign(self):
        self.request_bytes = C.canonical(self.request)
        self.grant_bytes = C.canonical({
            "body": self.grant,
            "signature": b64(self.root.sign(
                C.PX_DOMAIN + C.canonical(self.grant))),
        })

    def params(self, **changes):
        args = {
            "request_bytes": self.request_bytes,
            "px_review": self.review,
            "signed_px_grant_bytes": self.grant_bytes,
            "separately_pinned_px_issuer_public": self.root.public_key(),
            "independently_expected_patient_id": self.patient,
            "independently_expected_repository": self.repository,
            "independently_expected_operator_id": self.operator,
            "independently_expected_seat_id": self.seat,
            "independently_expected_host_id": self.host,
            "now": self.time,
        }
        args.update(changes)
        return args

    def check(self, **changes):
        return C.inspect_signed_hospital_grant_ci_only(**self.params(**changes))

    def refuse(self, **changes):
        with self.assertRaises(C.Refused):
            self.check(**changes)

    def test_01_valid_exact_trash_signed_px_envelope_yields_no_auth(self):
        self.assertEqual(C.PX_DOMAIN, PX.DOMAIN)
        self.assertEqual(C.PX_SCHEMA, PX.SCHEMA)
        self.assertEqual(C.PX_AUDIENCE, PX.AUDIENCE)
        self.assertEqual(C.PX_FIELDS, PX.BODY_FIELDS)
        self.assertEqual(PX._verify_bytes(
            self.grant_bytes, self.root.public_key(), now=self.time,
        ).body, self.grant)
        out = self.check()
        self.assertEqual(out["scope"], C.HOSPITAL_SCOPES["TRASH"])
        self.assertIs(out["ciSignedHospitalRoomGrantMatchesSourceAndRequest"], True)
        for field in C.NEGATIVE:
            self.assertIs(out[field], False, field)

    def test_02_exact_restore_scope_requires_trashed_review(self):
        self.request["scope"] = C.HOSPITAL_SCOPES["RESTORE"]
        self.request["action"] = "RESTORE"
        self.grant["action"] = "RESTORE"
        self.review.update(state="TRASHED", canTrash=False, canRestore=True)
        self.sign()
        self.assertEqual(self.check()["scope"], C.HOSPITAL_SCOPES["RESTORE"])
        self.assertIs(self.check()["roomRestoreAuthorized"], False)

    def test_03_tasks_scope_never_converts_to_hospital(self):
        self.request["scope"] = "postapollo.tasks.checkpoint.capture"
        self.sign()
        self.refuse()

    def test_04_tasks_specific_c5_action_never_valid_hospital(self):
        self.request["action"] = "CAPTURE"
        self.request["scope"] = "postapollo.tasks.capture"
        self.sign()
        self.refuse()

    def test_05_no_signed_grant_fails_even_correct_room_and_revision(self):
        self.refuse(signed_px_grant_bytes=b"")
        self.refuse(signed_px_grant_bytes=None)

    def test_06_unsigned_ui_confirmation_never_suffices(self):
        self.refuse(signed_px_grant_bytes=C.canonical({
            "body": self.grant, "signature": "",
        }))

    def test_07_corrupt_signature_even_with_exact_payload_fails(self):
        frame = json.loads(self.grant_bytes)
        frame["signature"] = b64(b"\x00"*64)
        self.refuse(signed_px_grant_bytes=C.canonical(frame))

    def test_08_wrong_independent_px_root_refuses(self):
        self.refuse(separately_pinned_px_issuer_public=
                    Ed25519PrivateKey.generate().public_key())

    def test_09_signed_but_other_room_refuses(self):
        self.grant["roomId"] = "hospital-room-002"
        self.sign()
        self.refuse()

    def test_10_signed_wrong_patient_refuses(self):
        self.grant["patientId"] = "patient-002"
        self.sign()
        self.refuse()

    def test_11_signed_wrong_repository_refuses(self):
        self.grant["repository"] = "kudokudo1/other"
        self.sign()
        self.refuse()

    def test_12_signed_stale_revision_refuses(self):
        self.grant["expectedRevision"] = 6
        self.sign()
        self.refuse()

    def test_13_signed_wrong_graph_digest_refuses(self):
        self.grant["expectedDigest"] = "f"*64
        self.sign()
        self.refuse()

    def test_14_one_use_nonce_must_match_exact_request(self):
        self.grant["nonce"] = b64(bytes(range(31,-1,-1)))
        self.sign()
        self.refuse()

    def test_15_wrong_host_pin_refuses(self):
        self.refuse(independently_expected_host_id="f"*64)

    def test_16_wrong_operator_pin_refuses(self):
        self.refuse(independently_expected_operator_id="another-operator")

    def test_17_wrong_seat_pin_refuses(self):
        self.refuse(independently_expected_seat_id="another-seat-fixture")

    def test_18_expired_signed_grant_refuses(self):
        self.grant["expiresAt"] = self.time
        self.sign()
        self.refuse()

    def test_19_future_signed_grant_refuses(self):
        self.grant["issuedAt"] = self.time+4
        self.grant["expiresAt"] = self.time+16
        self.sign()
        self.refuse()

    def test_20_more_than_60_seconds_lifetime_refuses(self):
        self.grant["expiresAt"] = self.time+80
        self.sign()
        self.refuse()

    def test_21_false_retention_approval_refuses(self):
        self.grant["retentionApproved"] = False
        self.sign()
        self.refuse()

    def test_22_wrong_signed_px_audience_refuses(self):
        self.grant["audience"] = "postapollo.tasks.capture"
        self.sign()
        self.refuse()

    def test_23_wrong_signed_px_schema_refuses(self):
        self.grant["schema"] = "postapollo.tasks.grant.v1"
        self.sign()
        self.refuse()

    def test_24_extra_signed_grant_claim_refuses(self):
        self.grant["overrideAuthorization"] = True
        self.sign()
        self.refuse()

    def test_25_duplicate_envelope_json_field_refuses(self):
        corrupted = self.grant_bytes.replace(
            b'"body":', b'"body":{},"body":', 1)
        self.refuse(signed_px_grant_bytes=corrupted)

    def test_26_px_review_must_not_claim_it_granted_human_permission(self):
        self.review["operatorAuthenticated"] = True
        self.refuse()

    def test_27_source_owner_review_must_not_be_silently_skipped(self):
        self.review["requiresOwnerReview"] = False
        self.refuse()

    def test_28_trashed_source_cannot_issue_trash(self):
        self.review.update(state="TRASHED", canTrash=False, canRestore=True)
        self.refuse()

    def test_29_blocked_source_graph_never_admits_grant(self):
        self.review["blockers"] = ["SESSION_NOT_PROVEN_TERMINAL"]
        self.refuse()

    def test_30_changed_source_revision_fails(self):
        self.review["revision"] = 8
        self.refuse()

    def test_31_forged_noncanonical_request_refuses(self):
        self.refuse(request_bytes=self.request_bytes+b" ")

    def test_32_boolean_revision_not_int_refused(self):
        self.request["expectedRevision"] = True
        self.sign()
        self.refuse()

    def test_33_wrong_scope_for_correct_action_refused(self):
        self.request["scope"] = C.HOSPITAL_SCOPES["RESTORE"]
        self.sign()
        self.refuse()

    def test_34_noncanonical_signed_px_envelope_refuses(self):
        self.refuse(signed_px_grant_bytes=b" "+self.grant_bytes)

    def test_35_corrupt_grant_is_rejected_by_real_px_verifier_too(self):
        frame = json.loads(self.grant_bytes)
        frame["body"]["expectedRevision"] = 8
        bad = C.canonical(frame)
        with self.assertRaises(PX.GrantRefused):
            PX._verify_bytes(bad, self.root.public_key(), now=self.time)
        self.refuse(signed_px_grant_bytes=bad)

    def test_36_invalid_request_nonce_refuses(self):
        self.request["requestNonce"] = "not-a-nonce"
        self.sign()
        self.refuse()

    def test_37_wrong_seat_value_inside_signed_grant_refuses(self):
        self.grant["seatId"] = "different-seat-fixture"
        self.sign()
        self.refuse()

    def test_38_wrong_action_inside_signed_grant_refuses(self):
        self.grant["action"] = "RESTORE"
        self.sign()
        self.refuse()

    def test_39_signed_noncanonical_grant_nonce_refuses(self):
        self.grant["nonce"] = "Z"*43
        self.sign()
        self.refuse()

    def test_40_production_flags_are_all_false_even_after_valid_check(self):
        result = self.check()
        for key in ("realHumanConsentAuthenticated",
                    "protectedPxWriterAndDatabaseVerified",
                    "operatorC5HospitalPermissionGranted",
                    "roomTrashAuthorized","roomRestoreAuthorized",
                    "productionAuthority"):
            self.assertIs(result[key], False, key)

if __name__ == "__main__":
    unittest.main(verbosity=2)
