#!/usr/bin/env python3
"""DOC 4 Hospital C5 structured Polkit review context contract.

This is SOURCE-ONLY. A successful pkcheck return code is NOT independently
verified human consent and these tests NEVER create a real grant, key, Room
mutation, or protected writer connection.
"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/connections/hospital"))
import HospitalNativeIssuerCore as C
import HospitalNativeIssuerService as S


class HospitalC5ConsentDetails(unittest.TestCase):
    def setUp(self):
        self.request = {"action": "TRASH"}
        self.prepared = {
            "roomId": "hospital-room-04",
            "patientId": "patient-04",
            "repository": "kudokudo1/The-Post-Apollo-Project",
            "expectedRevision": 37,
            "expectedDigest": "9" * 64,
            "requestNonce": C.b64(bytes(range(32))),
            "writerInstance": "protected-px-001",
            "policyGeneration": 9,
            "expiresAt": 1700000028,
        }
        self.peer = (12345, 1000, 1000, 98765)
        self.seat = "logind-seat0-c2"

    def invoke(self, action="TRASH", code=0):
        self.request["action"] = action
        with patch.object(
            S.subprocess, "run",
            return_value=subprocess.CompletedProcess(["pkcheck"], code),
        ) as run:
            if code == 0:
                S._polkit_approve(self.request, self.prepared, self.peer, self.seat)
            else:
                with self.assertRaises(C.Refused):
                    S._polkit_approve(
                        self.request, self.prepared, self.peer, self.seat
                    )
        args = run.call_args.args[0]
        kwargs = run.call_args.kwargs
        self.assertIs(type(args), list)
        self.assertEqual(args[0], "/usr/bin/pkcheck")
        self.assertIn("--allow-user-interaction", args)
        self.assertEqual(
            args[args.index("--process") + 1], "12345,98765,1000"
        )
        self.assertTrue(kwargs["capture_output"])
        self.assertFalse(kwargs["check"])
        self.assertEqual(kwargs["timeout"], 35)
        self.assertNotIn("shell", kwargs)
        details = {}
        for i, item in enumerate(args):
            if item == "--detail":
                key, value = args[i + 1:i + 3]
                self.assertNotIn(key, details, "duplicate Polkit detail")
                details[key] = value
        return args, details

    def test_exact_protected_room_review_details_for_trash(self):
        args, details = self.invoke("TRASH")
        self.assertEqual(
            args[args.index("--action-id") + 1],
            "org.postapollo.hospital.room-trash",
        )
        expected = {
            "hospital-room-id": "hospital-room-04",
            "hospital-action": "TRASH",
            "hospital-graph": "9" * 64,
            "hospital-request-nonce": C.b64(bytes(range(32))),
            "hospital-writer-instance": "protected-px-001",
            "hospital-policy-generation": "9",
            "hospital-review-expires-at": "1700000028",
            "hospital-patient-id": "patient-04",
            "hospital-repository": "kudokudo1/The-Post-Apollo-Project",
            "hospital-revision": "37",
            "hospital-seat-id": "logind-seat0-c2",
            "hospital-retention": "PRESERVE_ORIGINAL_NO_BURN",
        }
        for key, value in expected.items():
            self.assertEqual(details.get(key), value, key)
        message = details["polkit.message"]
        for text in (
            "TRASH", "hospital-room-04", "patient-04",
            "kudokudo1/The-Post-Apollo-Project",
            "revision 37", "graph SHA-256 " + "9" * 64,
            "retain original", "logind-seat0-c2",
        ):
            self.assertIn(text, message)
        self.assertNotIn("signedGrant", str(args))
        self.assertNotIn("privateKey", str(args))

    def test_restore_uses_separate_action_and_exact_details(self):
        args, details = self.invoke("RESTORE")
        self.assertEqual(
            args[args.index("--action-id") + 1],
            "org.postapollo.hospital.room-restore",
        )
        self.assertEqual(details["hospital-action"], "RESTORE")
        self.assertEqual(details["hospital-room-id"], "hospital-room-04")
        self.assertEqual(details["hospital-revision"], "37")
        self.assertEqual(details["hospital-retention"], "PRESERVE_ORIGINAL_NO_BURN")

    def test_request_nonce_is_per_operation_and_not_a_desktop_claim(self):
        _, first = self.invoke("TRASH")
        replacement = C.b64(bytes(range(31, -1, -1)))
        self.prepared["requestNonce"] = replacement
        _, second = self.invoke("TRASH")
        self.assertNotEqual(
            first["hospital-request-nonce"],
            second["hospital-request-nonce"],
        )
        self.assertEqual(second["hospital-request-nonce"], replacement)
        self.assertEqual(second["hospital-room-id"], first["hospital-room-id"])

    def test_writer_instance_rotates_without_changing_room_or_nonce(self):
        _, first = self.invoke("TRASH")
        self.prepared["writerInstance"] = "protected-px-002"
        _, second = self.invoke("TRASH")
        self.assertNotEqual(first["hospital-writer-instance"],
                            second["hospital-writer-instance"])
        self.assertEqual(second["hospital-writer-instance"], "protected-px-002")
        self.assertEqual(second["hospital-request-nonce"],
                         first["hospital-request-nonce"])
        self.assertEqual(second["hospital-room-id"], first["hospital-room-id"])

    def test_policy_generation_and_expiry_are_explicit_protected_details(self):
        _, first = self.invoke("TRASH")
        self.prepared["policyGeneration"] = 10
        self.prepared["expiresAt"] = 1700000040
        _, second = self.invoke("TRASH")
        self.assertNotEqual(first["hospital-policy-generation"],
                            second["hospital-policy-generation"])
        self.assertNotEqual(first["hospital-review-expires-at"],
                            second["hospital-review-expires-at"])
        self.assertEqual(second["hospital-policy-generation"], "10")
        self.assertEqual(second["hospital-review-expires-at"], "1700000040")

    def test_nonzero_polkit_result_refuses_even_with_exact_details(self):
        _, details = self.invoke("TRASH", code=1)
        self.assertEqual(details["hospital-room-id"], "hospital-room-04")

    def test_timeout_refuses(self):
        with patch.object(
            S.subprocess, "run",
            side_effect=subprocess.TimeoutExpired(["pkcheck"], timeout=35),
        ):
            with self.assertRaises(C.Refused):
                S._polkit_approve(
                    self.request, self.prepared, self.peer, self.seat
                )

    def test_structured_details_are_not_human_presence_evidence(self):
        """No test may claim a native approval just from source/fixture data."""
        _, details = self.invoke()
        self.assertNotIn("operatorApproved", details)
        self.assertNotIn("humanPresent", details)
        self.assertNotIn("userConsent", details)
        self.assertEqual(
            details["hospital-retention"], "PRESERVE_ORIGINAL_NO_BURN"
        )
        # A mocked zero exit cannot prove that a prompt appeared or
        # that the active agent actually displayed any of these details.


if __name__ == "__main__":
    unittest.main(verbosity=2)
