"""P39 signed *synthetic source bytes* from actual C4b/C3e-Y schemas.

All public roots, claimed measurements and signing keys are test-generated
within this process. C3e-X per-record denial signatures and an external
challenge ledger remain unverified here. Every path returns NO vault grant.
"""
from __future__ import annotations

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
import PhonePersonalSignedSourceP39 as P39
import PhonePersonalSignedTrustP37 as P37
import silverblue_release_candidate_v1 as C4B

C3EY_PATH = ROOT / "tests/connections/c3e_release_trust/C3eYSignedHostChallenge.py"
spec = importlib.util.spec_from_file_location("p39_source_current_c3ey", C3EY_PATH)
assert spec and spec.loader
Y = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = Y
spec.loader.exec_module(Y)


def public(key):
    return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)


class P39SourceBytesTests(unittest.TestCase):
    def setUp(self):
        self.host_key = Ed25519PrivateKey.generate()
        self.consent_key = Ed25519PrivateKey.generate()
        self.root_key = Ed25519PrivateKey.generate()
        self.witness_key = Ed25519PrivateKey.generate()
        self.receipt_key = Ed25519PrivateKey.generate()

        self.rpm = hashlib.sha256(b"fake-rpm-not-installed").hexdigest()
        self.files = {
            name: hashlib.sha256(("fake-file:"+name).encode()).hexdigest()
            for name in C4B.FILES
        }
        self.snapshot = {
            "rpmSha256": self.rpm,
            "entrypointSha256": self.files[C4B.PREFIX + "identity-gateway-ci"],
            "exeSha256": hashlib.sha256(b"synthetic-executable").hexdigest(),
            "exePath": Y.X.EXECUTABLE,
            "unit": C4B.UNIT,
            "pid": 12345,
            "startTicks": 100000,
            "uid": 1000,
            "gid": 1000,
            "cgroup": Y.X.CGROUP,
            "selinux": Y.X.SELINUX,
            "socketPath": Y.X.SOCKET,
        }
        self.release = {
            "schema": C4B.SCHEMA,
            "role": C4B.ROLE,
            "package": C4B.PACKAGE,
            "unit": C4B.UNIT,
            "epoch": 7,
            "sequence": 14,
            "rpmSha256": self.rpm,
            "receiptKeySha256": hashlib.sha256(public(self.receipt_key)).hexdigest(),
            "files": self.files,
        }
        self.evidence = Y.X._canonical({
            "schema": Y.X.SCHEMA, "role": Y.X.ROLE,
            # Deliberately only syntax/number and witness SHA bind checked.
            # Full record fields and signatures need independent C3e-X call.
            "records": [{"synthetic": i} for i in range(4)]
        }) + b"\n"
        self.denials = tuple(
            ("FAKE-UNVERIFIED-RECEIPT-" + str(i)).encode()
            for i in range(4)
        )
        self.request = {
            "schema": P37.SCHEMA, "action": "NOTE",
            "profileId": "123e4567-e89b-42d3-a456-426614174000",
            "providerOwner": ":1.42",
            "sessionRef": "synthetic-phone-session",
            "snapshotEpoch": 2,
            "selectedCardHmac": "b" * 64,
            "editHmac": "c" * 64,
            "expectedRevision": 3,
            "challengeSha256": "d" * 64,
            "minimumReleaseEpoch": 7,
            "minimumReleaseSequence": 14,
            "requestNonce": "e" * 32,
        }
        self.statement = {
            "schema": Y.SCHEMA, "role": Y.ROLE,
            "purpose": Y.PURPOSE, "audience": Y.AUDIENCE,
            "releaseEpoch": 7,
            "releaseSequence": 14,
            "challengeSha256": self.request["challengeSha256"],
            "evidenceSha256": hashlib.sha256(self.evidence).hexdigest(),
            "receiptSha256": [hashlib.sha256(raw).hexdigest() for raw in self.denials],
            "snapshotSha256": hashlib.sha256(
                Y.X._canonical(self.snapshot)).hexdigest(),
            "receiptKeySha256": hashlib.sha256(public(self.receipt_key)).hexdigest(),
        }
        self._resign()

    def _resign(self):
        self.release_bytes = C4B._canonical(self.release)
        self.release_sig = self.root_key.sign(C4B.DOMAIN + self.release_bytes)
        self.statement_bytes = Y.X._canonical(self.statement)
        self.statement_sig = self.witness_key.sign(Y.DOMAIN + self.statement_bytes)
        digest = hashlib.sha256(P37._canonical(self.request)).hexdigest()
        self.host = {
            "schema": P37.HOST_SCHEMA, "role": P37.HOST_ROLE,
            "audience": P37.AUDIENCE, "purpose": P37.PURPOSE,
            "requestSha256": digest,
            "challengeSha256": self.request["challengeSha256"],
            "releaseEpoch": 7, "releaseSequence": 14,
            "releaseSha256": self.rpm,
            "hostEvidenceSha256": hashlib.sha256(self.statement_bytes).hexdigest(),
            "issuedAt": 100, "expiresAt": 130,
        }
        self.host_bytes = P37._canonical(self.host)
        self.host_sig = self.host_key.sign(P37.HOST_DOMAIN + self.host_bytes)
        self.consent = {
            "schema": P37.CONSENT_SCHEMA, "role": P37.CONSENT_ROLE,
            "audience": P37.AUDIENCE, "purpose": P37.PURPOSE,
            "requestSha256": digest,
            "challengeSha256": self.request["challengeSha256"],
            "hostSha256": hashlib.sha256(self.host_bytes).hexdigest(),
            "gestureEvidenceSha256": "3" * 64,
            "issuedAt": 102, "expiresAt": 120,
        }
        self.consent_bytes = P37._canonical(self.consent)
        self.consent_sig = self.consent_key.sign(
            P37.CONSENT_DOMAIN + self.consent_bytes)

    def compare(self, **overrides):
        args = {
            "expected_request": self.request,
            "p37_host_frame": self.host_bytes,
            "p37_host_signature": self.host_sig,
            "p37_host_public_key": public(self.host_key),
            "p37_consent_frame": self.consent_bytes,
            "p37_consent_signature": self.consent_sig,
            "p37_consent_public_key": public(self.consent_key),
            "now": 110,
            "signed_release": self.release_bytes,
            "release_signature": self.release_sig,
            "release_root_key": public(self.root_key),
            "receipt_public_key": public(self.receipt_key),
            "independently_measured_files": self.files,
            "independently_measured_rpm": self.rpm,
            "signed_statement": self.statement_bytes,
            "witness_signature": self.statement_sig,
            "witness_public_key": public(self.witness_key),
            "evidence_line": self.evidence,
            "denial_frames": self.denials,
            "independently_measured_snapshot": self.snapshot,
        }
        args.update(overrides)
        return P39.compare_signed_ci_source(**args)

    def denied(self, **overrides):
        self.assertEqual(self.compare(**overrides), P39.REFUSED)

    def test_current_upstream_signed_schemas_are_version_pinned(self):
        self.assertEqual(P39.C4B_SCHEMA, C4B.SCHEMA)
        self.assertEqual(P39.C4B_DOMAIN, C4B.DOMAIN)
        self.assertEqual(P39.C4B_FIELDS, C4B.KEYS)
        self.assertEqual(P39.C4B_FILES, C4B.FILES)
        self.assertEqual(P39.C4B_UNIT, C4B.UNIT)
        self.assertEqual(P39.C3EY_SCHEMA, Y.SCHEMA)
        self.assertEqual(P39.C3EY_ROLE, Y.ROLE)
        self.assertEqual(P39.C3EY_PURPOSE, Y.PURPOSE)
        self.assertEqual(P39.C3EY_AUDIENCE, Y.AUDIENCE)
        self.assertEqual(P39.C3EY_DOMAIN, Y.DOMAIN)
        self.assertEqual(P39.C3EY_FIELDS, Y.SIGNED_KEYS)
        self.assertEqual(P39.C3EX_FIELDS, Y.X.SNAPSHOT.intersection(P39.C3EX_FIELDS)
                         if False else frozenset({"schema", "role", "records"}))
        self.assertEqual(P39.SNAPSHOT_FIELDS, Y.X.SNAPSHOT)

    def test_two_real_verified_upstream_signatures_still_deny_production(self):
        result = self.compare()
        self.assertEqual(result, P39.MATCHED)
        self.assertEqual(result["status"], "SIGNED_CI_SOURCE_BYTES_BOUND_NOT_AUTHENTICATED")
        for name in (
            "productionEnabled", "installedHostVerified", "humanConsentVerified",
            "vaultWriteEnabled", "keyReleaseEnabled",
            "externalChallengeConsumed",
        ):
            self.assertIs(result[name], False)
        for secret in (
            self.request["profileId"], self.request["editHmac"],
            self.request["selectedCardHmac"], self.request["requestNonce"],
            self.statement["evidenceSha256"],
        ):
            self.assertNotIn(secret, str(result))

    def test_invalid_or_tampered_release_signature_content_or_files(self):
        self.denied(release_signature=b"X" * 64)
        self.denied(release_root_key=public(Ed25519PrivateKey.generate()))
        self.denied(signed_release=self.release_bytes + b"\n",
                    release_signature=self.root_key.sign(
                        P39.C4B_DOMAIN + self.release_bytes + b"\n"))
        self.denied(independently_measured_rpm="f" * 64)
        self.denied(independently_measured_files={**self.files,
                    next(iter(self.files)): "a" * 64})
        self.denied(independently_measured_files={})
        malformed = self.release_bytes.replace(
            b'"epoch":7', b'"epoch":7,"epoch":7')
        self.denied(signed_release=malformed,
                    release_signature=self.root_key.sign(P39.C4B_DOMAIN + malformed))

    def test_release_epoch_role_and_receipt_signer_downgrade_denied(self):
        for field, value in (
            ("epoch", 8), ("sequence", 13), ("epoch", True),
            ("role", "different"), ("schema", "different"),
            ("receiptKeySha256", "f" * 64),
            ("package", "different")
        ):
            with self.subTest(field=field, value=value):
                self.release[field] = value
                self._resign()
                self.denied()
                self.release[field] = 7 if field == "epoch" else (
                    14 if field == "sequence" else
                    C4B.ROLE if field == "role" else
                    C4B.SCHEMA if field == "schema" else
                    hashlib.sha256(public(self.receipt_key)).hexdigest()
                    if field == "receiptKeySha256" else C4B.PACKAGE)
                self._resign()

    def test_witness_signature_evidence_receipts_snapshot_and_challenge(self):
        self.denied(witness_signature=b"Y" * 64)
        self.denied(witness_public_key=public(Ed25519PrivateKey.generate()))
        self.denied(evidence_line=self.evidence + b"x")
        self.denied(denial_frames=self.denials[:3])
        self.denied(denial_frames=self.denials[:3] + (b"DIFFERENT",))
        self.denied(independently_measured_snapshot={**self.snapshot,
                    "pid": 99999})
        self.denied(independently_measured_snapshot={**self.snapshot,
                    "rpmSha256": "a" * 64})
        self.denied(receipt_public_key=public(Ed25519PrivateKey.generate()))
        self.denied(signed_statement=self.statement_bytes + b" ",
                    witness_signature=self.witness_key.sign(
                        P39.C3EY_DOMAIN + self.statement_bytes + b" "))
        original = self.statement["challengeSha256"]
        self.statement["challengeSha256"] = "f" * 64
        self._resign()
        self.denied()
        self.statement["challengeSha256"] = original
        self._resign()

    def test_witness_frame_mutation_requires_new_p37_host_evidence(self):
        self.statement["evidenceSha256"] = "f" * 64
        self._resign()  # P37 frame points to changed signed witness.
        self.denied()   # Still fails actual evidence bytes hash.
        self.statement["evidenceSha256"] = hashlib.sha256(self.evidence).hexdigest()
        self._resign()
        self.assertEqual(self.compare(), P39.MATCHED)
        old = self.host_bytes
        self.host["hostEvidenceSha256"] = "f" * 64
        self.host_bytes = P37._canonical(self.host)
        self.host_sig = self.host_key.sign(P37.HOST_DOMAIN + self.host_bytes)
        # P37 consent still references the old host, so whole chain fails.
        self.denied()
        self.host_bytes = old
        self._resign()

    def test_signature_roles_missing_c5_and_different_request_denied(self):
        self.denied(release_root_key=public(self.witness_key))
        self.denied(receipt_public_key=public(self.host_key))
        self.denied(p37_consent_public_key=public(self.host_key))
        self.denied(genuine_c5_receipt={"approved": True})
        self.denied(genuine_c5_receipt=False)
        self.denied(p37_consent_signature=b"0" * 64)
        self.denied(expected_request={**self.request, "action": "FAVORITE"})
        self.denied(expected_request={**self.request, "requestNonce": "f" * 32})
        self.denied(expected_request={**self.request, "profileId":
                    "223e4567-e89b-42d3-a456-426614174000"})
        self.denied(now=130)

    def test_no_external_one_use_challenge_or_installed_process_claim(self):
        self.assertEqual(self.compare(), P39.MATCHED)
        self.assertEqual(self.compare(), P39.MATCHED)
        # Replays are deliberately NOT consumed: the real issuer is absent.
        self.assertFalse(self.compare()["externalChallengeConsumed"])
        source = (ROOT / "services/phone/PhonePersonalSignedSourceP39.py").read_text()
        for name in (
            "import sqlite3", "import dbus", "import subprocess",
            "PhonePersonalContactVault", "PhonePersonalKeyring",
            "os.open(", "Vault.commit(", "secret-tool", "def main(",
            "productionEnabled\": True", "vaultWriteEnabled\": True",
            "keyReleaseEnabled\": True",
        ):
            self.assertNotIn(name, source)


if __name__ == "__main__":
    unittest.main()
