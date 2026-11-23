#!/usr/bin/env python3
"""DOC 1: C3e local challenge + C4b signed denial is still no protected trust."""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "tests/connections/c3e_release_trust"
sys.path.insert(0, str(ROOT / "services/identity"))
from signed_command_receipt_v0 import LEGACY_RECEIPT_SCHEMA, ReceiptIssuer, _canonical


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_C4B_SHADOW_EXISTING_SOURCE_REQUIRED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M = _load("c3e_c4b_shadow_under_test", HERE / "C3eC4bLocalDenialShadowCI.py")
F = _load("c3e_c4b_shadow_old_local_fixture",
          ROOT / "tests/connections/test_connections_c3e_local_development_history_ledger.py")


class LocalChallengeAndSignedDenialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (sys.platform != "linux" or os.geteuid() != 0
                or os.environ.get("GITHUB_ACTIONS") != "true"
                or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
            raise RuntimeError("C3E_C4B_SHADOW_DISPOSABLE_GITHUB_ROOT_ONLY")

    def setUp(self):
        self.fixture = F.LocalHistoryLedgerTests(
            "test_01_true_signed_continuity_advances_only_dev_head")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.local_ledger = M.S.L.DevelopmentLedger(self.fixture.work)
        self.local_adapter = M.S.LocalSQLiteTestAdapter(self.local_ledger)
        self.local = M.S.TrustBoundary(
            required_mode=M.S.LOCAL_DEVELOPMENT,
            local_adapter=self.local_adapter)
        self.protected = M.S.TrustBoundary(
            required_mode=M.S.PROTECTED_REQUIRED)
        self.raw = self.fixture.challenge
        self.signer = Ed25519PrivateKey.generate()   # CI-only, never enrolled
        self.pub = self.signer.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw)
        self.serial = self.signed_denial(self.raw)

    def signed_denial(self, challenge, *, action="BEGIN"):
        nonce = M.E.encode_raw_challenge_ci_only(challenge)
        body = _canonical({
            "schema": LEGACY_RECEIPT_SCHEMA, "state": "UNAVAILABLE",
            "requestId": None,
        }) + b"\n"
        frame = ReceiptIssuer(self.signer).seal(
            action, None, nonce, body)
        return (M.E.C4B.PROOF_PREFIX + b"pub=" +
                base64.urlsafe_b64encode(self.pub).rstrip(b"=") +
                b" frame=" +
                base64.urlsafe_b64encode(frame).rstrip(b"=") + b"\n")

    def evaluate(self, *, raw=None, serial=None, local=None, protected=None):
        return M.inspect_ci_only(
            local=self.local if local is None else local,
            protected=self.protected if protected is None else protected,
            local_challenge=self.raw if raw is None else raw,
            signed_denial=self.serial if serial is None else serial,
        )

    def denied(self, output):
        self.assertEqual(output["schema"], M.SCHEMA)
        self.assertEqual(output["status"], M.STATUS)
        self.assertEqual(output["protectedCustodianStatus"], M.S.STATUS_HOLD)
        self.assertEqual(output["next"], "HOLD_NO_PROTECTED_CUSTODY_OR_SIGNIN")
        self.assertEqual(
            set(output),
            {"schema", "status", "localObservedState",
             "localObservedHeadSha256", "localObservedSequence",
             "ciOnlySignedDenialFrameSha256",
             "ciOnlyLocalRawChallengeSha256",
             "protectedCustodianStatus", "next", *M.DENIED},
        )
        for flag in M.DENIED:
            self.assertIs(output[flag], False, flag)

    def test_01_original_local_issued_challenge_signed_denial_still_holds(self):
        out = self.evaluate()
        self.denied(out)
        self.assertEqual(out["localObservedState"], "issued")
        self.assertEqual(
            out["ciOnlyLocalRawChallengeSha256"],
            hashlib.sha256(self.raw).hexdigest())

    def test_02_original_denial_nonce_is_lossless_43_character_encoding(self):
        nonce = M.E.encode_raw_challenge_ci_only(self.raw)
        self.assertEqual(len(nonce), 43)
        self.assertEqual(
            base64.urlsafe_b64decode(nonce + "="), self.raw)
        self.denied(self.evaluate())

    def test_03_signed_denial_after_local_history_spend_still_holds(self):
        self.fixture.commit()
        out = self.evaluate()
        self.assertEqual(out["localObservedState"], "consumed")
        self.assertIs(out["protectedChallengeSpentVerified"], False)
        self.denied(out)

    def test_04_local_restore_rewinds_consumed_state_but_same_denial_still_verifies(self):
        backup = self.fixture.work / "shadow-old-image"
        shutil.copy2(self.fixture.work / F.M.DB, backup)
        self.fixture.commit()
        committed = self.evaluate()
        self.assertEqual(committed["localObservedState"], "consumed")
        shutil.copyfile(backup, self.fixture.work / F.M.DB)
        restored = self.evaluate()
        self.assertEqual(restored["localObservedState"], "issued")
        self.assertEqual(
            restored["ciOnlySignedDenialFrameSha256"],
            committed["ciOnlySignedDenialFrameSha256"])
        self.assertEqual(
            restored["localObservedHeadSha256"],
            self.fixture.head)
        self.denied(restored)

    def test_05_local_replay_after_restore_does_not_change_protected_hold(self):
        backup = self.fixture.work / "shadow-old-image"
        shutil.copy2(self.fixture.work / F.M.DB, backup)
        self.fixture.commit()
        shutil.copyfile(backup, self.fixture.work / F.M.DB)
        self.fixture.commit()  # same already-consumed proof succeeds on old DB
        self.assertEqual(self.evaluate()["localObservedState"], "consumed")
        self.assertIs(self.evaluate()["operatorEnrolledCurrentIssuerVerified"],
                      False)

    def test_06_wrong_raw_challenge_signed_denial_refused(self):
        other = bytes([self.raw[0] ^ 1]) + self.raw[1:]
        with self.assertRaisesRegex(M.Refused, "UNTRUSTED_INPUT_OR_DENIAL"):
            self.evaluate(raw=other)

    def test_07_unknown_local_challenge_refused_before_trust(self):
        unknown = b"\xff" * 32
        with self.assertRaises(M.Refused):
            self.evaluate(raw=unknown, serial=self.signed_denial(unknown))

    def test_08_signed_denial_from_unenrolled_test_key_never_enrolls(self):
        out = self.evaluate()
        self.assertIs(out["independentReceiptKeyEnrollmentVerified"], False)
        self.assertIs(out["operatorEnrolledCurrentIssuerVerified"], False)
        self.denied(out)

    def test_09_fake_begin_success_text_cannot_promote_denial(self):
        out = self.evaluate(serial=self.serial + b"CAN_BEGIN_SIGN_IN_TRUE\n")
        self.denied(out)

    def test_10_invalid_denial_signature_refused(self):
        with self.assertRaises(M.Refused):
            self.evaluate(serial=self.serial.replace(b"frame=", b"frame=Z", 1))

    def test_11_wrong_signed_action_refused(self):
        with self.assertRaises(M.Refused):
            self.evaluate(serial=self.signed_denial(self.raw, action="STATUS"))

    def test_12_local_snapshot_positive_field_refused(self):
        baseline = self.local.read_current_snapshot()
        with mock.patch.object(
            self.local, "read_current_snapshot",
            return_value=dict(baseline, hostAuthenticated=True)
        ):
            with self.assertRaisesRegex(M.Refused, "AUTHORITY_PROMOTION"):
                self.evaluate()

    def test_13_local_snapshot_extra_grant_field_refused(self):
        baseline = self.local.read_current_snapshot()
        with mock.patch.object(
            self.local, "read_current_snapshot",
            return_value=dict(baseline, newGrant=True)
        ):
            with self.assertRaisesRegex(M.Refused, "EXTRA_OR_MISSING"):
                self.evaluate()

    def test_14_protected_hold_positive_field_refused(self):
        baseline = self.protected.protected_required_status()
        with mock.patch.object(
            self.protected, "protected_required_status",
            return_value=dict(baseline, protectedCustodianReachable=True)
        ):
            with self.assertRaisesRegex(M.Refused, "AUTHORITY_PROMOTION"):
                self.evaluate()

    def test_15_protected_hold_extra_success_flag_refused(self):
        baseline = self.protected.protected_required_status()
        with mock.patch.object(
            self.protected, "protected_required_status",
            return_value=dict(baseline, actualHostTrusted=True)
        ):
            with self.assertRaisesRegex(M.Refused, "EXTRA_OR_MISSING"):
                self.evaluate()

    def test_16_c4b_returned_authority_flag_refused(self):
        original = M.E.inspect_raw_challenge_denial_ci_only
        def poisoned(**kwargs):
            out = original(**kwargs)
            return dict(out, productionAuthority=True)
        with mock.patch.object(
            M.E, "inspect_raw_challenge_denial_ci_only",
            side_effect=poisoned,
        ):
            with self.assertRaisesRegex(M.Refused, "AUTHORITY_PROMOTION"):
                self.evaluate()

    def test_17_c4b_returned_extra_trust_claim_refused(self):
        original = M.E.inspect_raw_challenge_denial_ci_only
        def poisoned(**kwargs):
            return dict(original(**kwargs), enrolled=True)
        with mock.patch.object(
            M.E, "inspect_raw_challenge_denial_ci_only",
            side_effect=poisoned,
        ):
            with self.assertRaisesRegex(M.Refused, "EXTRA_OR_MISSING"):
                self.evaluate()

    def test_18_protected_mode_cannot_use_local_adapter(self):
        with self.assertRaisesRegex(M.S.Refused, "REFUSES_LOCAL_ADAPTER"):
            M.S.TrustBoundary(required_mode=M.S.PROTECTED_REQUIRED,
                              local_adapter=self.local_adapter)

    def test_19_swapped_modes_are_refused(self):
        with self.assertRaisesRegex(M.Refused, "MODES_REQUIRED"):
            self.evaluate(local=self.protected, protected=self.local)

    def test_20_no_signin_admission_or_c5_consent(self):
        self.denied(self.evaluate())
        self.assertIs(self.evaluate()["timewC5AuthorizationVerified"], False)
        with self.assertRaisesRegex(M.Refused, "NO_INDEPENDENT_CUSTODY"):
            M.production_admission(self.raw, self.serial)


if __name__ == "__main__":
    unittest.main(verbosity=2)
