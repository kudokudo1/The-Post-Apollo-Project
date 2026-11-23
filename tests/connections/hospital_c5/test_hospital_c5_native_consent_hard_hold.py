#!/usr/bin/env python3
"""DOC 4 Hospital C5-H4: real issuer must refuse without trusted native consent.

OS identity, Polkit and protected PX PREPARE are mocked. These tests do not
install a service or provision a key. In every case no signing or PX COMMIT.
"""
from __future__ import annotations

from contextlib import ExitStack
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/connections/hospital"))

import HospitalNativeIssuerCore as C
import HospitalNativeIssuerService as S


class NativeConsentHardHold(unittest.TestCase):
    def setUp(self):
        self.now = int(time.time())
        self.nonce_bytes = bytes(range(32))
        self.policy = {
            "schema": C.RUNTIME_POLICY_SCHEMA,
            "operatorUid": 1000,
            "clientExecutableSha256": "a" * 64,
            "pxWriterUid": 987,
            "pxWriterExecutableSha256": "b" * 64,
            "hostId": "c" * 64,
            "minimumPolicyGeneration": 9,
            "expiresAt": self.now + 3600,
        }
        self.request = {
            "schema": C.REQUEST_SCHEMA,
            "action": "TRASH",
            "roomId": "hospital-room-04",
        }
        self.prepared = {
            "schema": C.PREPARED_SCHEMA,
            "requestNonce": C.b64(self.nonce_bytes),
            "action": "TRASH",
            "roomId": "hospital-room-04",
            "patientId": "patient-04",
            "repository": "kudokudo1/The-Post-Apollo-Project",
            "expectedRevision": 37,
            "expectedDigest": "d" * 64,
            "state": "ACTIVE",
            "blockers": [],
            "canTrash": True,
            "canRestore": False,
            "retentionApproved": True,
            "legalHold": False,
            "policyGeneration": 9,
            "writerInstance": "protected-px-001",
            "expiresAt": self.now + 28,
        }

    def exercise(self, *, rc=0, timeout=False, seat=None, policy=None, environment=None):
        peer = (4321, 1000, 1000, 54321)
        calls = []
        def writer(_policy, body):
            calls.append(body["kind"])
            self.assertEqual(body["kind"], "prepare", "PX COMMIT must remain unreachable")
            self.assertEqual(body["requestNonce"], C.b64(self.nonce_bytes))
            return C.canonical(self.prepared)

        with ExitStack() as stack:
            stack.enter_context(patch.object(S, "_peer", return_value=peer))
            stack.enter_context(patch.object(S, "_same_peer", return_value=peer))
            stack.enter_context(patch.object(
                S, "_packet_recv", return_value=C.canonical(self.request)))
            stack.enter_context(patch.object(
                S, "_active_seat", return_value="logind-seat0-c1"
                if seat is None else None, side_effect=seat))
            stack.enter_context(patch.object(S, "_writer_exchange", side_effect=writer))
            stack.enter_context(patch.object(
                C, "host_fingerprint", return_value="c" * 64))
            stack.enter_context(patch.object(
                C, "read_policy", return_value=self.policy if policy is None else policy))
            stack.enter_context(patch.object(
                S.os, "urandom", side_effect=lambda n: self.nonce_bytes
                if n == 32 else self.fail("unexpected nonce length")))
            key = stack.enter_context(patch.object(C, "load_installed_key"))
            sign = stack.enter_context(patch.object(C, "sign_px_grant"))
            if timeout:
                result = stack.enter_context(patch.object(
                    S.subprocess, "run",
                    side_effect=subprocess.TimeoutExpired(["pkcheck"], 35)))
            else:
                result = stack.enter_context(patch.object(
                    S.subprocess, "run",
                    return_value=subprocess.CompletedProcess(["pkcheck"], rc)))
            stack.enter_context(patch.dict(os.environ, environment or {}, clear=False))
            with self.assertRaises(C.Refused) as cm:
                S._native_step(object(), self.policy)

            key.assert_not_called()
            sign.assert_not_called()
        return str(cm.exception), calls, result.call_count

    def test_01_direct_hard_gate_refuses_without_external_producer(self):
        with self.assertRaisesRegex(
                C.Refused, "INDEPENDENT_EXACT_ROOM_HUMAN_CONSENT_UNAVAILABLE"):
            S._require_independent_room_consent(
                self.request, self.prepared, (4321, 1000, 1000, 54321),
                "logind-seat0-c1")

    def test_02_valid_trash_and_polkit_success_still_hold(self):
        msg, calls, pk = self.exercise()
        self.assertIn("INDEPENDENT_EXACT_ROOM_HUMAN_CONSENT_UNAVAILABLE", msg)
        self.assertEqual(calls, ["prepare"])
        self.assertEqual(pk, 1)

    def test_03_valid_restore_and_polkit_success_still_hold(self):
        self.request["action"] = "RESTORE"
        self.prepared.update(action="RESTORE", state="TRASHED",
                             canTrash=False, canRestore=True)
        msg, calls, pk = self.exercise()
        self.assertIn("INDEPENDENT_EXACT_ROOM_HUMAN_CONSENT_UNAVAILABLE", msg)
        self.assertEqual(calls, ["prepare"])
        self.assertEqual(pk, 1)

    def test_04_environment_claims_never_supply_human_consent(self):
        msg, calls, pk = self.exercise(environment={
            "POST_APOLLO_CI": "1",
            "HOSPITAL_C5_HUMAN_CONSENT": "true",
            "HOSPITAL_C5_CONSENT_AGENT": "approved",
            "POLKIT_ALLOW_CACHED": "1",
        })
        self.assertIn("INDEPENDENT_EXACT_ROOM_HUMAN_CONSENT_UNAVAILABLE", msg)
        self.assertEqual(calls, ["prepare"])
        self.assertEqual(pk, 1)

    def test_05_polkit_denial_blocks_before_consent_gate(self):
        msg, calls, pk = self.exercise(rc=1)
        self.assertIn("OPERATOR_POLKIT_INTERACTION_NOT_APPROVED", msg)
        self.assertEqual(calls, ["prepare"])
        self.assertEqual(pk, 1)

    def test_06_polkit_timeout_blocks_before_consent_gate(self):
        msg, calls, pk = self.exercise(timeout=True)
        self.assertIn("POLKIT_UNAVAILABLE", msg)
        self.assertEqual(calls, ["prepare"])
        self.assertEqual(pk, 1)

    def test_07_added_desktop_confirmation_flag_does_not_authorize(self):
        self.request["operatorConfirmed"] = True
        msg, calls, pk = self.exercise()
        self.assertIn("FRAME_REFUSED", msg)
        self.assertEqual(calls, [])
        self.assertEqual(pk, 0)

    def test_08_added_px_display_claim_is_not_a_prepared_source_field(self):
        self.prepared["claimedVisible"] = True
        msg, calls, pk = self.exercise()
        self.assertIn("FRAME_REFUSED", msg)
        self.assertEqual(calls, ["prepare"])
        self.assertEqual(pk, 0)

    def test_09_added_px_signature_claim_cannot_override_review(self):
        self.prepared["humanConsentVerified"] = True
        msg, calls, pk = self.exercise()
        self.assertIn("FRAME_REFUSED", msg)
        self.assertEqual(calls, ["prepare"])
        self.assertEqual(pk, 0)

    def test_10_wrong_nonce_prepared_refused_before_polkit(self):
        self.prepared["requestNonce"] = C.b64(bytes(range(31, -1, -1)))
        msg, calls, pk = self.exercise()
        self.assertIn("REFUSED", msg)
        self.assertEqual(calls, ["prepare"])
        self.assertEqual(pk, 0)

    def test_11_blocked_room_cannot_be_confirmed(self):
        self.prepared["legalHold"] = True
        msg, calls, pk = self.exercise()
        self.assertIn("HOSPITAL_NATIVE_HOLD", msg)
        self.assertEqual(calls, ["prepare"])
        self.assertEqual(pk, 0)

    def test_12_expired_px_prepared_never_reaches_polkit(self):
        self.prepared["expiresAt"] = self.now - 1
        msg, calls, pk = self.exercise()
        self.assertIn("HOSPITAL_NATIVE_HOLD", msg)
        self.assertEqual(calls, ["prepare"])
        self.assertEqual(pk, 0)

    def test_13_changed_operator_seat_refuses_before_sign(self):
        msg, calls, pk = self.exercise(
            seat=["logind-seat0-c1", "logind-seat0-c1", "logind-seat1-c2"])
        self.assertIn("SESSION_CHANGED_AFTER_CONSENT", msg)
        self.assertEqual(calls, ["prepare"])
        self.assertEqual(pk, 1)

    def test_14_revoked_issuer_policy_refuses_after_polkit(self):
        stale = dict(self.policy, minimumPolicyGeneration=10)
        msg, calls, pk = self.exercise(policy=stale)
        self.assertIn("ISSUER_POLICY_CHANGED_DURING_OPERATOR_APPROVAL", msg)
        self.assertEqual(calls, ["prepare"])
        self.assertEqual(pk, 1)

    def test_15_exact_guard_precedes_private_key_and_px_commit_in_source(self):
        source = (
            ROOT / "services/connections/hospital/HospitalNativeIssuerService.py"
        ).read_text()
        start = source.index("def _native_step(client, policy):")
        block = source[start:]
        self.assertLess(
            block.index("_polkit_approve(request, prepared, peer, first_seat)"),
            block.index("_require_independent_room_consent("
                        "request, prepared, peer, first_seat)"))
        self.assertLess(
            block.index("_require_independent_room_consent("
                        "request, prepared, peer, first_seat)"),
            block.index("key = C.load_installed_key()"))
        self.assertLess(
            block.index("key = C.load_installed_key()"),
            block.index('"kind": "commit"'))

    def test_16_no_runtime_test_agent_or_authorizing_environment_override(self):
        source = (
            ROOT / "services/connections/hospital/HospitalNativeIssuerService.py"
        ).read_text()
        self.assertNotIn("HospitalC5ExactConsentProbe", source)
        self.assertNotIn("POST_APOLLO_CI", source)
        self.assertNotIn("HOSPITAL_C5_CONSENT_AGENT", source)
        self.assertNotIn("operatorConfirmed", source)
        self.assertNotIn("humanConsentVerified", source)
        self.assertNotIn("allow_untrusted", source)
        self.assertNotIn("exec(", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
