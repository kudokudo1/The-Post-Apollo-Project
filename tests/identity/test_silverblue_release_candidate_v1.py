"""Identity-owned C4b #1785 release-envelope compatibility, never login tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services/identity"))
import silverblue_release_candidate_v1 as C


class SilverblueReleaseCandidateContract(unittest.TestCase):
    def setUp(self):
        self.root = Ed25519PrivateKey.generate()
        self.receipt_key = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
        self.files = {p: hashlib.sha256(("independent:" + p).encode()).hexdigest()
                      for p in C.FILES}
        self.rpm_digest = hashlib.sha256(b"not-installed-test-fixture").hexdigest()
        self.doc = {
            "schema": C.SCHEMA, "role": C.ROLE,
            "package": C.PACKAGE, "unit": C.UNIT,
            "epoch": 3, "sequence": 7,
            "rpmSha256": self.rpm_digest,
            "receiptKeySha256": hashlib.sha256(self.receipt_key).hexdigest(),
            "files": self.files,
        }

    def assess(self, doc=None, **overrides):
        doc = self.doc if doc is None else doc
        raw = C._canonical(doc)
        args = dict(
            signed_release=raw, signature=self.root.sign(C.DOMAIN + raw),
            independently_pinned_root=self.root.public_key(),
            independently_pinned_receipt_key=self.receipt_key,
            independently_measured_rpm_sha256=self.rpm_digest,
            independently_measured_files=self.files,
            minimum_epoch=3, minimum_sequence=7,
        )
        args.update(overrides)
        return C.assess_synthetic_release(**args)

    def test_valid_synthetic_candidate_is_never_admission(self):
        result = self.assess()
        self.assertEqual((result.epoch, result.sequence), (3, 7))
        for flag in ("installed_guest_measured", "host_authenticated",
                     "production_authority", "can_begin_sign_in",
                     "credential_actions_enabled"):
            self.assertIs(getattr(result, flag), False)

    def test_wrong_root_receipt_rpm_and_installed_file_pin_refused(self):
        wrong_root = Ed25519PrivateKey.generate().public_key()
        wrong_receipt = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
        for altered in (
            {"independently_pinned_root": wrong_root},
            {"independently_pinned_receipt_key": wrong_receipt},
            {"independently_measured_rpm_sha256": "0" * 64},
            {"independently_measured_files": {**self.files, C.UNIT_PATH: "0" * 64}},
        ):
            with self.subTest(altered=list(altered)):
                with self.assertRaises(C.CandidateRefused):
                    self.assess(**altered)

    def test_missing_or_extra_source_and_unit_refused(self):
        for altered in (
            {k: v for k, v in self.files.items() if k != C.UNIT_PATH},
            {**self.files, "/tmp/extra": "a" * 64},
        ):
            with self.assertRaises(C.CandidateRefused):
                self.assess(dict(self.doc, files=altered))

    def test_wrong_schema_role_package_unit_floors_refused(self):
        for k, v in (
            ("schema", "post-apollo.identity.installed-release.ci-v1"),
            ("role", "postapollo.connections.c4d-status"),
            ("package", "post-apollo-identity-ci-fixture"),
            ("unit", "different.service"),
            ("epoch", 2), ("sequence", 6),
            ("epoch", True), ("sequence", True),
        ):
            with self.subTest(field=k, value=v):
                with self.assertRaises(C.CandidateRefused):
                    self.assess(dict(self.doc, **{k: v}))

    def test_unknown_authority_field_duplicate_and_noncanonical_refused(self):
        with self.assertRaises(C.CandidateRefused):
            self.assess(dict(self.doc, hostAuthenticated=True))
        raw = C._canonical(self.doc)
        for invalid in (
            raw.replace(b'"epoch":3', b'"epoch":3,"epoch":3', 1),
            raw.replace(b'"epoch":3', b'"epoch": 3', 1),
        ):
            with self.assertRaises(C.CandidateRefused):
                C.assess_synthetic_release(
                    signed_release=invalid,
                    signature=self.root.sign(C.DOMAIN + invalid),
                    independently_pinned_root=self.root.public_key(),
                    independently_pinned_receipt_key=self.receipt_key,
                    independently_measured_rpm_sha256=self.rpm_digest,
                    independently_measured_files=self.files,
                    minimum_epoch=3, minimum_sequence=7,
                )

    def test_reject_missing_pins_instead_of_trusting_candidate(self):
        for pin in (
            {"independently_pinned_root": None},
            {"independently_pinned_receipt_key": b""},
            {"independently_measured_files": {}},
            {"minimum_epoch": True},
            {"minimum_sequence": 0},
        ):
            with self.subTest(pin=list(pin)):
                with self.assertRaises(C.CandidateRefused):
                    self.assess(**pin)

    def test_identity_candidate_has_no_native_command_or_ui_surface(self):
        source = (Path(__file__).resolve().parents[2] /
                  "services/identity/silverblue_release_candidate_v1.py").read_text()
        self.assertNotIn("SignedIdentityCommandClient(", source)
        self.assertNotIn("InstalledIdentityCommandAdapterV1(", source)
        self.assertNotIn("HostBoundary.authenticated(", source)
        upper = (Path(__file__).resolve().parents[2] /
                 "widgets/cpuplus/CpuPlusUniversalSignInHeaderPane.qml").read_text()
        self.assertIn("HostBoundary.offline()", upper)


if __name__ == "__main__":
    unittest.main()
