"""P38: actual upstream CI type/field compatibility. All outcomes deny writes."""
from __future__ import annotations

from dataclasses import asdict, fields
from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
sys.path.insert(0, str(ROOT / "services" / "identity"))
import PhonePersonalSignedTrustP37 as P37
import PhonePersonalUpstreamHandoffP38 as P38
import silverblue_release_candidate_v1 as C4B

# Loading the real owning C3e-Z module reads code/format only. This does NOT
# run its challenge issuer, consume a ledger, verify a host, or change any file.
C3EZ_FILE = ROOT / "tests/connections/c3e_release_trust/C3eZReleaseBoundHostEvidence.py"
spec = importlib.util.spec_from_file_location("p38_existing_c3ez", C3EZ_FILE)
assert spec is not None and spec.loader is not None
C3EZ = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = C3EZ
spec.loader.exec_module(C3EZ)


def public(private):
    return private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)


class P38OwnerInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.host_key = Ed25519PrivateKey.generate()
        self.consent_key = Ed25519PrivateKey.generate()
        self.request = {
            "schema": P37.SCHEMA, "action": "NOTE",
            "profileId": "123e4567-e89b-42d3-a456-426614174000",
            "providerOwner": ":1.42", "sessionRef": "trusted-session-reference",
            "snapshotEpoch": 2, "selectedCardHmac": "b" * 64,
            "editHmac": "c" * 64, "expectedRevision": 3,
            "challengeSha256": "d" * 64,
            "minimumReleaseEpoch": 7, "minimumReleaseSequence": 14,
            "requestNonce": "e" * 32,
        }
        digest = hashlib.sha256(P37._canonical(self.request)).hexdigest()
        self.host = {
            "schema": P37.HOST_SCHEMA, "role": P37.HOST_ROLE,
            "audience": P37.AUDIENCE, "purpose": P37.PURPOSE,
            "requestSha256": digest, "challengeSha256": "d" * 64,
            "releaseEpoch": 7, "releaseSequence": 14,
            "releaseSha256": "1" * 64,
            "hostEvidenceSha256": "2" * 64,
            "issuedAt": 100, "expiresAt": 130,
        }
        self.consent = {
            "schema": P37.CONSENT_SCHEMA, "role": P37.CONSENT_ROLE,
            "audience": P37.AUDIENCE, "purpose": P37.PURPOSE,
            "requestSha256": digest, "challengeSha256": "d" * 64,
            "hostSha256": hashlib.sha256(P37._canonical(self.host)).hexdigest(),
            "gestureEvidenceSha256": "3" * 64,
            "issuedAt": 102, "expiresAt": 120,
        }
        self.c4b = asdict(C4B.SilverblueReleaseCandidateV1(
            epoch=7, sequence=14,
            package_sha256="1" * 64, receipt_key_sha256="4" * 64))
        self.c3ez = {
            "schema": C3EZ.SCHEMA,
            "releaseSourceAndRuntimePinsMatchedInCI": True,
            "releaseReceiptSignerMatchedInCI": True,
            "fullRecordChallengeConsumedInRootLocalCI": True,
            **C3EZ.NEGATIVE, **C3EZ.Y.X.NEGATIVE,
        }

    def compare(self, **overrides):
        hf = P37._canonical(self.host)
        cf = P37._canonical(self.consent)
        args = {
            "expected_request": self.request,
            "host_frame": hf,
            "host_signature": self.host_key.sign(P37.HOST_DOMAIN + hf),
            "host_public_key": public(self.host_key),
            "consent_frame": cf,
            "consent_signature": self.consent_key.sign(P37.CONSENT_DOMAIN + cf),
            "consent_public_key": public(self.consent_key),
            "now": 110,
            "c4b_candidate": self.c4b,
            "c3ez_result": self.c3ez,
        }
        args.update(overrides)
        return P38.compare_fixture_handoff(**args)

    def denied(self, **changes):
        self.assertEqual(self.compare(**changes), P38.REFUSED)

    def test_real_upstream_types_and_flags_are_recognized_but_not_authority(self):
        self.assertEqual(set(self.c4b), P38.C4B_FIELDS)
        self.assertEqual(set(f.name for f in fields(C4B.SilverblueReleaseCandidateV1)),
                         P38.C4B_FIELDS)
        self.assertEqual(P38.C3EZ_SCHEMA, C3EZ.SCHEMA)
        self.assertEqual(set(C3EZ.NEGATIVE) | set(C3EZ.Y.X.NEGATIVE),
                         P38.C3EZ_FALSE)
        self.assertEqual(set(self.c3ez), P38.C3EZ_FIELDS)
        got = self.compare()
        self.assertEqual(got, P38.CI_COMPATIBLE)
        self.assertEqual(got["status"], "CI_FORMATS_RECOGNIZED_NOT_AUTHENTICATED")
        for flag in (
            "productionEnabled", "vaultWriteEnabled", "humanConsentVerified",
            "installedHostVerified", "keyReleaseEnabled",
        ):
            self.assertIs(got[flag], False)
        self.assertNotIn(self.request["profileId"], str(got))
        self.assertNotIn(self.request["selectedCardHmac"], str(got))
        self.assertNotIn(self.request["editHmac"], str(got))

    def test_missing_receipts_or_production_c5_claim_is_denied(self):
        self.denied(c4b_candidate=None)
        self.denied(c3ez_result=None)
        for claim in ({}, True, False, "approved", {"approved": True},
                      {"humanConsentVerified": True}):
            with self.subTest(c5=repr(claim)):
                self.denied(genuine_c5_receipt=claim)

    def test_c3e_z_promotion_or_unknown_format_is_denied(self):
        for change in (
            lambda x: x.pop("schema"),
            lambda x: x.update(schema="unknown"),
            lambda x: x.update(productionAuthority=True),
            lambda x: x.update(c5HumanConsentVerified=True),
            lambda x: x.update(installedGuestMeasured=True),
            lambda x: x.update(externalRollbackResistanceVerified=True),
            lambda x: x.update(fullRecordChallengeConsumedInRootLocalCI=False),
            lambda x: x.update(releaseReceiptSignerMatchedInCI="yes"),
            lambda x: x.update(newProductionProof=True),
            lambda x: x.pop("signedGuestOriginAuthenticated"),
        ):
            obj = deepcopy(self.c3ez)
            change(obj)
            with self.subTest(obj_keys=sorted(obj.keys())[:3]):
                self.denied(c3ez_result=obj)

    def test_c4b_production_promotion_tamper_and_release_mismatch(self):
        for change in (
            lambda x: x.update(installed_guest_measured=True),
            lambda x: x.update(host_authenticated=True),
            lambda x: x.update(production_authority=True),
            lambda x: x.update(can_begin_sign_in=True),
            lambda x: x.update(credential_actions_enabled=True),
            lambda x: x.update(epoch=8),
            lambda x: x.update(sequence=13),
            lambda x: x.update(package_sha256="7" * 64),
            lambda x: x.update(receipt_key_sha256="unknown"),
            lambda x: x.update(sequence=True),
            lambda x: x.pop("installed_guest_measured"),
            lambda x: x.update(unknown="yes"),
        ):
            obj = deepcopy(self.c4b)
            change(obj)
            with self.subTest(keys=sorted(obj.keys())[:3]):
                self.denied(c4b_candidate=obj)

    def test_p37_signature_mutation_and_request_drift_denied(self):
        self.denied(host_public_key=public(self.consent_key))
        self.denied(consent_public_key=public(self.host_key))
        self.denied(host_signature=b"0" * 64)
        self.denied(consent_signature=b"0" * 64)
        self.denied(now=200)
        self.denied(expected_request={**self.request, "profileId":
                     "223e4567-e89b-42d3-a456-426614174000"})
        self.denied(expected_request={**self.request, "requestNonce": "f" * 32})
        self.denied(expected_request={**self.request, "action": "FAVORITE"})
        self.denied(expected_request={**self.request, "expectedRevision": 2})

    def test_unsigned_external_results_never_bind_real_c3ez_receipt_to_p37(self):
        # Deliberately unchanged: C3e-Z results expose CI test booleans but
        # no authenticated C3e witness signature/evidence bytes to P38.
        self.assertNotIn("signed_statement", P38.C3EZ_FIELDS)
        self.assertNotIn("hostEvidenceSha256", P38.C3EZ_FIELDS)
        self.assertNotIn("c5HumanConsentReceipt", P38.C3EZ_FIELDS)
        self.assertEqual(self.compare(), P38.CI_COMPATIBLE)
        self.assertFalse(self.compare()["installedHostVerified"])
        self.assertFalse(self.compare()["humanConsentVerified"])

    def test_no_real_host_or_contact_storage_side_effect(self):
        path = ROOT / "services/phone/PhonePersonalUpstreamHandoffP38.py"
        source = path.read_text(encoding="utf-8")
        for banned in (
            "PhonePersonalContactVault", "PhonePersonalKeyringP36",
            "import dbus", "import subprocess", "import socket", "os.open(",
            "Vault.commit(", "secret-tool", "QtQuick", "def main(",
            "if __name__ ==", "productionEnabled\": True",
            "vaultWriteEnabled\": True", "keyReleaseEnabled\": True",
        ):
            self.assertNotIn(banned, source)
        self.assertIn("P37.compare_signed_fixture_receipts(", source)
        self.assertIn("genuine_c5_receipt is not None", source)
        self.assertIn("all(result[k] is False for k in C3EZ_FALSE)", source)


if __name__ == "__main__":
    unittest.main()
