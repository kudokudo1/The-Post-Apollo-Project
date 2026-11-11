"""P37 dual-signed exact-request binding contract. CI-only, always denied.

Both keys are independently generated ephemeral test keys. They are NOT
enrolled host or human-consent trust anchors. There are no real contacts,
phones, keyring items, file writes, providers, or production receipts here.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
import PhonePersonalSignedTrustP37 as trust

PROFILE = "123e4567-e89b-42d3-a456-426614174000"
HEX = "a" * 64


def request():
    return {
        "schema": trust.SCHEMA,
        "action": "NOTE",
        "profileId": PROFILE,
        "providerOwner": ":1.42",
        "sessionRef": "trusted-session-reference",
        "snapshotEpoch": 2,
        "selectedCardHmac": "b" * 64,
        "editHmac": "c" * 64,
        "expectedRevision": 3,
        "challengeSha256": "d" * 64,
        "minimumReleaseEpoch": 7,
        "minimumReleaseSequence": 14,
        "requestNonce": "e" * 32,
    }


def signed(public_private, domain, payload):
    data = trust._canonical(payload)
    return data, public_private.sign(domain + data)


def raw_public(private):
    return private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)


class SignedTrustP37Tests(unittest.TestCase):
    def setUp(self):
        self.host_key = Ed25519PrivateKey.generate()
        self.consent_key = Ed25519PrivateKey.generate()
        self.expected = request()
        self.host = {
            "schema": trust.HOST_SCHEMA,
            "role": trust.HOST_ROLE,
            "audience": trust.AUDIENCE,
            "purpose": trust.PURPOSE,
            "requestSha256": hashlib.sha256(
                trust._canonical(self.expected)).hexdigest(),
            "challengeSha256": self.expected["challengeSha256"],
            "releaseEpoch": 7,
            "releaseSequence": 14,
            "releaseSha256": "1" * 64,
            "hostEvidenceSha256": "2" * 64,
            "issuedAt": 100,
            "expiresAt": 130,
        }
        self.consent = {
            "schema": trust.CONSENT_SCHEMA,
            "role": trust.CONSENT_ROLE,
            "audience": trust.AUDIENCE,
            "purpose": trust.PURPOSE,
            "requestSha256": hashlib.sha256(
                trust._canonical(self.expected)).hexdigest(),
            "challengeSha256": self.expected["challengeSha256"],
            "hostSha256": hashlib.sha256(
                trust._canonical(self.host)).hexdigest(),
            "gestureEvidenceSha256": "3" * 64,
            "issuedAt": 102,
            "expiresAt": 120,
        }

    def verify(self, **changes):
        host_frame, host_signature = signed(
            self.host_key, trust.HOST_DOMAIN, self.host)
        consent_frame, consent_signature = signed(
            self.consent_key, trust.CONSENT_DOMAIN, self.consent)
        kwargs = {
            "expected_request": self.expected,
            "host_frame": host_frame,
            "host_signature": host_signature,
            "host_public_key": raw_public(self.host_key),
            "consent_frame": consent_frame,
            "consent_signature": consent_signature,
            "consent_public_key": raw_public(self.consent_key),
            "now": 110,
        }
        kwargs.update(changes)
        return trust.compare_signed_fixture_receipts(**kwargs)

    def denied(self, **changes):
        result = self.verify(**changes)
        self.assertEqual(result, trust.DENIED)
        self.assertIs(result["vaultWriteEnabled"], False)
        self.assertIs(result["productionEnabled"], False)
        self.assertIs(result["humanConsentVerified"], False)
        self.assertIs(result["installedHostVerified"], False)

    def test_valid_independently_signed_pair_is_still_not_a_grant(self):
        out = self.verify()
        self.assertEqual(out, trust.MATCHED_FIXTURE)
        self.assertIs(out["productionEnabled"], False)
        self.assertIs(out["vaultWriteEnabled"], False)
        self.assertIs(out["humanConsentVerified"], False)
        self.assertIs(out["installedHostVerified"], False)
        self.assertNotIn(PROFILE, str(out))
        self.assertNotIn(self.expected["selectedCardHmac"], str(out))
        self.assertNotIn(self.expected["editHmac"], str(out))
        self.assertNotIn(self.expected["requestNonce"], str(out))
        self.assertNotIn(self.expected["challengeSha256"], str(out))

    def test_missing_or_same_signer_key_denied(self):
        frame, sig = signed(self.host_key, trust.HOST_DOMAIN, self.host)
        self.denied(host_public_key=b"bad")
        self.denied(consent_public_key=b"bad")
        self.denied(host_public_key=raw_public(self.consent_key))
        self.denied(host_public_key=b"x" * 32)
        self.denied(host_signature=b"short")
        self.denied(consent_signature=b"short")
        self.denied(host_signature=sig[:-1] + b"\x00")

    def test_changed_signature_domain_and_unsigned_payload_denied(self):
        hf, hs = signed(self.host_key, trust.HOST_DOMAIN, self.host)
        cf, cs = signed(self.consent_key, trust.CONSENT_DOMAIN, self.consent)
        self.denied(host_signature=self.host_key.sign(
            trust.CONSENT_DOMAIN + hf))
        self.denied(consent_signature=self.consent_key.sign(
            trust.HOST_DOMAIN + cf))
        forged = bytearray(hf)
        forged[-2] ^= 1
        self.denied(host_frame=bytes(forged), host_signature=hs)
        forged_consent = bytearray(cf)
        forged_consent[-2] ^= 1
        self.denied(consent_frame=bytes(forged_consent), consent_signature=cs)

    def test_all_request_scope_inputs_are_signed_and_bound(self):
        variations = {
            "profileId": "223e4567-e89b-42d3-a456-426614174000",
            "providerOwner": ":1.900",
            "sessionRef": "different-session-ref",
            "snapshotEpoch": 3,
            "selectedCardHmac": "f" * 64,
            "editHmac": "f" * 64,
            "expectedRevision": 4,
            "challengeSha256": "f" * 64,
            "minimumReleaseEpoch": 8,
            "minimumReleaseSequence": 15,
            "requestNonce": "f" * 32,
            "action": "FAVORITE",
        }
        for key, value in variations.items():
            with self.subTest(key=key):
                wrong = deepcopy(self.expected)
                wrong[key] = value
                self.denied(expected_request=wrong)

    def test_host_receipt_role_challenge_release_and_schema_bound(self):
        for field, value in (
            ("role", trust.CONSENT_ROLE),
            ("audience", "other-audience"),
            ("purpose", "phone.calls.dial"),
            ("challengeSha256", "f" * 64),
            ("requestSha256", "f" * 64),
            ("releaseEpoch", 6),
            ("releaseSequence", 13),
            ("releaseSha256", "not-a-digest"),
            ("hostEvidenceSha256", "not-a-digest"),
            ("schema", "not-canonical"),
            ("releaseEpoch", True),
        ):
            with self.subTest(field=field, value=value):
                previous = self.host[field]
                self.host[field] = value
                try:
                    self.denied()
                finally:
                    self.host[field] = previous

    def test_consent_receipt_host_binding_and_gesture_evidence_bound(self):
        for field, value in (
            ("role", trust.HOST_ROLE),
            ("audience", "other-audience"),
            ("purpose", "phone.calls.dial"),
            ("challengeSha256", "f" * 64),
            ("requestSha256", "f" * 64),
            ("hostSha256", "f" * 64),
            ("gestureEvidenceSha256", "not-a-digest"),
            ("schema", "bad"),
        ):
            with self.subTest(field=field):
                previous = self.consent[field]
                self.consent[field] = value
                try:
                    self.denied()
                finally:
                    self.consent[field] = previous

    def test_new_host_receipt_invalidates_old_consent_even_if_both_signed(self):
        self.host["hostEvidenceSha256"] = "6" * 64
        self.denied()  # Consent signed hash of original host frame
        self.consent["hostSha256"] = hashlib.sha256(
            trust._canonical(self.host)).hexdigest()
        self.assertEqual(self.verify(), trust.MATCHED_FIXTURE)

    def test_expiry_and_receipt_ordering(self):
        self.denied(now=131)
        self.denied(now=99)
        self.denied(now=True)
        old = self.consent["issuedAt"]
        self.consent["issuedAt"] = 99
        self.denied()
        self.consent["issuedAt"] = old
        old = self.consent["expiresAt"]
        self.consent["expiresAt"] = 131
        self.denied()
        self.consent["expiresAt"] = old
        old = self.host["expiresAt"]
        self.host["expiresAt"] = 200
        self.denied()
        self.host["expiresAt"] = old
        self.assertEqual(self.verify(now=119), trust.MATCHED_FIXTURE)
        self.denied(now=120)

    def test_noncanonical_duplicate_or_extra_json_is_denied_with_good_signatures(self):
        hf = trust._canonical(self.host)
        for raw in (
            b" " + hf,
            hf + b"\n",
            hf.replace(b'"audience":', b'"audience":"duplicate","audience":'),
            json.dumps(self.host).encode("utf-8"),
            hf[:-1] + b',"extra":0}',
            hf + b"x" * 5000,
        ):
            with self.subTest(length=len(raw)):
                self.denied(
                    host_frame=raw,
                    host_signature=self.host_key.sign(trust.HOST_DOMAIN + raw))
        cf = trust._canonical(self.consent)
        for raw in (
            cf + b"\n",
            cf.replace(b'"role":', b'"role":"duplicate","role":'),
            cf[:-1] + b',"extra":true}',
        ):
            with self.subTest(length=len(raw)):
                self.denied(
                    consent_frame=raw,
                    consent_signature=self.consent_key.sign(
                        trust.CONSENT_DOMAIN + raw))

    def test_untrusted_requested_inputs_never_get_authorization(self):
        for bad in (
            None,
            {},
            {**self.expected, "note": "a private note"},
            {**self.expected, "selectedCardHmac": "unknown"},
            {**self.expected, "editHmac": False},
            {**self.expected, "snapshotEpoch": True},
            {**self.expected, "expectedRevision": -1},
            {**self.expected, "requestNonce": "../escape"},
            {**self.expected, "providerOwner": "org"},
            {**self.expected, "sessionRef": "x"},
        ):
            with self.subTest(kind=str(type(bad))):
                self.denied(expected_request=bad)

    def test_even_replayed_signed_fixture_is_not_permission(self):
        first = self.verify()
        replayed = self.verify()
        self.assertEqual(first, replayed)
        self.assertEqual(first, trust.MATCHED_FIXTURE)
        self.assertIs(first["productionEnabled"], False)
        self.assertIs(first["vaultWriteEnabled"], False)
        # A future trusted issuer must enforce one-use challenge consumption.
        # No claim of actual replay protection is made by this fixture.

    def test_receipt_verifier_has_no_vault_keyring_or_consent_side_effect(self):
        source = (ROOT / "services/phone/PhonePersonalSignedTrustP37.py").read_text()
        for forbidden in (
            "import PhonePersonalContactVault",
            "import PhonePersonalHostGateP36",
            "import PhonePersonalKeyringP36",
            "import dbus", "subprocess.run(", "os.open(",
            "secret-tool", "aes-gcm", "os.replace(",
            "def main(", "if __name__ ==", "read_for_trusted_host(",
            "Vault.commit(", "Identity.edit(", "seal(",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn('vaultWriteEnabled": False', source)
        self.assertIn("Ed25519PublicKey.from_public_bytes(", source)
        self.assertIn("_verify_signature(host_public_key, host_signature, HOST_DOMAIN, host_frame)", source)
        self.assertIn("_verify_signature(consent_public_key, consent_signature,", source)
        self.assertIn("CONSENT_DOMAIN, consent_frame)", source)
        self.assertIn("signature, domain + raw", source)


if __name__ == "__main__":
    unittest.main()
